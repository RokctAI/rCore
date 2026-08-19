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
from frappe.model.document import Document
from frappe.utils import add_days, nowdate

from importlib import import_module

# Doctype trees compose verbatim (no rcore substitution), so the
# composed "<app>.polaris" package root is derived from __name__ at runtime.
calculate_accrual_for_loan = import_module(
    __name__.split(".doctype.")[0] + ".doctype.loan_interest_accrual.loan_interest_accrual"
).calculate_accrual_for_loan


class ProcessLoanInterestAccrual(Document):
    """
    Polaris's own Process Loan Interest Accrual doctype - forked from Frappe
    Lending's `Process Loan Interest Accrual` orchestrator (Phase 5).
    `on_submit` runs the simple-interest accrual (see loan_interest_accrual.py)
    over every matching bullet (non-term) Loan synchronously - upstream's
    background `frappe.enqueue` batching wasn't ported since Polaris's loan
    volume/usage evidence doesn't suggest it's needed yet, and a synchronous
    run is easier to verify.
    """

    def validate(self):
        if not self.posting_date:
            self.posting_date = nowdate()

    def on_submit(self):
        filters = {
            "docstatus": 1,
            "status": ("in", ["Disbursed", "Active"]),
            "is_term_loan": 0,
        }
        if self.loan:
            filters["name"] = self.loan
        if self.loan_product:
            filters["loan_product"] = self.loan_product
        if self.company:
            filters["company"] = self.company

        loan_names = frappe.get_all("Loan", filters=filters, pluck="name")

        for loan_name in loan_names:
            loan = frappe.get_doc("Loan", loan_name)
            try:
                calculate_accrual_for_loan(loan, self.posting_date, process_loan_interest_accrual=self.name)
            except Exception:
                frappe.log_error(
                    title="Loan Interest Accrual Error",
                    message=frappe.get_traceback(),
                    reference_doctype="Loan",
                    reference_name=loan_name,
                )

        self.db_set("status", "Completed")


def process_loan_interest_accrual_for_loans(
    posting_date=None,
    loan_product=None,
    loan=None,
    company=None,
):
    """
    Whitelisted entry point matching upstream's real function name/shape (see
    process_loan_interest_accrual.py), minus loan_disbursement/from_demand/
    accrual_type params that only apply to the term-loan/EMI path this fork
    doesn't implement.

    NOTE: RokctAI_frontend's operations.ts calls this with an extra
    `term_loan: 0` kwarg that doesn't match any parameter here (or in the
    real upstream signature either) - that call would raise a TypeError
    against this or the real Lending app. Flagged, not fixed (frontend
    caller code, out of scope for this doctype fork).
    """
    process = frappe.new_doc("Process Loan Interest Accrual")
    process.posting_date = posting_date or add_days(nowdate(), -1)
    process.loan_product = loan_product
    process.loan = loan
    process.company = company
    process.submit()
    return process.name
