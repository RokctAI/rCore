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

MIN_GRADE = 1
MAX_GRADE = 12

# Kept in sync with api/student.py's CURRICULA (the api/ and doctype/ sides
# deliberately don't import each other — same posture as the grade range).
CURRICULA = ("CAPS", "IEB", "Cambridge", "US Common Core")

# Kept in sync with api/partner.py's PARTNER_ROLE and role-exclusivity
# messages (same no-cross-import posture as the grade range above).
PARTNER_ROLE = "Accountability Partner"


class LMSStudentProfile(Document):
    def before_insert(self):
        # if_owner read permission: the profile belongs to its student.
        if self.user and self.owner != self.user:
            self.owner = self.user

    def validate(self):
        if self.grade and not (MIN_GRADE <= int(self.grade) <= MAX_GRADE):
            frappe.throw(
                _("Grade must be between {0} and {1}.").format(MIN_GRADE, MAX_GRADE)
            )
        if self.curriculum and self.curriculum not in CURRICULA:
            frappe.throw(
                _("Curriculum must be one of: {0}.").format(", ".join(CURRICULA))
            )
        self.validate_role_exclusivity()

    def validate_role_exclusivity(self):
        # Role exclusivity (open-decisions-log #23): one User is never both
        # personas. A grade profile IS the student footprint, so it may never
        # be written for an accountability-partner account — enforced at the
        # doctype layer so desk/admin writes and any future endpoint obey the
        # same rule as the api/ paths.
        if self.user and frappe.db.exists(
            "Has Role", {"parent": self.user, "role": PARTNER_ROLE}
        ):
            frappe.throw(
                _(
                    "This account is an accountability partner and can't also join as "
                    "a student. Students need their own separate account."
                )
            )
