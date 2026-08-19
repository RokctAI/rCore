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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""One student's subscription payment and who funded it (product log #33).

The wallet ledger (Wallet History) carries the money movement hop by hop;
this doctype is the LMS-side summary that answers "who paid for this
student's period, at what rate" in one row, without replaying the ledger.
Written only by rlms.api.billing's checkout flows.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class LMSBillingRecord(Document):
    def before_insert(self):
        # if_owner read permission: the record belongs to the PAYER — they
        # are the one entitled to see what they were charged. The student's
        # own view of coverage is LMS Subscription Period, not this row.
        if self.payer and self.owner != self.payer:
            self.owner = self.payer

    def validate(self):
        if self.amount is not None and self.amount <= 0:
            frappe.throw(_("A billing record needs a positive amount."))
        if self.period_end and self.period_start and self.period_end < self.period_start:
            frappe.throw(_("A billing period cannot end before it starts."))
