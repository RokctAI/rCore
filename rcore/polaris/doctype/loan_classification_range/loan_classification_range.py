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


class LoanClassificationRange(Document):
    def validate(self):
        if self.min_dpd_range > self.max_dpd_range:
            frappe.throw(_("Min DPD cannot be greater than Max DPD"))


def get_classification_for_dpd(days_past_due, company, is_written_off=False):
    """
    Ported from Frappe Lending's `loan.py:get_classification_code_and_name`,
    adapted to Loan Classification Range being a standalone doctype (see its
    JSON description) instead of a Company child table.
    """
    ranges = frappe.get_all(
        "Loan Classification Range",
        filters={"company": company, "is_written_off": 1 if is_written_off else 0},
        fields=["min_dpd_range", "max_dpd_range", "classification_code"],
        order_by="min_dpd_range",
    )
    for r in ranges:
        if r.min_dpd_range <= days_past_due <= r.max_dpd_range:
            classification_name = frappe.db.get_value(
                "Loan Classification", r.classification_code, "classification_name"
            )
            return r.classification_code, classification_name
    return "", ""
