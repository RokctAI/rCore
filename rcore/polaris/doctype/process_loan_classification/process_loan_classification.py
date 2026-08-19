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
from frappe.utils import date_diff, getdate, nowdate

from importlib import import_module

# Doctype trees compose verbatim (no rcore substitution), so the
# composed "<app>.polaris" package root is derived from __name__ at runtime.
_base = __name__.split(".doctype.")[0]
get_classification_for_dpd = import_module(
    _base + ".doctype.loan_classification_range.loan_classification_range"
).get_classification_for_dpd
trigger_repossession_flag = import_module(
    _base + ".doctype.pledged_asset.pledged_asset"
).trigger_repossession_flag


def get_days_past_due(loan_name, posting_date):
    """
    Adapted from Frappe Lending's DPD calculation (loan.py:
    update_days_past_due_in_loans). Upstream computes DPD from the oldest
    unpaid EMI row in a Loan Repayment Schedule; this fork has no EMI
    schedule (see loan_interest_accrual.py's note - nothing in rlending or
    RokctAI_frontend generates one), so it substitutes the oldest unpaid
    `Loan Demand` row instead, using `demand_date` the same way upstream
    uses the EMI's `demand_date`. Same shape of calculation, different
    source of "what's overdue."
    """
    oldest_unpaid = frappe.db.get_value(
        "Loan Demand",
        {"loan": loan_name, "docstatus": 1, "outstanding_amount": (">", 0)},
        "demand_date",
        order_by="demand_date asc",
    )
    if not oldest_unpaid:
        return 0

    days_past_due = date_diff(getdate(posting_date), getdate(oldest_unpaid)) + 1
    return max(0, days_past_due)


def update_loan_classification(loan_name, posting_date):
    loan = frappe.get_doc("Loan", loan_name)

    days_past_due = get_days_past_due(loan_name, posting_date)
    threshold = frappe.db.get_value(
        "Loan Product", loan.loan_product, "days_past_due_threshold_for_npa"
    ) or 0
    is_npa = 1 if (threshold and days_past_due > threshold) else 0
    is_written_off = loan.status == "Written Off"

    classification_code, classification_name = get_classification_for_dpd(
        days_past_due, loan.company, is_written_off=is_written_off
    )

    loan.db_set("days_past_due", days_past_due)
    loan.db_set("is_npa", is_npa)
    loan.db_set("classification_code", classification_code)
    loan.db_set("classification_name", classification_name)

    if is_npa and loan.is_secured_loan:
        # Secured-lending-brief.md: NPA classification is the TRIGGER (signal),
        # not the repossession itself - trigger_repossession_flag() only flags
        # the Pledged Asset for review, it never executes repossession.
        trigger_repossession_flag(loan_name)


class ProcessLoanClassification(Document):
    """
    Polaris's own Process Loan Classification doctype - forked from Frappe
    Lending's `Process Loan Classification` orchestrator (Phase 5). Real DPD/
    NPA classification math is ported in spirit (day-count against the
    oldest overdue amount, threshold lookup, range-based classification
    lookup) but adapted to run against `Loan Demand` instead of the
    EMI-schedule infrastructure this fork never built - see
    get_days_past_due()'s docstring for the reasoning.
    """

    def validate(self):
        if not self.posting_date:
            self.posting_date = nowdate()

    def on_submit(self):
        filters = {
            "docstatus": 1,
            "status": ("in", ["Disbursed", "Active", "Written Off", "Settled", "Closed"]),
        }
        if self.loan:
            filters["name"] = self.loan
        if self.loan_product:
            filters["loan_product"] = self.loan_product

        loan_names = frappe.get_all("Loan", filters=filters, pluck="name")

        for loan_name in loan_names:
            try:
                update_loan_classification(loan_name, self.posting_date)
            except Exception:
                frappe.log_error(
                    title="Process Loan Classification Error",
                    message=frappe.get_traceback(),
                    reference_doctype="Loan",
                    reference_name=loan_name,
                )

        self.db_set("status", "Completed")


def create_process_loan_classification(posting_date=None, loan_product=None, loan=None):
    """Whitelisted entry point matching upstream's real function shape."""
    process = frappe.new_doc("Process Loan Classification")
    process.posting_date = posting_date or nowdate()
    process.loan_product = loan_product
    process.loan = loan
    process.submit()
    return process.name
