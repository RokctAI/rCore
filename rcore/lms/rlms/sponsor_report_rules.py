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

"""Sponsor/CSI outcome reporting (product log #42 item 3) — frappe-free
pure module.

The productized sponsor channel sits on the wallet/sponsor ledger #33/#34
already write: LMS Billing Record rows (who funded whom, how much, when)
and sponsor-sourced LMS Subscription Period rows (paid coverage windows).
This module is the aggregation maths for the sponsor-facing dashboard and
the packaged CSI outcome report, in the style of billing_rules.py: plain
lists/dicts in, plain dicts out, unit-tested standalone; every frappe query
stays in api/sponsor.py.

PRIVACY RULE (the sponsor-channel hard requirement): a sponsor sees the
AGGREGATE progress of the learners they fund — counts, rates, averages,
distributions. Nothing returned by these functions carries a per-learner
row or name; cohort membership stays server-side in the API layer.

Vocabulary shared with the per-student weekly report (partner.weekly_report),
aggregated across the cohort instead of resolved for one student:
  - attendance: LMS Attendance Event outcomes (Attended / Skipped Answered /
    Skipped Unanswered) against the broadcast timetable's scheduled sessions,
  - engagement: LMS Lesson Quiz Result answered-vs-skipped,
  - readiness_percent per subject: the correct-rate over answered questions,
    grouped by subject — the sponsor-report currency of #42 item 5,
  - improvement arc: early-half vs late-half of the reporting period, the
    "improvement arcs" a CSI funder reports against.
"""


def _as_date(value):
    """A date for comparison, from a date or datetime (frappe hands back
    datetimes for Datetime fields and dates for Date fields)."""
    if value is None:
        return None
    return value.date() if hasattr(value, "date") else value


def _rate_percent(part, whole):
    """Rounded percentage, 0 when the denominator is empty (an empty cohort
    or a week with no scheduled sessions must read as 0, never divide)."""
    if not whole:
        return 0
    return round(part * 100 / whole)


def funded_students(billing_rows, sponsor=None):
    """The funded cohort: distinct students across the sponsor's billing
    rows, in a stable (sorted) order. [sponsor] excludes the payer's own
    self-checkout rows (a self-paying account is not its own beneficiary).

    Returns the list of student ids — for the API layer's follow-up queries
    ONLY, never for a sponsor-facing payload (privacy rule above)."""
    seen = set()
    for row in billing_rows or []:
        student = row.get("student")
        if not student or student == sponsor:
            continue
        seen.add(student)
    return sorted(seen)


def coverage_count(period_rows, today):
    """How many distinct students hold a subscription period covering
    [today] — the sponsor's ACTIVE coverage, from the sponsor-sourced
    LMS Subscription Period rows the checkout wrote."""
    today = _as_date(today)
    covered = set()
    for row in period_rows or []:
        start = _as_date(row.get("start_date"))
        end = _as_date(row.get("end_date"))
        if start is None or end is None:
            continue
        if start <= today <= end:
            covered.add(row.get("student"))
    return len(covered)


def spend_total(billing_rows):
    """All-time spend across the sponsor's billing rows."""
    return float(sum(row.get("amount") or 0 for row in billing_rows or []))


def spend_in_period(billing_rows, period_start, period_end):
    """Spend charged within [period_start, period_end] (inclusive), by
    charged_at. Rows without a charged_at are excluded — an undated charge
    cannot honestly belong to a dated reporting period."""
    start = _as_date(period_start)
    end = _as_date(period_end)
    total = 0.0
    for row in billing_rows or []:
        charged = _as_date(row.get("charged_at"))
        if charged is None:
            continue
        if start <= charged <= end:
            total += float(row.get("amount") or 0)
    return total


def students_funded_in_period(billing_rows, period_start, period_end, sponsor=None):
    """Distinct students with a charge inside the period — the report's
    "learners funded this period" count."""
    start = _as_date(period_start)
    end = _as_date(period_end)
    in_period = []
    for row in billing_rows or []:
        charged = _as_date(row.get("charged_at"))
        if charged is None or not (start <= charged <= end):
            continue
        in_period.append(row)
    return len(funded_students(in_period, sponsor=sponsor))


def attendance_rollup(events, scheduled_sessions, cohort_size):
    """Cohort attendance against the broadcast timetable.

    [events] are the cohort's LMS Attendance Event rows in the window;
    [scheduled_sessions] is how many sessions the timetable scheduled in the
    window; the denominator is scheduled_sessions x cohort_size (every
    funded learner had that many seats to fill). The rate is capped at 100
    so late-synced duplicate events can never report an impossible rate."""
    attended = sum(1 for e in events or [] if e.get("outcome") == "Attended")
    skipped_answered = sum(
        1 for e in events or [] if e.get("outcome") == "Skipped Answered"
    )
    skipped_unanswered = sum(
        1 for e in events or [] if e.get("outcome") == "Skipped Unanswered"
    )
    scheduled_slots = (scheduled_sessions or 0) * (cohort_size or 0)
    return {
        "sessions_scheduled": scheduled_sessions or 0,
        "cohort_size": cohort_size or 0,
        "scheduled_slots": scheduled_slots,
        "attended": attended,
        "skipped_answered": skipped_answered,
        "skipped_unanswered": skipped_unanswered,
        "attendance_rate_percent": min(
            100, _rate_percent(attended, scheduled_slots)
        ),
    }


def engagement_rollup(quiz_rows):
    """Answered-vs-skipped across the cohort's quiz results, plus the
    correct-rate over what was answered — the same engagement definition the
    weekly report uses, cohort-wide."""
    answered = sum(
        1 for q in quiz_rows or [] if q.get("outcome") in ("Correct", "Incorrect")
    )
    skipped = sum(1 for q in quiz_rows or [] if q.get("outcome") == "Skipped")
    correct = sum(1 for q in quiz_rows or [] if q.get("outcome") == "Correct")
    return {
        "questions_answered": answered,
        "questions_skipped": skipped,
        "engagement_rate_percent": _rate_percent(answered, answered + skipped),
        "correct_rate_percent": _rate_percent(correct, answered),
    }


def readiness_by_subject(quiz_rows, subject_by_lesson):
    """readiness_percent per subject (#42 item 5's sponsor-report currency):
    the cohort's correct-rate over answered questions, grouped by the
    subject each lesson belongs to. [subject_by_lesson] maps lesson id ->
    subject title; a lesson without a mapping groups under its own id rather
    than being dropped."""
    answered_by_subject = {}
    correct_by_subject = {}
    for q in quiz_rows or []:
        if q.get("outcome") not in ("Correct", "Incorrect"):
            continue
        subject = subject_by_lesson.get(q.get("lesson")) or q.get("lesson")
        answered_by_subject[subject] = answered_by_subject.get(subject, 0) + 1
        if q.get("outcome") == "Correct":
            correct_by_subject[subject] = correct_by_subject.get(subject, 0) + 1
    return {
        subject: {
            "readiness_percent": _rate_percent(
                correct_by_subject.get(subject, 0), answered
            ),
            "questions_answered": answered,
        }
        for subject, answered in sorted(answered_by_subject.items())
    }


def improvement_arc(quiz_rows, period_start, period_end):
    """The period's improvement arc: split [period_start, period_end] in
    half chronologically and compare the cohort's early-half engagement and
    correct rates against the late half.

    [quiz_rows] must carry an "at" timestamp (the row's creation). Deltas
    are None when either half has no activity — a one-sided arc is "not
    enough data", never a fabricated trend."""
    midpoint = period_start + (period_end - period_start) / 2
    early = [q for q in quiz_rows or [] if q.get("at") and q["at"] < midpoint]
    late = [q for q in quiz_rows or [] if q.get("at") and q["at"] >= midpoint]
    early_roll = engagement_rollup(early)
    late_roll = engagement_rollup(late)
    early_active = (
        early_roll["questions_answered"] + early_roll["questions_skipped"]
    ) > 0
    late_active = (
        late_roll["questions_answered"] + late_roll["questions_skipped"]
    ) > 0
    two_sided = early_active and late_active
    return {
        "early": early_roll,
        "late": late_roll,
        "engagement_delta_points": (
            late_roll["engagement_rate_percent"]
            - early_roll["engagement_rate_percent"]
            if two_sided
            else None
        ),
        "correct_delta_points": (
            late_roll["correct_rate_percent"] - early_roll["correct_rate_percent"]
            if two_sided
            else None
        ),
    }


def _month_key(value):
    return (value.year, value.month)


def _iter_months(period_start, period_end):
    """Every (year, month) touched by the period, in order."""
    start = _as_date(period_start)
    end = _as_date(period_end)
    year, month = start.year, start.month
    months = []
    while (year, month) <= (end.year, end.month):
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def monthly_attendance_trend(events, scheduled_times, cohort_size, period_start, period_end):
    """Month-by-month attendance inside the reporting period — the CSI
    report's trend line (a quarterly/annual funder reads months, not weeks).

    [events] carry "outcome" + "occurred_at"; [scheduled_times] are the
    timetable's scheduled_at datetimes inside the period. Every month the
    period touches appears, zeros included — a silent month is a data point,
    not a gap in the chart."""
    months = _iter_months(period_start, period_end)
    scheduled_by_month = {}
    for t in scheduled_times or []:
        key = _month_key(_as_date(t))
        scheduled_by_month[key] = scheduled_by_month.get(key, 0) + 1
    attended_by_month = {}
    skipped_by_month = {}
    for e in events or []:
        at = e.get("occurred_at")
        if at is None:
            continue
        key = _month_key(_as_date(at))
        if e.get("outcome") == "Attended":
            attended_by_month[key] = attended_by_month.get(key, 0) + 1
        elif e.get("outcome") in ("Skipped Answered", "Skipped Unanswered"):
            skipped_by_month[key] = skipped_by_month.get(key, 0) + 1
    trend = []
    for year, month in months:
        scheduled = scheduled_by_month.get((year, month), 0)
        slots = scheduled * (cohort_size or 0)
        attended = attended_by_month.get((year, month), 0)
        trend.append(
            {
                "month": f"{year:04d}-{month:02d}",
                "sessions_scheduled": scheduled,
                "scheduled_slots": slots,
                "attended": attended,
                "skipped": skipped_by_month.get((year, month), 0),
                "attendance_rate_percent": min(100, _rate_percent(attended, slots)),
            }
        )
    return trend


def total_data_used_mb(events):
    """Total synced data usage across the cohort's attendance events — the
    on-device ledger's own numbers summed, the same source the weekly report
    reads per student."""
    return float(sum(e.get("data_used_mb") or 0 for e in events or []))
