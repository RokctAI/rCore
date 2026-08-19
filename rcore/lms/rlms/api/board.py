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

"""The Board's coverage endpoint (decision #32) — queries only, judgement in
rlms.board_coverage (the api-vs-pure split every rlms feature uses)."""

import frappe
from frappe.utils import now_datetime

from .. import board_coverage


def _enrolled_course(user, subject):
    """The user's enrolled published course for [subject], preferring one
    matching their profile grade (a course whose grade is 0/empty is
    grade-agnostic and always eligible — same reading as course.list_courses).
    Returns (course_row, enrollment_name) or (None, None)."""
    enrollments = frappe.get_all(
        "LMS Enrollment", {"member": user}, ["name", "course"]
    )
    if not enrollments:
        return None, None
    courses = frappe.get_all(
        "LMS Course",
        {
            "name": ["in", [e.course for e in enrollments]],
            "subject": subject,
            "published": 1,
        },
        ["name", "grade"],
    )
    if not courses:
        return None, None

    grade = frappe.db.get_value("LMS Student Profile", {"user": user}, "grade")
    if grade:
        graded = [c for c in courses if c.grade and int(c.grade) == int(grade)]
        if graded:
            courses = graded

    course = courses[0]
    enrollment = next(e.name for e in enrollments if e.course == course.name)
    return course, enrollment


@frappe.whitelist()
def coverage(subject):
    """The session user's Board term for [subject] — the dict the client's
    BoardTerm.fromJson parses (contract in board_coverage's docstring).

    None when the user has no enrolled published course for the subject or
    the course has no lessons: the client then shows the honest coming-soon
    state (decision #47 — never demo data in a real build).
    """
    user = frappe.session.user
    course, _enrollment = _enrolled_course(user, subject)
    if not course:
        return None

    chapters = frappe.get_all(
        "Course Chapter",
        {"course": course.name},
        ["name", "title", "sequence"],
    )
    lessons = frappe.get_all(
        "Course Lesson",
        {"course": course.name},
        ["name", "chapter", "title", "sequence", "session_id"],
    )

    completed = frappe.get_all(
        "LMS Course Progress",
        {"course": course.name, "member": user, "is_complete": 1},
        pluck="lesson",
    )

    session_ids = [l.session_id for l in lessons if l.session_id]
    attended = (
        frappe.get_all(
            "LMS Attendance Event",
            {
                "student": user,
                "session_id": ["in", session_ids],
                "outcome": "Attended",
            },
            pluck="session_id",
        )
        if session_ids
        else []
    )
    session_schedule = {
        row.session_id: (
            frappe.utils.get_datetime(row.scheduled_at) if row.scheduled_at else None
        )
        for row in (
            frappe.get_all(
                "Replay Session",
                {"session_id": ["in", session_ids]},
                ["session_id", "scheduled_at"],
            )
            if session_ids
            else []
        )
    }

    # Cohort pace: the OTHER students enrolled in the same course, progress
    # percentages only — reduced to an unranked band range by the pure module.
    cohort_progress = frappe.get_all(
        "LMS Enrollment",
        {"course": course.name, "member": ["!=", user]},
        pluck="progress",
    )

    return board_coverage.build_term(
        subject_label=subject,
        chapters=chapters,
        lessons=lessons,
        completed_lessons=set(completed),
        attended_session_ids=set(attended),
        session_schedule=session_schedule,
        cohort_progress=cohort_progress,
        now=now_datetime(),
    )
