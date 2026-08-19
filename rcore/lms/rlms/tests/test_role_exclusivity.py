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

"""Student/partner role exclusivity (open-decisions-log #23): one User is
never both personas. The rule the decision is most specific about — a student
account can't become a partner, a partner account can't become a student.

Loaded by file path rather than package import on purpose: every other python
test in this workspace imports through an `rcore` placeholder and
therefore only runs inside a composed app. role_exclusivity.py is deliberately
frappe-free, so this test runs anywhere python does — `python -m unittest`
from the repo, no bench, no site, no substitution. Same pattern as
test_alert_rules.py.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "role_exclusivity.py")
_spec = importlib.util.spec_from_file_location("rlms_role_exclusivity", _MODULE_PATH)
role_exclusivity = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(role_exclusivity)

STUDENT = role_exclusivity.STUDENT
PARTNER = role_exclusivity.PARTNER
ALLOWED = role_exclusivity.ALLOWED
conflicting_role = role_exclusivity.conflicting_role
has_student_footprint = role_exclusivity.has_student_footprint


class TestRoleExclusivity(unittest.TestCase):
    # --- both directions are rejected (the core of decision #23) ---

    def test_student_cannot_become_a_partner(self):
        # A student account accepting a partner invite is blocked; the
        # conflicting existing role reported back is STUDENT.
        self.assertEqual(
            conflicting_role(PARTNER, is_student=True, is_partner=False),
            STUDENT,
        )

    def test_partner_cannot_become_a_student(self):
        # A partner account redeeming a student invite is blocked; the
        # conflicting existing role reported back is PARTNER.
        self.assertEqual(
            conflicting_role(STUDENT, is_student=False, is_partner=True),
            PARTNER,
        )

    # --- the legitimate case: neither role held, either binding succeeds ---

    def test_fresh_account_may_become_a_partner(self):
        self.assertIs(
            conflicting_role(PARTNER, is_student=False, is_partner=False),
            ALLOWED,
        )

    def test_fresh_account_may_become_a_student(self):
        self.assertIs(
            conflicting_role(STUDENT, is_student=False, is_partner=False),
            ALLOWED,
        )

    # --- taking on a persona already held is never a conflict ---

    def test_existing_partner_may_take_a_second_student(self):
        # A parent accepting a second child's invite is still just a partner —
        # not a new persona, so no exclusivity violation.
        self.assertIs(
            conflicting_role(PARTNER, is_student=False, is_partner=True),
            ALLOWED,
        )

    def test_existing_student_binding_as_student_is_fine(self):
        # Re-binding a student as a student holds no partner role to clash
        # with (any "already have a partner" limit is enforced elsewhere).
        self.assertIs(
            conflicting_role(STUDENT, is_student=True, is_partner=False),
            ALLOWED,
        )

    # --- a corrupt account already holding BOTH still can't extend either ---

    def test_dual_role_account_is_blocked_from_partnering(self):
        # Defensive: if an account somehow already holds both, extending the
        # partner side still trips on the student role it holds.
        self.assertEqual(
            conflicting_role(PARTNER, is_student=True, is_partner=True),
            STUDENT,
        )

    def test_dual_role_account_is_blocked_from_studying(self):
        self.assertEqual(
            conflicting_role(STUDENT, is_student=True, is_partner=True),
            PARTNER,
        )


class TestStudentFootprint(unittest.TestCase):
    """What counts as holding the STUDENT persona at all — the single
    definition every guard site (partner.py's _is_student, and by kept-in-sync
    comment the doctype validators) measures against. Any one footprint is
    enough; how far the student has progressed never matters."""

    def test_no_footprint_is_not_a_student(self):
        self.assertFalse(
            has_student_footprint(
                has_grade_profile=False, has_enrollment=False, is_linked_student=False
            )
        )

    def test_grade_profile_alone_is_enough(self):
        # A brand-new student who only completed grade capture is already a
        # student — the persona exists before any enrolment does.
        self.assertTrue(
            has_student_footprint(
                has_grade_profile=True, has_enrollment=False, is_linked_student=False
            )
        )

    def test_enrollment_alone_is_enough(self):
        # A pre-grade-field account that enrolled straight into a course.
        self.assertTrue(
            has_student_footprint(
                has_grade_profile=False, has_enrollment=True, is_linked_student=False
            )
        )

    def test_active_link_alone_is_enough(self):
        # Being the learner on an Active partner link marks the persona even
        # with no profile or enrolment yet.
        self.assertTrue(
            has_student_footprint(
                has_grade_profile=False, has_enrollment=False, is_linked_student=True
            )
        )

    def test_truthy_lookup_results_count(self):
        # Callers pass frappe.db.exists results straight through — truthy row
        # names, not literal True — and the rule must read them as held.
        self.assertTrue(
            has_student_footprint(
                has_grade_profile="LMS-PROF-0001",
                has_enrollment=None,
                is_linked_student=None,
            )
        )


if __name__ == "__main__":
    unittest.main()
