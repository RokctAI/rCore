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


class LoanTransfer(Document):
    """
    Polaris's own Loan Transfer doctype - forked from Frappe Lending's
    `Loan Transfer` (Phase 4). Plain Document. `on_submit` moves each listed
    Loan's `branch` field from `from_branch` to `to_branch` - the actual
    effect a branch transfer is supposed to have, and the only one evidenced
    by `RokctAI_frontend`'s `transfer.ts` (which reads `Loan.branch` via
    `getLoansByBranch` to build the transfer candidate list in the first
    place).
    """

    def validate(self):
        if not self.loans:
            frappe.throw(_("At least one Loan is required"))
        for row in self.loans:
            if not frappe.db.exists("Loan", row.loan):
                frappe.throw(_("Loan {0} does not exist").format(row.loan))

    def on_submit(self):
        for row in self.loans:
            frappe.db.set_value("Loan", row.loan, "branch", self.to_branch)

    def on_cancel(self):
        for row in self.loans:
            frappe.db.set_value("Loan", row.loan, "branch", self.from_branch)
