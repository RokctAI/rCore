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

"""Sponsor-facing dashboard + packaged CSI outcome report (#42 item 3).

The productized sponsor channel over the wallet/sponsor ledger #33/#34
already write. Two endpoints, both scoped to the CALLER as the sponsor —
no student argument exists, so there is nothing to permission-check beyond
the session itself: a caller can only ever read the aggregate outcomes of
learners their own billing rows funded.

PRIVACY RULE (hard requirement of the channel): sponsors see AGGREGATE
progress — counts, rates, averages, distributions. No per-learner names,
no per-learner rows leave this module. The funded-cohort membership list is
used server-side to scope queries and is never returned.

All aggregation maths lives in the frappe-free rlms.sponsor_report_rules
(unit-tested standalone, billing_rules.py-style); this layer only queries
the doctypes the weekly report already reads (partner.weekly_report's exact
sources: Course Lesson + Replay Session for the timetable denominator,
LMS Attendance Event, LMS Lesson Quiz Result) and feeds plain rows in.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, nowdate

from .. import sponsor_report_rules as rules

# The dashboard's live window: the last 30 days, a month-at-a-glance.
_DASHBOARD_WINDOW_DAYS = 30

# The packaged report's default period: the last 90 days — a CSI funder
# reports quarterly, not weekly (#42 item 3's "reporting period beyond
# weekly").
_DEFAULT_REPORT_DAYS = 90


def _billing_rows(sponsor):
    """The sponsor's own ledger rows — the cohort's source of truth. The
    payer's self-checkout rows (payer == student) are excluded up front: a
    self-paying account is not its own sponsored learner."""
    return frappe.get_all(
        "LMS Billing Record",
        {"payer": sponsor, "student": ["!=", sponsor]},
        ["student", "amount", "charged_at"],
    )


def _timetable():
    """The broadcast timetable join the weekly report uses: lessons that
    carry a session_id, plus the subject each lesson belongs to (LMS
    Course.subject, falling back to the course/lesson title) for the
    per-subject readiness grouping."""
    lesson_rows = frappe.get_all(
        "Course Lesson",
        {"session_id": ["is", "set"]},
        ["name", "title", "session_id", "course"],
    )
    courses = sorted({r.course for r in lesson_rows if r.course})
    course_rows = (
        frappe.get_all(
            "LMS Course", {"name": ["in", courses]}, ["name", "subject", "title"]
        )
        if courses
        else []
    )
    subject_of_course = {c.name: (c.subject or c.title) for c in course_rows}
    subject_by_lesson = {
        r.name: subject_of_course.get(r.course) or r.title for r in lesson_rows
    }
    return lesson_rows, subject_by_lesson


def _scheduled_times(session_ids, start_dt, end_dt):
    """When the timetable's sessions aired inside the window."""
    if not session_ids:
        return []
    return [
        r.scheduled_at
        for r in frappe.get_all(
            "Replay Session",
            {
                "session_id": ["in", session_ids],
                "scheduled_at": ["between", [start_dt, end_dt]],
            },
            ["scheduled_at"],
        )
    ]


def _cohort_events(students, start_dt=None, end_dt=None):
    """The cohort's synced attendance events, optionally windowed."""
    filters = {"student": ["in", students]}
    if start_dt and end_dt:
        filters["occurred_at"] = ["between", [start_dt, end_dt]]
    return frappe.get_all(
        "LMS Attendance Event", filters, ["outcome", "occurred_at", "data_used_mb"]
    )


def _cohort_quiz_rows(students, lesson_names, start_dt, end_dt):
    """The cohort's quiz results inside the window, shaped for the pure
    module (creation exposed as "at" for the improvement arc)."""
    if not lesson_names:
        return []
    rows = frappe.get_all(
        "LMS Lesson Quiz Result",
        {
            "lesson": ["in", lesson_names],
            "member": ["in", students],
            "creation": ["between", [start_dt, end_dt]],
        },
        ["lesson", "outcome", "creation"],
    )
    return [
        {"lesson": r.lesson, "outcome": r.outcome, "at": r.creation} for r in rows
    ]


def _empty_rollups():
    return {
        "attendance": rules.attendance_rollup([], 0, 0),
        "engagement": rules.engagement_rollup([]),
        "readiness_by_subject": {},
    }


@frappe.whitelist()
def sponsor_dashboard():
    """The live cohort rollup for the logged-in sponsor: how many learners
    their funding reaches, how many hold active coverage today, what the
    funding cost (all-time and this month), and the cohort's last-30-days
    attendance / engagement / per-subject readiness. Aggregates only.

    A caller with no billing rows gets the empty-but-well-formed shape
    (zero learners, zero rates) — a new sponsor account is an empty
    dashboard, not an error page."""
    sponsor = frappe.session.user
    billing = _billing_rows(sponsor)
    students = rules.funded_students(billing, sponsor=sponsor)

    today = getdate(nowdate())
    empty = _empty_rollups()
    if not students:
        return {
            "students_funded": 0,
            "active_coverage": 0,
            "total_spend": 0.0,
            "month_spend": 0.0,
            "window_days": _DASHBOARD_WINDOW_DAYS,
            "total_data_used_mb": 0.0,
            **empty,
        }

    periods = frappe.get_all(
        "LMS Subscription Period",
        {"student": ["in", students], "source": f"sponsor:{sponsor}"},
        ["student", "start_date", "end_date"],
    )

    end_dt = get_datetime(add_days(today, 1))
    start_dt = get_datetime(add_days(today, -_DASHBOARD_WINDOW_DAYS))
    month_start = today.replace(day=1)

    lesson_rows, subject_by_lesson = _timetable()
    scheduled = _scheduled_times(
        [r.session_id for r in lesson_rows], start_dt, end_dt
    )
    window_events = _cohort_events(students, start_dt, end_dt)
    quiz_rows = _cohort_quiz_rows(
        students, [r.name for r in lesson_rows], start_dt, end_dt
    )
    all_events = _cohort_events(students)

    return {
        "students_funded": len(students),
        "active_coverage": rules.coverage_count(periods, today),
        "total_spend": rules.spend_total(billing),
        "month_spend": rules.spend_in_period(billing, month_start, today),
        "window_days": _DASHBOARD_WINDOW_DAYS,
        "attendance": rules.attendance_rollup(
            window_events, len(scheduled), len(students)
        ),
        "engagement": rules.engagement_rollup(quiz_rows),
        "readiness_by_subject": rules.readiness_by_subject(
            quiz_rows, subject_by_lesson
        ),
        "total_data_used_mb": rules.total_data_used_mb(all_events),
    }


@frappe.whitelist()
def sponsor_outcome_report(period_start=None, period_end=None):
    """The packaged CSI outcome report for the logged-in sponsor: one
    self-contained aggregate the app renders and shares as-is. Defaults to
    the last 90 days — the CSI-framed period beyond weekly; a caller may
    pass any [period_start, period_end] (a quarter, a funding year).

    Contents, all cohort-level aggregates: period bounds, learners funded,
    spend inside the period, the attendance rollup, engagement, per-subject
    readiness_percent (#42 item 5's currency), the early-vs-late improvement
    arc, and the month-by-month attendance trend."""
    sponsor = frappe.session.user

    end = getdate(period_end) if period_end else getdate(nowdate())
    start = (
        getdate(period_start)
        if period_start
        else getdate(add_days(end, -_DEFAULT_REPORT_DAYS))
    )
    if start > end:
        frappe.throw(_("The report period must start before it ends."))

    billing = _billing_rows(sponsor)
    students = rules.funded_students(billing, sponsor=sponsor)

    base = {
        "period_start": str(start),
        "period_end": str(end),
        "students_funded": len(students),
        "students_funded_in_period": rules.students_funded_in_period(
            billing, start, end, sponsor=sponsor
        ),
        "spend_in_period": rules.spend_in_period(billing, start, end),
    }
    if not students:
        return {
            **base,
            **_empty_rollups(),
            "improvement_arc": rules.improvement_arc(
                [], get_datetime(start), get_datetime(end)
            ),
            "monthly_trend": rules.monthly_attendance_trend([], [], 0, start, end),
            "data_used_mb": 0.0,
        }

    start_dt = get_datetime(start)
    end_dt = get_datetime(add_days(end, 1))

    lesson_rows, subject_by_lesson = _timetable()
    scheduled = _scheduled_times(
        [r.session_id for r in lesson_rows], start_dt, end_dt
    )
    events = _cohort_events(students, start_dt, end_dt)
    quiz_rows = _cohort_quiz_rows(
        students, [r.name for r in lesson_rows], start_dt, end_dt
    )

    return {
        **base,
        "attendance": rules.attendance_rollup(events, len(scheduled), len(students)),
        "engagement": rules.engagement_rollup(quiz_rows),
        "readiness_by_subject": rules.readiness_by_subject(
            quiz_rows, subject_by_lesson
        ),
        "improvement_arc": rules.improvement_arc(quiz_rows, start_dt, end_dt),
        "monthly_trend": rules.monthly_attendance_trend(
            events, scheduled, len(students), start, end
        ),
        "data_used_mb": rules.total_data_used_mb(events),
    }
