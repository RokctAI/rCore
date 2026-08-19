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

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

from importlib import import_module

# Doctype trees compose verbatim (no rcore substitution), so the
# composed "<app>.polaris" package root is derived from __name__ at runtime.
_base = __name__.split(".doctype.")[0]
get_pending_principal_amount = import_module(
    _base + ".doctype.loan_repayment.loan_repayment"
).get_pending_principal_amount
gl_posting = import_module(_base + ".rlending.gl_posting")

# Fixed Actual/365 day-count convention. Upstream supports a per-Company
# `interest_day_count_convention` setting (Actual/365, Actual/360, 30/360,
# Actual/Actual) - Polaris has no such Company field anywhere in this
# codebase, so rather than invent one, this fork fixes the single most
# common/conservative convention. Revisit if a specific convention is
# ever required.
YEAR_DIVISOR = 365


def get_per_day_interest(principal_amount, rate_of_interest):
    """Ported from Frappe Lending's loan_interest_accrual.py:get_per_day_interest,
    fixed to Actual/365 (see YEAR_DIVISOR note above)."""
    return flt((flt(principal_amount) * flt(rate_of_interest)) / (YEAR_DIVISOR * 100))


def get_interest_amount(no_of_days, principal_amount, rate_of_interest):
    """Ported from Frappe Lending's loan_interest_accrual.py:get_interest_amount."""
    return get_per_day_interest(principal_amount, rate_of_interest) * no_of_days


def get_last_accrual_date(loan_name, posting_date):
    """
    Ported/simplified from Frappe Lending's get_last_accrual_date. Upstream's
    version branches heavily on Loan Repayment Schedule / moratorium / Line of
    Credit handling - none of which apply here since Polaris only forks the
    non-term-loan (bullet loan) accrual path. Reduces to: last Normal Interest
    accrual's posting_date, or the day before the loan's last disbursement
    date if there's no prior accrual.
    """
    last_accrual_date = frappe.db.get_value(
        "Loan Interest Accrual",
        {"loan": loan_name, "docstatus": 1, "interest_type": "Normal Interest"},
        "posting_date",
        order_by="posting_date desc",
    )
    if last_accrual_date:
        return last_accrual_date

    disbursement_date = frappe.db.get_value(
        "Loan Disbursement",
        {"against_loan": loan_name, "docstatus": 1},
        "disbursement_date",
        order_by="disbursement_date desc",
    )
    if disbursement_date:
        return add_days(disbursement_date, -1)

    return posting_date


def calculate_accrual_for_loan(loan, posting_date, process_loan_interest_accrual=None):
    """
    Ported/trimmed from Frappe Lending's calculate_accrual_amount_for_loans -
    the non-term-loan (bullet loan, simple interest) branch only. The
    term-loan branch requires Loan Repayment Schedule (EMI schedule
    generation), which this fork deliberately never built (see Phase 2/3
    notes - nothing in rlending or RokctAI_frontend generates or reads
    repayment schedule rows).
    """
    posting_date = getdate(posting_date)
    last_accrual_date = get_last_accrual_date(loan.name, posting_date)

    no_of_days = date_diff(posting_date, last_accrual_date)
    if no_of_days <= 0:
        return None

    pending_principal_amount = get_pending_principal_amount(loan)
    payable_interest = get_interest_amount(no_of_days, pending_principal_amount, loan.rate_of_interest)

    precision = cint(frappe.db.get_default("currency_precision")) or 2
    payable_interest = flt(payable_interest, precision)

    if payable_interest <= 0:
        return None

    accrual = frappe.new_doc("Loan Interest Accrual")
    accrual.loan = loan.name
    accrual.applicant_type = loan.applicant_type
    accrual.applicant = loan.applicant
    accrual.company = loan.company
    accrual.loan_product = loan.loan_product
    accrual.interest_type = "Normal Interest"
    accrual.process_loan_interest_accrual = process_loan_interest_accrual
    accrual.base_amount = pending_principal_amount
    accrual.rate_of_interest = loan.rate_of_interest
    accrual.interest_amount = payable_interest
    accrual.start_date = last_accrual_date
    accrual.posting_date = posting_date
    accrual.insert(ignore_permissions=True)
    accrual.submit()
    return accrual.name


class LoanInterestAccrual(Document):
    """
    Polaris's own Loan Interest Accrual doctype - forked from Frappe Lending's
    `Loan Interest Accrual` (Phase 5), trimmed HARD: upstream's real file is
    1,256 lines covering term-loan schedule-based accrual, penal interest tied
    to EMI demand rows, and async batch queuing, none of which are ported.
    What upstream called "GL posting" (its own make_gl_entries()) isn't
    ported either - this fork's real GL posting (gl-posting-brief.md) is a
    much smaller, purpose-built module (gl_posting.py) invoked from
    on_submit/on_cancel below, not a port of upstream's GL logic.
    """

    def validate(self):
        if not self.interest_amount:
            frappe.throw(_("Interest Amount is mandatory"))
        if not self.posting_date:
            self.posting_date = nowdate()
        if not frappe.db.exists("Loan", self.loan):
            frappe.throw(_("Loan {0} does not exist").format(self.loan))

    def on_submit(self):
        gl_posting.post_interest_accrual(self)

        loan = frappe.get_doc("Loan", self.loan)
        # get_pending_principal_amount() computes total_payment - total_principal_paid
        # - total_interest_payable - it's PRINCIPAL only, deliberately unaffected by
        # interest accrual. total_payment must move in lockstep with
        # total_interest_payable so that formula's principal figure stays correct
        # instead of silently drifting down as interest accrues (a real bug caught
        # by Phase 5's mocked lifecycle test - outstanding_amount must NOT be
        # touched here).
        loan.db_set("total_interest_payable", flt(loan.total_interest_payable) + flt(self.interest_amount))
        loan.db_set("total_payment", flt(loan.total_payment) + flt(self.interest_amount))

    def on_cancel(self):
        gl_posting.cancel_journal_entry(self.journal_entry)

        loan = frappe.get_doc("Loan", self.loan)
        loan.db_set("total_interest_payable", flt(loan.total_interest_payable) - flt(self.interest_amount))
        loan.db_set("total_payment", flt(loan.total_payment) - flt(self.interest_amount))
