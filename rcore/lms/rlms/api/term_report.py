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

"""Per-subject Term Report endpoints — the weekly report's big sibling.

Queries only; term boundaries and assembly live in rlms.term_report_rules
(the api-vs-pure split every rlms feature uses). Everything is computed
from rows the backend already tracks — LMS Attendance Event, LMS Lesson
Quiz Result, LMS Practice Attempt, LMS Course Progress, LMS Enrollment —
plus readiness_rules for the readiness component (the formula is reused,
never duplicated). No manual marks anywhere.

Two callers, one report:
- `my_term_report` — the signed-in student's own report;
- `partner_term_report` — the partner variant, permission-scoped exactly
  as partner.weekly_report is: partner._resolve_student only ever answers
  with the caller's OWN Active link (permission error otherwise).
"""

import frappe
from frappe.utils import now_datetime

from .. import readiness_rules, term_report_rules
from .practice import _bank_items
from .readiness import _subject_scores
from .partner import _resolve_student


def _subject_courses(user):
    """The user's enrolled published courses grouped by subject — the same
    grouping readiness._subject_scores walks. {subject: [course names]}."""
    enrollments = frappe.get_all("LMS Enrollment", {"member": user}, ["course"])
    if not enrollments:
        return {}
    courses = frappe.get_all(
        "LMS Course",
        {"name": ["in", [e.course for e in enrollments]], "published": 1},
        ["name", "subject"],
    )
    by_subject = {}
    for course in courses:
        if course.subject:
            by_subject.setdefault(course.subject, []).append(course.name)
    return by_subject


def _practice_outcomes_by_subject(user, window_start, window_end):
    """The member's in-term practice attempts attributed to subjects via the
    published item bank (the attempt row itself carries no subject).
    Attempts on items the bank no longer carries stay unattributed and are
    left out — honest omission over guessed attribution.
    {subject: [outcome, ...]} in chronological order."""
    rows = frappe.get_all(
        "LMS Practice Attempt",
        {"member": user, "creation": ["between", [window_start, window_end]]},
        ["item_id", "outcome"],
        order_by="creation asc",
    )
    if not rows:
        return {}
    bank = _bank_items()
    by_subject = {}
    for row in rows:
        subject = (bank.get(row.item_id) or {}).get("subject")
        if subject:
            by_subject.setdefault(subject, []).append(row.outcome)
    return by_subject


def _readiness_at(user, courses, lessons, session_ids, cutoff):
    """readiness_rules' verdict for one subject using only evidence recorded
    BEFORE [cutoff] — the "at term start" end of the report's readiness
    comparison. Same components as readiness._subject_scores, restricted in
    time; coverage is completed-lessons-before-cutoff over each course's
    lesson count (enrollment progress percentages carry no history)."""
    mastery = None
    if lessons:
        quiz_rows = frappe.get_all(
            "LMS Lesson Quiz Result",
            {
                "member": user,
                "lesson": ["in", [l.name for l in lessons]],
                "creation": ["<", cutoff],
            },
            ["outcome"],
        )
        mastery = readiness_rules.mastery_component(
            correct=sum(1 for r in quiz_rows if r.outcome == "Correct"),
            incorrect=sum(1 for r in quiz_rows if r.outcome == "Incorrect"),
            skipped=sum(1 for r in quiz_rows if r.outcome == "Skipped"),
        )

    lessons_per_course = {}
    for lesson in lessons:
        lessons_per_course[lesson.course] = lessons_per_course.get(lesson.course, 0) + 1
    completed_rows = frappe.get_all(
        "LMS Course Progress",
        {
            "member": user,
            "course": ["in", courses],
            "is_complete": 1,
            "creation": ["<", cutoff],
        },
        ["course"],
    )
    completed_per_course = {}
    for row in completed_rows:
        completed_per_course[row.course] = completed_per_course.get(row.course, 0) + 1
    percents = [
        completed_per_course.get(course, 0) * 100.0 / total
        for course, total in lessons_per_course.items()
        if total
    ]
    coverage = readiness_rules.coverage_component(percents)

    consistency = None
    if session_ids:
        events = frappe.get_all(
            "LMS Attendance Event",
            {
                "student": user,
                "session_id": ["in", session_ids],
                "occurred_at": ["<", cutoff],
            },
            ["outcome"],
        )
        consistency = readiness_rules.consistency_component(
            attended=sum(1 for e in events if e.outcome == "Attended"),
            skipped_answered=sum(1 for e in events if e.outcome == "Skipped Answered"),
            skipped_unanswered=sum(
                1 for e in events if e.outcome == "Skipped Unanswered"
            ),
        )

    return readiness_rules.readiness_score(mastery, coverage, consistency)


def _term_report(user, term=None, subject=None):
    """The full Term Report dict for [user]: the term header plus one
    subject entry per enrolled subject (or just [subject] when named)."""
    now = now_datetime()
    terms, approximate = term_report_rules.terms_for_year(now.year)
    resolved = term_report_rules.resolve_term(now.date(), terms, requested=term)
    window_start, window_end = term_report_rules.term_window(resolved)

    by_subject = _subject_courses(user)
    if subject:
        by_subject = {subject: by_subject[subject]} if subject in by_subject else {}

    readiness_now = {
        entry["subject"]: (
            {
                "score": entry["score"],
                "band": entry["band"],
                "components": entry["components"],
            }
            if entry["score"] is not None
            else None
        )
        for entry in _subject_scores(user)
    }
    practice_by_subject = _practice_outcomes_by_subject(
        user, window_start, window_end
    )

    subjects = []
    for subject_name in sorted(by_subject):
        courses = by_subject[subject_name]
        lessons = frappe.get_all(
            "Course Lesson",
            {"course": ["in", courses]},
            ["name", "title", "chapter", "course", "session_id"],
        )
        chapter_titles = {
            c.name: c.title
            for c in frappe.get_all(
                "Course Chapter", {"course": ["in", courses]}, ["name", "title"]
            )
        }

        quiz_rows = []
        if lessons:
            lesson_topic = {
                l.name: chapter_titles.get(l.chapter) or l.title for l in lessons
            }
            quiz_rows = [
                {"topic": lesson_topic.get(r.lesson), "outcome": r.outcome}
                for r in frappe.get_all(
                    "LMS Lesson Quiz Result",
                    {
                        "member": user,
                        "lesson": ["in", [l.name for l in lessons]],
                        "creation": ["between", [window_start, window_end]],
                    },
                    ["lesson", "outcome"],
                )
            ]

        session_ids = [l.session_id for l in lessons if l.session_id]
        term_events = (
            frappe.get_all(
                "LMS Attendance Event",
                {
                    "student": user,
                    "session_id": ["in", session_ids],
                    "occurred_at": ["between", [window_start, window_end]],
                },
                ["outcome"],
            )
            if session_ids
            else []
        )

        # Coverage picture is the syllabus to date, not just the term's
        # events — the Board's own framing.
        completed = frappe.get_all(
            "LMS Course Progress",
            {"member": user, "course": ["in", courses], "is_complete": 1},
            pluck="lesson",
        )
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

        subjects.append(
            term_report_rules.build_subject_term_report(
                subject=subject_name,
                attendance_outcomes=[e.outcome for e in term_events],
                quiz_rows=quiz_rows,
                practice_outcomes=practice_by_subject.get(subject_name, []),
                readiness_start=_readiness_at(
                    user, courses, lessons, session_ids, window_start
                ),
                readiness_now=readiness_now.get(subject_name),
                lessons=lessons,
                completed_lessons=set(completed),
                attended_session_ids=set(attended),
            )
        )

    return {
        "term": term_report_rules.term_summary(resolved, now.year, approximate),
        "subjects": subjects,
    }


@frappe.whitelist()
def my_term_report(term=None, subject=None):
    """The signed-in student's per-subject Term Report for the current term
    (or [term] 1..4 of this year). [subject] narrows to one subject."""
    return _term_report(frappe.session.user, term=term, subject=subject)


@frappe.whitelist()
def partner_term_report(student=None, term=None, subject=None):
    """Partner-side Term Report — the weekly report's big sibling on the
    partner dashboard. Permission pattern is exactly weekly_report's:
    [student] must be one of the caller's OWN Active links
    (partner._resolve_student throws a permission error otherwise)."""
    student = _resolve_student(student).student
    report = _term_report(student, term=term, subject=subject)
    report["student_name"] = (
        frappe.db.get_value("User", student, "full_name") or student
    )
    return report
