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
from frappe.utils import cint, flt

from importlib import import_module

# Doctype trees compose verbatim (no rcore substitution), so the
# composed "<app>.polaris" package root is derived from __name__ at runtime.
_base = __name__.split(".doctype.")[0]
gl_posting = import_module(_base + ".rlending.gl_posting")


def get_pending_principal_amount(loan):
    """
    Ported from Frappe Lending's `loan_repayment.py:get_pending_principal_amount`,
    trimmed to the branches Polaris actually reaches (no Line of Credit schedule
    type - unused today). Debit/credit adjustment amounts ARE included: Phase 4
    confirmed `RokctAI_frontend`'s `lifecycle.ts:createBalanceAdjustment` writes
    a real `Loan Balance Adjustment` doctype against these fields, so they're
    live, not speculative.
    """
    precision = cint(frappe.db.get_default("currency_precision")) or 2

    if loan.status == "Cancelled":
        return 0

    if loan.status in ("Disbursed", "Closed", "Active", "Written Off", "Settled"):
        return flt(
            flt(loan.total_payment)
            + flt(loan.debit_adjustment_amount)
            - flt(loan.credit_adjustment_amount)
            - flt(loan.total_principal_paid)
            - flt(loan.total_interest_payable),
            precision,
        )

    return flt(
        flt(loan.disbursed_amount)
        + flt(loan.debit_adjustment_amount)
        - flt(loan.credit_adjustment_amount)
        - flt(loan.total_principal_paid),
        precision,
    )


class LoanRepayment(Document):
    """
    Polaris's own Loan Repayment doctype - forked from Frappe Lending's
    `Loan Repayment` (Phase 3). Plain Document. Upstream's 3,497-line
    controller was NOT ported wholesale - only `get_pending_principal_amount`
    (the one function `rlending` actually imported) plus enough on_submit
    balance-tracking to make repayments a real, working sub-ledger entry
    rather than a dead-end doctype. Real GL posting (gl-posting-brief.md)
    happens in wallet_integration.py's debit_wallet_on_repayment, which runs
    as an on_submit doc_event alongside this doctype's own on_submit.
    """

    def validate(self):
        if not self.amount_paid:
            frappe.throw(_("Amount Paid is mandatory"))
        if not frappe.db.exists("Loan", self.against_loan):
            frappe.throw(_("Loan {0} does not exist").format(self.against_loan))
        if not self.principal_amount_paid:
            self.principal_amount_paid = self.amount_paid

        loan = frappe.get_doc("Loan", self.against_loan)
        self.pending_principal_amount = max(
            0, flt(get_pending_principal_amount(loan)) - flt(self.principal_amount_paid)
        )

    def on_submit(self):
        self.update_loan_on_repayment()

    def on_cancel(self):
        gl_posting.cancel_journal_entry(self.journal_entry)
        loan = frappe.get_doc("Loan", self.against_loan)
        loan.db_set("total_principal_paid", flt(loan.total_principal_paid) - flt(self.principal_amount_paid))
        loan.db_set("total_amount_paid", flt(loan.total_amount_paid) - flt(self.amount_paid))
        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))

    def update_loan_on_repayment(self):
        loan = frappe.get_doc("Loan", self.against_loan)
        loan.db_set("total_principal_paid", flt(loan.total_principal_paid) + flt(self.principal_amount_paid))
        loan.db_set("total_amount_paid", flt(loan.total_amount_paid) + flt(self.amount_paid))

        if get_pending_principal_amount(loan) <= 0:
            loan.db_set("status", "Closed")
            loan.db_set("closure_date", self.posting_date)

        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))
