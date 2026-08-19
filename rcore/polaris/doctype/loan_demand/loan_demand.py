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


class LoanDemand(Document):
    """
    Polaris's own Loan Demand doctype - forked from Frappe Lending's
    `Loan Demand` (Phase 3), trimmed to what `RokctAI_frontend`'s
    `demand.ts` actually creates: an ad-hoc Penalty/Charges demand against a
    Loan. The upstream doctype's EMI-schedule-generation role (tied to
    `Process Loan Demand` and the repayment schedule) is out of scope - Phase
    5/interest-accrual territory, not exercised by any code path today.
    """

    def validate(self):
        if not self.demand_amount:
            frappe.throw(_("Demand Amount is mandatory"))
        if not self.outstanding_amount:
            self.outstanding_amount = self.demand_amount

    def on_submit(self):
        pass

    def on_cancel(self):
        pass
