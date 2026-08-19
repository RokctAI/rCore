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

"""Rollover last-year comparison baseline (decision #31) — frappe-free pure
module.

The rollover gate preserves last year's records; the progress card shows
them as the comparison baseline for a REPEATING student ("Last year 5% ·
Current 40%"). This module does the COMPUTING over plain event tuples;
api/student.py does the querying — the same split as alert_rules /
entitlements / time_gates, which is what makes the maths unit-testable
without a bench/site.

Definitions mirror the client's `AttendanceSummary` exactly (lms_sdk's
student_profile_models.dart), so server and on-device numbers can never
disagree about what a rate means:

- "scheduled" = every attendance event in the window (attended + skipped —
  the ledger only has a row when a session was on the student's schedule);
- "attended" = events with the "Attended" outcome;
- rate = attended * 100 / scheduled, rounded, 0 when nothing was scheduled.

Per-window rates compare like with like (decision #31's collapsed-card
inline figures): each ProfileWindow (day/week/month) is anchored at "this
moment, one year ago" and bounded exactly the way the client's
`ProfileNotifier._summaryFor` bounds the current side — same calendar day,
Monday-start week, calendar month — just shifted a year back. So the "day"
comparison is the same date last year, not December 31st.
"""

from datetime import date, datetime, timedelta

#: `LMS Attendance Event.outcome` label counted as attended; everything
#: else in the ledger is a skip variant.
ATTENDED = "Attended"

#: The client's ProfileWindow names, verbatim (rates_by_window keys).
WINDOWS = ("day", "week", "month")


def year_anchor(now, year):
    """[now] transposed into [year] — the like-for-like anchor the window
    rates are computed around. Feb 29 maps to Feb 28 when [year] is not a
    leap year (the one date with no counterpart)."""
    try:
        return now.replace(year=year)
    except ValueError:
        return now.replace(year=year, day=28)


def window_bounds(anchor, window):
    """The [from, to) datetime bounds of [window] around [anchor], mirroring
    the client's ProfileNotifier._summaryFor: day = the anchor's calendar
    day; week = Monday-start week containing the anchor; month = the
    anchor's calendar month — each running up to the day AFTER the anchor,
    exactly as the client bounds the current side at "now + 1 day"."""
    day_start = datetime(anchor.year, anchor.month, anchor.day)
    if window == "day":
        start = day_start
    elif window == "week":
        start = day_start - timedelta(days=anchor.weekday())
    elif window == "month":
        start = datetime(anchor.year, anchor.month, 1)
    else:
        raise ValueError(f"Unknown window: {window}")
    return start, day_start + timedelta(days=1)


def attendance_rate(events, start, end):
    """Rounded attendance percentage over [start, end); None when the window
    holds no events at all (the client then falls back to the overall rate —
    LastYearBaseline.rateFor's contract)."""
    in_window = [o for at, o in events if start <= at < end]
    if not in_window:
        return None
    attended = sum(1 for o in in_window if o == ATTENDED)
    return round(attended * 100 / len(in_window))


def year_baseline(events, quizzes_skipped, year, now):
    """The wire-shape baseline dict for [year], or None when the student has
    no attendance ledger for that year (no baseline beats a fabricated 0% —
    the client keeps its own fallback).

    [events] is the student's ledger as (occurred_at datetime, outcome
    label) pairs — ANY range is fine, only [year]'s rows count.
    [quizzes_skipped] is pre-counted by the caller (a COUNT query, not a row
    fetch). [now] is the server clock, used only to anchor the per-window
    like-for-like slices.

    Keys mirror lms_sdk's LastYearBaseline.fromJson exactly.
    """
    year_start = datetime(year, 1, 1)
    year_end = datetime(year + 1, 1, 1)
    in_year = [(at, o) for at, o in events if year_start <= at < year_end]
    if not in_year:
        return None

    attended = sum(1 for _, o in in_year if o == ATTENDED)
    anchor = year_anchor(now, year)
    rates = {}
    for window in WINDOWS:
        start, end = window_bounds(anchor, window)
        rate = attendance_rate(in_year, start, end)
        if rate is not None:
            rates[window] = rate

    return {
        "year": year,
        "attendance_rate_percent": round(attended * 100 / len(in_year)),
        "rates_by_window": rates,
        "sessions_attended": attended,
        "sessions_scheduled": len(in_year),
        "quizzes_skipped": int(quizzes_skipped or 0),
    }
