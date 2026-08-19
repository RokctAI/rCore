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

"""One covered stretch of a student's subscription (product log #27). The
canonical answer to "which periods was this student subscribed" — the
back-catalog entitlement rule ("full lessons only from periods the
subscription was active") and the skills rule ("active subscriber, always")
both resolve from these rows via rlms.entitlements.

Written ONLY by server-side flows (payment completion, admin backfill) —
never by the student's own session; a student who could write their own
periods could grant themselves the whole back-catalog.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class LMSSubscriptionPeriod(Document):
    def before_insert(self):
        # if_owner read permission: the student may SEE their own coverage.
        if self.student and self.owner != self.student:
            self.owner = self.student

    def validate(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            frappe.throw(_("A subscription period cannot end before it starts."))
