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
from frappe.utils import flt

from importlib import import_module

# Doctype trees compose verbatim (no rcore substitution), so the
# composed "<app>.polaris" package root is derived from __name__ at runtime.
_base = __name__.split(".doctype.")[0]
get_pending_principal_amount = import_module(
    _base + ".doctype.loan_repayment.loan_repayment"
).get_pending_principal_amount
gl_posting = import_module(_base + ".rlending.gl_posting")


class LoanDisbursement(Document):
    """
    Polaris's own Loan Disbursement doctype - forked from Frappe Lending's
    `Loan Disbursement` (Phase 3). Plain Document - `on_submit` updates the
    linked Loan's running balances directly as a self-contained sub-ledger
    entry. Real GL posting (gl-posting-brief.md) happens in
    wallet_integration.py's credit_wallet_on_disbursement, which runs as an
    on_submit doc_event alongside this method, not here - this keeps GL
    posting in one place (also used by Loan Repayment) rather than
    duplicating it per doctype.
    """

    def validate(self):
        if not self.disbursed_amount:
            frappe.throw(_("Disbursed Amount is mandatory"))
        if not frappe.db.exists("Loan", self.against_loan):
            frappe.throw(_("Loan {0} does not exist").format(self.against_loan))

    def on_submit(self):
        self.status = "Submitted"
        self.update_loan_on_disbursement()

    def on_cancel(self):
        self.status = "Cancelled"
        gl_posting.cancel_journal_entry(self.journal_entry)
        loan = frappe.get_doc("Loan", self.against_loan)
        loan.db_set("disbursed_amount", flt(loan.disbursed_amount) - flt(self.disbursed_amount))
        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))

    def update_loan_on_disbursement(self):
        loan = frappe.get_doc("Loan", self.against_loan)
        loan.db_set("disbursed_amount", flt(loan.disbursed_amount) + flt(self.disbursed_amount))
        loan.db_set("disbursement_date", self.disbursement_date)

        # Without interest accrual (Phase 5), total_payment tracks principal
        # outstanding only - it will need to be re-derived once accrual lands.
        loan.db_set("total_payment", flt(loan.disbursed_amount))

        if loan.status in (None, "", "Draft", "Approved", "Sanctioned"):
            loan.db_set("status", "Disbursed")

        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))
