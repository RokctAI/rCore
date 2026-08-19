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

# Kept in sync with api/partner.py's PARTNER_ROLE and role-exclusivity
# messages (the api/ and doctype/ sides deliberately don't import each other).
PARTNER_ROLE = "Accountability Partner"


class LMSEnrollment(Document):
    def before_insert(self):
        self.validate_owner()
        self.validate_duplicate_enrollment()
        self.validate_course_published()
        self.validate_role_exclusivity()

    def validate_owner(self):
        if self.owner != self.member:
            self.owner = self.member

    def validate_duplicate_enrollment(self):
        if frappe.db.exists("LMS Enrollment", {"course": self.course, "member": self.member}):
            frappe.throw(_("Student is already enrolled in this course."))

    def validate_course_published(self):
        published = frappe.db.get_value("LMS Course", self.course, "published")
        if not published and "System Manager" not in frappe.get_roles(frappe.session.user):
            frappe.throw(_("You cannot enroll in an unpublished course."))

    def validate_role_exclusivity(self):
        # Role exclusivity (open-decisions-log #23): one User is never both
        # personas. An enrolment is a student footprint, so it may never be
        # written for an accountability-partner account — enforced at the
        # doctype layer so desk/admin writes and any future endpoint obey the
        # same rule as the api/ paths.
        if frappe.db.exists("Has Role", {"parent": self.member, "role": PARTNER_ROLE}):
            frappe.throw(
                _(
                    "This account is an accountability partner and can't also join as "
                    "a student. Students need their own separate account."
                )
            )
