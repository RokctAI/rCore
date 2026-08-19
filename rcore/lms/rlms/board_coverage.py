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

"""The Board's real coverage source (decision #32) — frappe-free pure module.

Decision #32 made the Board a per-subject data displayer opened from an
enrolled subject's card, and left "a real per-subject coverage source is
still needed". This module IS that source's judgement half: api/board.py
owns the queries (chapters, lessons, progress, attendance, replay schedule,
cohort enrolments) and calls [build_term] for the assembly, mirroring the
api-vs-pure split every other rlms feature uses (SDK_README "Testable
Backend Logic" — no frappe import here, unit-tested standalone).

The output dict is the ONE JSON contract with the client's BoardTerm model
(lms/dart .../domain/models/board_models.dart — keep the two in sync):

    {
      "label": "Term 3 · Mathematics",
      "cohort_low": 12 | null,      # band counts, never per-student data
      "cohort_high": 19 | null,
      "topics": [
        {"name": "...", "live_now": false,
         "bands": ["covered" | "current" | "upcoming", ...]},
        ...
      ]
    }

Documented choices (owner-visible, revisit when better data lands):

- BANDS ARE LESSONS: one band per Course Lesson, in chapter order then
  lesson order (sequence, then name — the same ordering api/course.py's
  get_course_content serves). No new data model, exactly as the Board's
  design note promised.
- COVERED means the student finished the lesson (LMS Course Progress
  is_complete=1) OR attended its live session (LMS Attendance Event
  'Attended') — either is honest coverage; requiring both would punish a
  student who watched live but never replayed.
- CURRENT is the FIRST non-covered band in curriculum order — the camera
  sits at the first gap. All later non-covered bands are upcoming. A fully
  covered term simply has no current band.
- LIVE_NOW (per topic) means a lesson's Replay Session is scheduled within
  [scheduled_at, scheduled_at + LIVE_NOW_WINDOW) of now. 90 minutes, NOT
  time_gates.LIVE_SESSION_WINDOW's 3 hours: that serving gate errs long
  because locking a student out mid-lesson is the harm that matters, while
  this is a display chip where claiming "LIVE NOW" for a lesson that ended
  an hour ago is the harm. Replace with the real session length when Replay
  Session grows a duration field.
- COHORT RANGE is the 25th..75th percentile (nearest-rank) of the OTHER
  enrolled students' LMS Enrollment.progress in the same course, mapped
  onto the term's total band count. An unranked aggregate band range by
  construction — never a ranking, never per-student data (the Board's
  design excludes leaderboards). No cohort → null/null, and the client
  hides the cohort card rather than inventing a range.
- TERM LABEL approximates the SA school term from the calendar quarter
  (the SA academic year is the calendar year). Expected-coverage pacing
  against the national DBE ATP (decision #28) needs the factory repo's
  curriculum data and is deliberately NOT modelled here yet.

All datetimes are naive server-local, matching frappe's now_datetime()
(same convention as time_gates.py).
"""

from datetime import datetime, timedelta
from math import ceil

# See module docstring ("LIVE_NOW") for why this is 90 minutes and not
# time_gates.LIVE_SESSION_WINDOW.
LIVE_NOW_WINDOW = timedelta(minutes=90)

# The cohort range's percentile pair: the middle half of the class.
COHORT_LOW_PERCENTILE = 25
COHORT_HIGH_PERCENTILE = 75

COVERED = "covered"
CURRENT = "current"
UPCOMING = "upcoming"


def term_label(subject_label: str, now: datetime) -> str:
    """"Term N · Subject" — the calendar-quarter approximation of the SA
    school term (Jan–Mar = 1 … Oct–Dec = 4). See module docstring."""
    term = (now.month - 1) // 3 + 1
    return f"Term {term} · {subject_label}"


def is_live_now(scheduled_at, now: datetime) -> bool:
    """Whether a session broadcast at [scheduled_at] is on air for display
    purposes — the Board's LIVE NOW chip. None (no schedule) is never live."""
    if scheduled_at is None:
        return False
    return scheduled_at <= now < scheduled_at + LIVE_NOW_WINDOW


def cohort_band_range(cohort_progress, total_bands):
    """(low, high) band counts from the cohort's enrolment progress
    percentages, or (None, None) when there is no cohort.

    Nearest-rank 25th/75th percentiles of the raw progress values (each
    clamped to 0..100; None reads as 0 — an enrolment with no recorded
    progress is at the start, not missing), each mapped onto the term's
    band count by rounding. Aggregate band indices only — the shape the
    client's unranked "most are between band X and Y" card renders; no
    ordering or identity survives into the output.
    """
    values = sorted(
        min(max(float(p or 0), 0.0), 100.0) for p in (cohort_progress or [])
    )
    if not values or total_bands <= 0:
        return None, None

    def nearest_rank(q):
        rank = max(1, ceil(q / 100.0 * len(values)))
        return values[rank - 1]

    def to_band(percent):
        band = round(percent / 100.0 * total_bands)
        return min(max(band, 0), total_bands)

    return (
        to_band(nearest_rank(COHORT_LOW_PERCENTILE)),
        to_band(nearest_rank(COHORT_HIGH_PERCENTILE)),
    )


def _ordered(rows):
    """Catalog order: sequence then name — matching get_course_content."""
    return sorted(rows, key=lambda r: (r.get("sequence") or 0, r.get("name") or ""))


def build_term(
    subject_label,
    chapters,
    lessons,
    completed_lessons,
    attended_session_ids,
    session_schedule,
    cohort_progress,
    now,
):
    """Assemble the Board's term dict (the module-docstring contract).

    - [chapters]: dicts with name/title/sequence (Course Chapter rows).
    - [lessons]: dicts with name/chapter/title/sequence/session_id.
    - [completed_lessons]: lesson names with LMS Course Progress
      is_complete=1 for this student.
    - [attended_session_ids]: session_ids this student holds an 'Attended'
      LMS Attendance Event for.
    - [session_schedule]: session_id -> scheduled_at datetime (or None) from
      Replay Session.
    - [cohort_progress]: the OTHER enrolled students' progress percentages
      in this course (the caller excludes the requesting student).
    - [now]: server time (frappe.utils.now_datetime()).

    Returns None when the course has no lessons at all — there is no map to
    draw, and the client's honest fallback (the coming-soon state, decision
    #47) is better than an empty canvas.
    """
    completed = {c for c in (completed_lessons or []) if c}
    attended = {a for a in (attended_session_ids or []) if a}
    schedule = session_schedule or {}

    by_chapter = {}
    for lesson in _ordered(lessons or []):
        by_chapter.setdefault(lesson.get("chapter"), []).append(lesson)

    # First pass: flat covered/not-covered per lesson, in curriculum order,
    # so the single CURRENT band (the first gap) can be found globally.
    topics = []
    flat_states = []
    for chapter in _ordered(chapters or []):
        chapter_lessons = by_chapter.get(chapter.get("name"), [])
        if not chapter_lessons:
            # A chapter with no lessons has no bands — skipped rather than
            # drawn as an empty row.
            continue
        band_refs = []
        live = False
        for lesson in chapter_lessons:
            session_id = lesson.get("session_id")
            state = (
                COVERED
                if lesson.get("name") in completed
                or (session_id and session_id in attended)
                else UPCOMING
            )
            ref = {"state": state}
            band_refs.append(ref)
            flat_states.append(ref)
            if is_live_now(schedule.get(session_id), now):
                live = True
        topics.append(
            {"name": chapter.get("title") or "", "live_now": live, "bands": band_refs}
        )

    if not flat_states:
        return None

    for ref in flat_states:
        if ref["state"] != COVERED:
            ref["state"] = CURRENT
            break

    low, high = cohort_band_range(cohort_progress, len(flat_states))
    return {
        "label": term_label(subject_label, now),
        "cohort_low": low,
        "cohort_high": high,
        "topics": [
            {
                "name": t["name"],
                "live_now": t["live_now"],
                "bands": [b["state"] for b in t["bands"]],
            }
            for t in topics
        ],
    }
