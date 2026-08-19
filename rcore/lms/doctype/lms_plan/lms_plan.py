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

"""One purchasable subscription plan (owner's instruction, 2026-08-13:
"sub plans should be configurable").

These records ARE the plan catalog: rlms.api.billing.plans() lists the
active ones and the plan-aware checkouts charge each record's own price —
runtime code reads the records, never constants. The documented launch
rates are seeded once by rlms.api.billing when no plan records exist
(rlms.plan_rules.default_plans); after that, editing these records is how
prices, terms, programme windows and availability change.

Kinds (rlms.plan_rules): Recurring (months >= 1), One-Off Programme (the
upcoming programme window on this record — the Holiday Programme), and
Per Lesson (a once-off charge for one attended lesson).
"""

import frappe
from frappe import _
from frappe.model.document import Document

_ONE_OFF_KINDS = ("One-Off Programme", "Per Lesson")


class LMSPlan(Document):
    def validate(self):
        self.plan_key = (self.plan_key or "").strip().lower().replace(" ", "-")
        if not self.plan_key:
            frappe.throw(_("A plan needs a plan key."))
        months = self.months or 0
        if self.kind == "Recurring" and months < 1:
            frappe.throw(_("A recurring plan needs at least one month."))
        if self.kind in _ONE_OFF_KINDS and months != 0:
            frappe.throw(
                _("A {0} plan is one-off — months must be 0.").format(self.kind)
            )
        # An active plan with no price would make checkout invent a number,
        # which #47 forbids. Inactive drafts (e.g. the seeded per-lesson
        # plan, whose rate no document defines) may hold price 0 until the
        # owner sets one and activates.
        if self.active and (self.price or 0) <= 0:
            frappe.throw(_("An active plan needs a positive price."))
        if (
            self.window_start
            and self.window_end
            and frappe.utils.getdate(self.window_end)
            < frappe.utils.getdate(self.window_start)
        ):
            frappe.throw(_("A programme window cannot end before it starts."))
