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
get_pending_principal_amount = import_module(
    __name__.split(".doctype.")[0] + ".doctype.loan_repayment.loan_repayment"
).get_pending_principal_amount


class LoanWriteOff(Document):
    """
    Polaris's own Loan Write Off doctype - forked from Frappe Lending's
    `Loan Write Off` (Phase 3). Plain Document, no GL posting (Phase 0
    decision) - `on_submit` marks the linked Loan's outstanding principal as
    settled via write-off rather than posting a reversal GL entry.
    """

    def validate(self):
        if not self.write_off_amount:
            frappe.throw(_("Write Off Amount is mandatory"))
        if not frappe.db.exists("Loan", self.loan):
            frappe.throw(_("Loan {0} does not exist").format(self.loan))

    def on_submit(self):
        loan = frappe.get_doc("Loan", self.loan)
        loan.db_set("written_off_amount", flt(loan.written_off_amount) + flt(self.write_off_amount))
        loan.db_set("total_principal_paid", flt(loan.total_principal_paid) + flt(self.write_off_amount))
        loan.db_set("status", "Written Off")
        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))

    def on_cancel(self):
        loan = frappe.get_doc("Loan", self.loan)
        loan.db_set("written_off_amount", flt(loan.written_off_amount) - flt(self.write_off_amount))
        loan.db_set("total_principal_paid", flt(loan.total_principal_paid) - flt(self.write_off_amount))
        loan.db_set("outstanding_amount", get_pending_principal_amount(loan))
