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

"""Pure student/partner role-exclusivity rule (open-decisions-log #23).

Deliberately frappe-free: `partner.py` does the querying (which roles a user
already holds) and the throwing (the error surfaced to the API caller), this
module does the DECIDING. Keeping the rule free of frappe imports is what
makes it unit-testable without a bench/site — same convention as
`alert_rules.py` (see SDK_README §4).

The rule (decision #23): the two personas are mutually exclusive. A user
account that is already a STUDENT may not also become someone's accountability
PARTNER, and an account that is already a PARTNER may not join as a STUDENT.
One User is never both personas at once.

Enforced at EVERY write path where a user newly takes on a persona, not just
the link-binding ones:

- partner-side bindings: `accept_invite` and `invite_student`/`invite`
  creation (partner.py). partner.py evaluates BOTH sides of every link
  binding — the party taking on the new persona AND the party already on the
  other end — so a pre-existing corruption on either side is caught rather
  than propagated.
- student-side acquisitions: `redeem_student_invite` (partner.py), grade/
  school/maths-track profile capture (api/student.py), and course enrolment
  (api/course.py `enroll`).
- the doctype layer (LMS Student Profile, LMS Enrollment, LMS Partner Link
  validate hooks) re-enforces the same rule with its own frappe queries, so
  desk/admin writes and any future endpoint obey it too. Doctype code
  deliberately doesn't import this module (api/ and doctype/ never
  cross-import in this workspace) — its checks are kept in sync by comment.
"""

#: The two personas, used both as the [binding] argument (what the user is
#: about to become) and as the returned conflict code (the existing role that
#: blocks the binding).
STUDENT = "student"
PARTNER = "partner"

#: No conflict — the binding is clean.
ALLOWED = None


def conflicting_role(binding, is_student, is_partner):
    """Decide whether binding a user into a new persona breaks exclusivity.

    [binding] is the persona the user is about to take on: [STUDENT] (they are
    becoming the learner on a link) or [PARTNER] (they are becoming the
    accountability partner). [is_student]/[is_partner] describe the personas
    the user ALREADY holds, as plain booleans the caller looked up.

    Returns [ALLOWED] when the binding is clean, or the existing role
    ([STUDENT] or [PARTNER]) that blocks it. Taking on a persona the user
    already holds is never a conflict (a parent accepting a second child's
    invite is still just a partner) — only holding the OPPOSITE persona is.
    """
    if binding == PARTNER and is_student:
        return STUDENT
    if binding == STUDENT and is_partner:
        return PARTNER
    return ALLOWED


def has_student_footprint(has_grade_profile, has_enrollment, is_linked_student):
    """Whether a user counts as holding the STUDENT persona at all.

    The single definition of student-ness the guard measures against: a grade
    profile (captured at onboarding), a course enrolment, or being the learner
    on an Active partner link. ANY ONE is enough — the guard only needs to
    know the persona exists, not how far it's progressed. The caller looks up
    the three facts (frappe queries in partner.py); this rule owns which facts
    constitute the persona, so the definition can't drift per call site.
    """
    return bool(has_grade_profile or has_enrollment or is_linked_student)
