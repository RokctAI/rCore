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


class LoanRestructure(Document):
    """
    Polaris's own Loan Restructure doctype - forked from Frappe Lending's
    `Loan Restructure` (Phase 4), trimmed hard: upstream's real controller is
    dominated by unaccrued-interest/DPD/NPA fields that only matter once
    interest accrual exists (Phase 5) - none of it is written by
    `RokctAI_frontend`'s `lifecycle.ts:createLoanRestructure`, which only ever
    sends restructure_type/date/reason/new_term_months/new_interest_rate and
    submits immediately with status "Initiated".

    `on_submit` only applies the new terms to the Loan when status is already
    "Approved" at submit time - since the frontend always submits with
    "Initiated", new terms are NOT applied automatically today. There's no
    separate approval action anywhere in rlending or RokctAI_frontend to flip
    status to "Approved" after creation - that's a real gap, not something
    this doctype can invent evidence for. Flagged in the Phase 4 report.
    """

    def validate(self):
        if not frappe.db.exists("Loan", self.loan):
            frappe.throw(_("Loan {0} does not exist").format(self.loan))

    def on_submit(self):
        if self.status == "Approved":
            self.apply_new_terms()

    def apply_new_terms(self):
        loan = frappe.get_doc("Loan", self.loan)
        if self.new_rate_of_interest:
            loan.db_set("rate_of_interest", self.new_rate_of_interest)
        if self.new_repayment_period_in_months:
            loan.db_set("repayment_periods", self.new_repayment_period_in_months)
        if self.new_monthly_repayment_amount:
            loan.db_set("monthly_repayment_amount", self.new_monthly_repayment_amount)
