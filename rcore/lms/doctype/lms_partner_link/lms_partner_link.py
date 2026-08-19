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

import frappe
from frappe import _
from frappe.model.document import Document

# Kept in sync with api/partner.py's PARTNER_ROLE, _is_student footprint
# definition (role_exclusivity.has_student_footprint), and role-exclusivity
# messages (the api/ and doctype/ sides deliberately don't import each other).
PARTNER_ROLE = "Accountability Partner"


class LMSPartnerLink(Document):
    def before_insert(self):
        # if_owner read permission: the link belongs to whichever side exists
        # at insert time — the student on a student-initiated invite, the
        # partner on a partner-initiated one (student is empty until redeemed).
        anchor = self.student or self.partner
        if anchor and self.owner != anchor:
            self.owner = anchor

    def validate(self):
        # A link can be born one-sided (pending invite), but never Active
        # without both sides resolved.
        if self.status == "Active" and not (self.student and self.partner):
            frappe.throw(_("An active partner link needs both a student and a partner."))
        if not (self.student or self.partner):
            frappe.throw(_("A partner link needs at least one side set."))
        if self.student and self.partner and self.student == self.partner:
            frappe.throw(_("A user cannot be their own accountability partner."))
        self.validate_role_exclusivity()

    def validate_role_exclusivity(self):
        # Role exclusivity (open-decisions-log #23): one User is never both
        # personas. Enforced at the doctype layer when a link goes Active —
        # the moment both personas are truly bound — so desk/admin writes obey
        # the same rule as the api/ paths (accept_invite and
        # redeem_student_invite already check both sides before saving).
        if self.status != "Active":
            return
        if frappe.db.exists("Has Role", {"parent": self.student, "role": PARTNER_ROLE}):
            frappe.throw(
                _(
                    "This account is an accountability partner and can't also join as "
                    "a student. Students need their own separate account."
                )
            )
        partner_is_student = (
            frappe.db.exists("LMS Student Profile", {"user": self.partner})
            or frappe.db.exists("LMS Enrollment", {"member": self.partner})
            or frappe.db.exists(
                "LMS Partner Link",
                {
                    "student": self.partner,
                    "status": "Active",
                    "name": ["!=", self.name],
                },
            )
        )
        if partner_is_student:
            frappe.throw(
                _(
                    "This account is registered as a student and can't also be an "
                    "accountability partner. Partners need their own separate account."
                )
            )
