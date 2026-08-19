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

"""Per-subject Term Report assembly — frappe-free pure module.

The Term Report is the weekly report's big sibling on the partner dashboard
(and the student's own mirror of it): one term of evidence per subject,
assembled server-side ENTIRELY from rows the backend already tracks —
attendance (LMS Attendance Event, the partner ledger's sync point),
in-lesson MCQ accuracy by topic (LMS Lesson Quiz Result), practice mastery
trend (LMS Practice Attempt), Readiness Score at term start vs now
(readiness_rules — the formula is reused, never duplicated), and Board
coverage (board_coverage's COVERED stance). No manual marks anywhere.

Split of responsibilities (the api-vs-pure split every rlms feature uses):
api/term_report.py owns the queries and permissions; this module owns term
boundaries and the report's judgement/assembly, unit-tested without a bench
(`python -m unittest tests.test_term_report_rules`). Deliberately
self-contained — no relative imports — so the test suite's
file-path-loading style (test_board_coverage.py) works unchanged; the
readiness component arrives as readiness_rules' already-computed verdicts.

TERM BOUNDARIES
---------------
The SA school year is the calendar year, split into four gazetted terms.
data/sa_school_terms.json packages the official DBE national calendar
(known_schools.json posture: verbatim official dates, one unified national
calendar since 2024 — no province split). A year absent from the file
degrades to the calendar-quarter approximation board_coverage.py already
uses, flagged `approximate` so the client can label it honestly.

"Current term" during a school holiday means the term that just ENDED — a
term report matters most right after the term closes, and there is no
evidence in a term that hasn't started.
"""

import json
import os
from datetime import date, datetime, timedelta

#: Packaged DBE term dates, resolved relative to this module so the pure
#: module stays importable by file path (test style) and inside any
#: composed app name.
TERMS_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "sa_school_terms.json")

#: Below this many in-term practice attempts the early/late trend split is
#: noise, so the report keeps the totals but claims no direction.
MIN_TREND_ATTEMPTS = 4

#: A first-half vs second-half accuracy shift smaller than this (percentage
#: points) reads as steady — practice accuracy is lumpy at term scale.
TREND_DELTA_PERCENT = 5

IMPROVING = "improving"
STEADY = "steady"
SLIPPING = "slipping"

#: Outcome labels — must match the Select options on the source doctypes.
ATTENDED = "Attended"
SKIPPED_ANSWERED = "Skipped Answered"
SKIPPED_UNANSWERED = "Skipped Unanswered"
CORRECT = "Correct"
INCORRECT = "Incorrect"
SKIPPED = "Skipped"

#: Topic bucket for quiz rows whose lesson resolves to no chapter title.
GENERAL_TOPIC = "General"

_terms_file_cache = None


def _load_terms_file():
    """The packaged term-dates file, parsed once per process. Missing or
    malformed data degrades to no gazetted years (quarter fallback), never
    an error — a broken data file must not take the report down."""
    global _terms_file_cache
    if _terms_file_cache is None:
        try:
            with open(TERMS_DATA_PATH, encoding="utf-8") as handle:
                _terms_file_cache = json.load(handle)
        except (OSError, ValueError):
            _terms_file_cache = {}
    return _terms_file_cache


def _quarter_terms(year):
    """The calendar-quarter approximation for years the file doesn't carry
    (board_coverage.term_label's reading: Jan–Mar = 1 … Oct–Dec = 4)."""
    quarters = ((1, 1, 3, 31), (4, 1, 6, 30), (7, 1, 9, 30), (10, 1, 12, 31))
    return [
        {
            "term": index + 1,
            "start": date(year, sm, sd),
            "end": date(year, em, ed),
        }
        for index, (sm, sd, em, ed) in enumerate(quarters)
    ]


def terms_for_year(year):
    """(terms, approximate) for [year]: the gazetted DBE terms when the
    packaged file carries the year, else the quarter approximation flagged
    approximate. Terms are dicts {"term": 1..4, "start": date, "end": date},
    ordered."""
    raw = (_load_terms_file().get("years") or {}).get(str(year))
    if not raw:
        return _quarter_terms(year), True
    terms = []
    try:
        for row in raw:
            terms.append(
                {
                    "term": int(row["term"]),
                    "start": date.fromisoformat(row["start"]),
                    "end": date.fromisoformat(row["end"]),
                }
            )
    except (KeyError, TypeError, ValueError):
        return _quarter_terms(year), True
    terms.sort(key=lambda t: t["term"])
    return terms, False


def resolve_term(today, terms, requested=None):
    """Which term the report is about.

    [requested] (1..4) picks that term outright; invalid values fall through
    to the current-term reading. Otherwise: the term containing [today]; in
    a holiday gap the most recently ENDED term (that is when a term report
    matters); before term 1 opens, term 1. None only for empty [terms]."""
    if not terms:
        return None
    try:
        number = int(requested)
    except (TypeError, ValueError):
        number = None
    if number is not None:
        for term in terms:
            if term["term"] == number:
                return term

    current = terms[0]
    for term in terms:
        if term["start"] <= today <= term["end"]:
            return term
        if term["end"] < today:
            current = term
    if today < terms[0]["start"]:
        return terms[0]
    return current


def term_window(term):
    """[start, end) datetimes for querying rows into the term: midnight of
    the start date up to (exclusive) midnight after the end date."""
    start = datetime.combine(term["start"], datetime.min.time())
    end = datetime.combine(term["end"], datetime.min.time()) + timedelta(days=1)
    return start, end


def term_summary(term, year, approximate):
    """The term header dict the API answers (the client's TermWindow)."""
    return {
        "number": term["term"],
        "year": year,
        "label": "Term {0} {1}".format(term["term"], year),
        "start": term["start"].isoformat(),
        "end": term["end"].isoformat(),
        "approximate": bool(approximate),
    }


def _percent(numerator, denominator):
    return int(round(numerator * 100.0 / denominator)) if denominator else None


def attendance_summary(outcomes):
    """The term's attended-vs-skipped split from the partner ledger's synced
    outcomes. Rate is attended over every recorded outcome (both skip kinds
    count as missed — same stance as readiness consistency); None when the
    term holds no events yet."""
    attended = sum(1 for o in outcomes if o == ATTENDED)
    skipped_answered = sum(1 for o in outcomes if o == SKIPPED_ANSWERED)
    skipped_unanswered = sum(1 for o in outcomes if o == SKIPPED_UNANSWERED)
    total = attended + skipped_answered + skipped_unanswered
    return {
        "attended": attended,
        "skipped_answered": skipped_answered,
        "skipped_unanswered": skipped_unanswered,
        "sessions_total": total,
        "attendance_rate_percent": _percent(attended, total),
    }


def quiz_accuracy_by_topic(rows):
    """In-lesson MCQ accuracy grouped by topic.

    [rows]: dicts with `topic` (the lesson's chapter title, resolved by the
    API) and `outcome`. Accuracy counts skips against — an unanswered
    question earns nothing, exactly readiness_rules' mastery stance — with
    the skip count reported alongside so the split stays visible. Topics
    ordered weakest first (the actionable end), then alphabetically."""
    by_topic = {}
    for row in rows:
        outcome = row.get("outcome")
        if outcome not in (CORRECT, INCORRECT, SKIPPED):
            continue
        topic = (row.get("topic") or "").strip() or GENERAL_TOPIC
        bucket = by_topic.setdefault(topic, {CORRECT: 0, INCORRECT: 0, SKIPPED: 0})
        bucket[outcome] += 1

    topics = []
    for topic, bucket in by_topic.items():
        total = bucket[CORRECT] + bucket[INCORRECT] + bucket[SKIPPED]
        topics.append(
            {
                "topic": topic,
                "correct": bucket[CORRECT],
                "incorrect": bucket[INCORRECT],
                "skipped": bucket[SKIPPED],
                "questions": total,
                "accuracy_percent": _percent(bucket[CORRECT], total),
            }
        )
    topics.sort(key=lambda t: (t["accuracy_percent"], t["topic"]))
    return topics


def practice_trend(outcomes):
    """The term's practice mastery trend from the member's chronological
    in-term practice attempts (oldest→newest). None with no attempts — the
    practice layer is optional and an absent section beats a zero. Below
    MIN_TREND_ATTEMPTS the totals stand but no direction is claimed."""
    scored = [o for o in outcomes if o in (CORRECT, INCORRECT, SKIPPED)]
    if not scored:
        return None
    correct = sum(1 for o in scored if o == CORRECT)
    result = {
        "attempts": len(scored),
        "accuracy_percent": _percent(correct, len(scored)),
        "early_percent": None,
        "late_percent": None,
        "direction": None,
    }
    if len(scored) < MIN_TREND_ATTEMPTS:
        return result

    half = len(scored) // 2
    early, late = scored[:half], scored[half:]
    early_percent = _percent(sum(1 for o in early if o == CORRECT), len(early))
    late_percent = _percent(sum(1 for o in late if o == CORRECT), len(late))
    delta = late_percent - early_percent
    result["early_percent"] = early_percent
    result["late_percent"] = late_percent
    result["direction"] = (
        IMPROVING
        if delta >= TREND_DELTA_PERCENT
        else SLIPPING
        if delta <= -TREND_DELTA_PERCENT
        else STEADY
    )
    return result


def readiness_change(start_verdict, now_verdict):
    """Readiness at term start vs now, from readiness_rules' verdict dicts
    (score/band/components — the formula lives THERE; this only compares).
    Either side None means that end had no computable evidence; change is
    claimed only when both ends exist."""
    start_score = start_verdict["score"] if start_verdict else None
    now_score = now_verdict["score"] if now_verdict else None
    return {
        "at_term_start": start_score,
        "now": now_score,
        "band_now": now_verdict["band"] if now_verdict else None,
        "change": (now_score - start_score)
        if start_score is not None and now_score is not None
        else None,
    }


def board_coverage_summary(lessons, completed_lessons, attended_session_ids):
    """Board coverage rolled up to one figure: lessons covered over the
    subject's total. COVERED means finished the lesson OR attended its live
    session — board_coverage.build_term's exact stance, restated here so the
    partner variant needs no session-scoped board endpoint. None when the
    subject has no lessons (no map to summarise)."""
    lessons = list(lessons or [])
    if not lessons:
        return None
    completed = {c for c in (completed_lessons or []) if c}
    attended = {a for a in (attended_session_ids or []) if a}
    covered = sum(
        1
        for lesson in lessons
        if lesson.get("name") in completed
        or (lesson.get("session_id") and lesson.get("session_id") in attended)
    )
    return {
        "lessons_covered": covered,
        "lessons_total": len(lessons),
        "coverage_percent": _percent(covered, len(lessons)),
    }


def build_subject_term_report(
    subject,
    attendance_outcomes,
    quiz_rows,
    practice_outcomes,
    readiness_start,
    readiness_now,
    lessons,
    completed_lessons,
    attended_session_ids,
):
    """One subject's Term Report dict — the JSON contract with the client's
    SubjectTermReport model (term_report_models.dart — keep in sync).

    All row inputs are already term-filtered by the API except [lessons] /
    [completed_lessons] / [attended_session_ids], which are the subject's
    full coverage picture (the Board is a term map of the syllabus, not of
    the term's events). `has_activity` marks whether the TERM itself holds
    any evidence, so the client can show an honest "no term data yet"."""
    attendance = attendance_summary(attendance_outcomes or [])
    topics = quiz_accuracy_by_topic(quiz_rows or [])
    practice = practice_trend(practice_outcomes or [])
    return {
        "subject": subject,
        "attendance": attendance,
        "quiz_topics": topics,
        "practice": practice,
        "readiness": readiness_change(readiness_start, readiness_now),
        "board": board_coverage_summary(
            lessons, completed_lessons, attended_session_ids
        ),
        "has_activity": bool(
            attendance["sessions_total"] or topics or (practice or {}).get("attempts")
        ),
    }
