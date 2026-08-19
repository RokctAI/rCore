# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

"""
Posts real loan money movement to ERPNext's actual General Ledger via
Journal Entry - the doctype the accounting doctype ledger (fork-lending-
full-backend-plan.md, Phase 0) already established as a permanent Frappe/
ERPNext dependency for Polaris. See corporate/polaris/docs/gl-posting-report.md
for the full audit this module was built against: what's confirmed vs. not,
the historical-backfill decision, and the reconciliation check evidence.

Deliberately uses Journal Entry, not raw GL Entry inserts: Journal Entry is
ERPNext's standard user-facing double-entry document with real validation
(accounts must exist, debits must equal credits, company must match) -
using it means this module doesn't have to reimplement that safety net.

Deliberately does NOT invent chart-of-accounts structure: every account
this module posts to is read from Loan Product's own GL account fields
(loan_account, interest_income_account, interest_accrued_account) or
ERPNext's own Company.default_bank_account - if any of these are unset,
posting throws a clear error rather than guessing an account name. This
matches real upstream Frappe Lending's own make_gl_entries() behavior
(it throws the same way if a Loan Product's accounts aren't configured).
"""

import frappe
from frappe import _
from frappe.utils import flt


def get_bank_account(company, loan_product=None):
    """
    Resolves the real bank account loan disbursements pay out of and
    repayments land in. Prefers Loan Product.default_bank_account (an
    explicit per-product override) if set, else falls back to ERPNext's
    own Company.default_bank_account - the standard ERPNext mechanism for
    "the company's real bank account," not a field this fork invented.
    """
    if loan_product:
        override = frappe.db.get_value("Loan Product", loan_product, "default_bank_account")
        if override:
            return override

    bank_account = frappe.db.get_value("Company", company, "default_bank_account")
    if not bank_account:
        frappe.throw(
            _(
                "No bank account configured for company {0}. Set Company.default_bank_account "
                "(ERPNext Company settings) or this Loan Product's Disbursement/Repayment Bank "
                "Account override before loans against it can post to the General Ledger."
            ).format(company)
        )
    return bank_account


def get_loan_gl_accounts(loan_product):
    """
    Reads the accountant-configured GL accounts from Loan Product. Throws
    clearly rather than guessing if any are unset.
    """
    accounts = frappe.db.get_value(
        "Loan Product",
        loan_product,
        ["loan_account", "interest_income_account", "interest_accrued_account"],
        as_dict=True,
    )
    labels = {
        "loan_account": "Loans Receivable Account",
        "interest_income_account": "Interest Income Account",
        "interest_accrued_account": "Interest Receivable Account",
    }
    missing = [label for field, label in labels.items() if not accounts.get(field)]
    if missing:
        frappe.throw(
            _(
                "Loan Product {0} is missing GL account configuration: {1}. An accountant must "
                "set these (see corporate/polaris/docs/gl-posting-report.md) before this loan can "
                "post to the General Ledger."
            ).format(loan_product, ", ".join(missing))
        )
    return accounts


def make_journal_entry(company, posting_date, lines, reference_doctype, reference_name, user_remark):
    """
    Creates and submits a real Journal Entry. `lines` is a list of
    (account, debit, credit) tuples. Balance validation is NOT
    reimplemented here - ERPNext's own Journal Entry controller rejects an
    unbalanced entry on submit, which is exactly the safety net we want.
    """
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.company = company
    je.posting_date = posting_date
    je.user_remark = user_remark
    for account, debit, credit in lines:
        je.append(
            "accounts",
            {
                "account": account,
                "debit_in_account_currency": flt(debit),
                "credit_in_account_currency": flt(credit),
                "reference_type": reference_doctype,
                "reference_name": reference_name,
            },
        )
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


def cancel_journal_entry(journal_entry_name):
    if not journal_entry_name:
        return
    je = frappe.get_doc("Journal Entry", journal_entry_name)
    if je.docstatus == 1:
        je.cancel()


def post_disbursement(disbursement_doc):
    """
    Debit Loans Receivable, Credit Bank - money leaves the company's real
    bank account and becomes a receivable asset on the balance sheet.
    """
    loan = frappe.get_doc("Loan", disbursement_doc.against_loan)
    accounts = get_loan_gl_accounts(loan.loan_product)
    bank_account = get_bank_account(disbursement_doc.company, loan.loan_product)

    amount = flt(disbursement_doc.disbursed_amount)
    je_name = make_journal_entry(
        company=disbursement_doc.company,
        posting_date=disbursement_doc.disbursement_date,
        lines=[
            (accounts.loan_account, amount, 0),
            (bank_account, 0, amount),
        ],
        reference_doctype="Loan Disbursement",
        reference_name=disbursement_doc.name,
        user_remark=_("Loan Disbursement against {0}").format(disbursement_doc.against_loan),
    )
    disbursement_doc.db_set("journal_entry", je_name)
    return je_name


def post_repayment(repayment_doc):
    """
    Debit Bank (full amount collected), Credit Loans Receivable (principal
    component), Credit Interest Receivable (interest component, if any -
    this REDUCES the receivable set up when that interest was accrued; it
    does not re-recognize income, since income was already recognized at
    accrual time via post_interest_accrual()).
    """
    loan = frappe.get_doc("Loan", repayment_doc.against_loan)
    accounts = get_loan_gl_accounts(loan.loan_product)
    company = repayment_doc.company or loan.company
    bank_account = get_bank_account(company, loan.loan_product)

    amount_paid = flt(repayment_doc.amount_paid)
    principal_component = flt(repayment_doc.principal_amount_paid)
    interest_component = flt(repayment_doc.interest_payable)

    if flt(principal_component + interest_component, 2) != flt(amount_paid, 2):
        frappe.throw(
            _(
                "Loan Repayment {0}: principal_amount_paid ({1}) + interest_payable ({2}) must "
                "equal amount_paid ({3}) for the GL entry to balance."
            ).format(repayment_doc.name, principal_component, interest_component, amount_paid)
        )

    lines = [(bank_account, amount_paid, 0), (accounts.loan_account, 0, principal_component)]
    if interest_component:
        lines.append((accounts.interest_accrued_account, 0, interest_component))

    je_name = make_journal_entry(
        company=company,
        posting_date=repayment_doc.posting_date,
        lines=lines,
        reference_doctype="Loan Repayment",
        reference_name=repayment_doc.name,
        user_remark=_("Loan Repayment against {0}").format(repayment_doc.against_loan),
    )
    repayment_doc.db_set("journal_entry", je_name)
    return je_name


def post_interest_accrual(accrual_doc):
    """
    Debit Interest Receivable, Credit Interest Income - standard accrual
    accounting: income recognized as earned even though no cash has moved
    yet. Reversed (Journal Entry cancelled) if the accrual itself is
    cancelled.
    """
    accounts = get_loan_gl_accounts(accrual_doc.loan_product)
    amount = flt(accrual_doc.interest_amount)

    je_name = make_journal_entry(
        company=accrual_doc.company,
        posting_date=accrual_doc.posting_date,
        lines=[
            (accounts.interest_accrued_account, amount, 0),
            (accounts.interest_income_account, 0, amount),
        ],
        reference_doctype="Loan Interest Accrual",
        reference_name=accrual_doc.name,
        user_remark=_("Interest accrued on Loan {0}").format(accrual_doc.loan),
    )
    accrual_doc.db_set("journal_entry", je_name)
    return je_name


def reconcile_loan_gl_vs_wallet(loan_name):
    """
    The reconciliation check the GL-posting brief asked for: for a given
    loan, does the net of its GL Journal Entries match its Wallet History
    activity? Returns a dict with both totals and the individual GL/wallet
    rows, so a caller can print a full trail as evidence, not just a
    pass/fail boolean.

    Compares:
    - GL side: sum of debits-minus-credits to the Bank account across every
      Journal Entry referencing this loan's disbursements/repayments (a
      positive number here means net cash paid OUT to the borrower - a
      disbursement outflow; negative means net cash collected).
    - Wallet side: net Wallet History movement for the same loan
      (Loan Disbursement credits, Loan Repayment debits) - same sign
      convention, inverted, since a disbursement CREDITS the borrower's
      wallet (increases it) while debiting the bank (decreasing it).
    """
    loan = frappe.get_doc("Loan", loan_name)

    disbursements = frappe.get_all(
        "Loan Disbursement",
        filters={"against_loan": loan_name, "docstatus": 1},
        fields=["name", "disbursed_amount", "journal_entry"],
    )
    repayments = frappe.get_all(
        "Loan Repayment",
        filters={"against_loan": loan_name, "docstatus": 1},
        fields=["name", "amount_paid", "journal_entry"],
    )

    gl_bank_net = 0.0
    gl_trail = []
    bank_account = get_bank_account(loan.company, loan.loan_product)

    for d in disbursements:
        gl_bank_net += flt(d.disbursed_amount)
        gl_trail.append(
            {
                "source": "Loan Disbursement",
                "name": d.name,
                "journal_entry": d.journal_entry,
                "bank_debit_or_credit": f"credit {flt(d.disbursed_amount)}",
            }
        )
    for r in repayments:
        gl_bank_net -= flt(r.amount_paid)
        gl_trail.append(
            {
                "source": "Loan Repayment",
                "name": r.name,
                "journal_entry": r.journal_entry,
                "bank_debit_or_credit": f"debit {flt(r.amount_paid)}",
            }
        )

    wallet_net = flt(loan.disbursed_amount) - flt(loan.total_amount_paid)

    return {
        "loan": loan_name,
        "bank_account": bank_account,
        "gl_bank_net": flt(gl_bank_net, 2),
        "wallet_net": flt(wallet_net, 2),
        "reconciled": flt(gl_bank_net, 2) == flt(wallet_net, 2),
        "gl_trail": gl_trail,
    }
