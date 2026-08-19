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

"""Pure scoring rules for the per-subject Supacharge Readiness Score
(decision #42 gap 5: a verifiable, shareable credential generated from the
analytics the backend already tracks).

Deliberately frappe-free: `api/readiness.py` does the querying and the
serving, this module does the SCORING. Keeping the formula free of frappe
imports is what makes it unit-testable without a bench/site — the same split
alert_rules.py and time_gates.py already use.

THE FORMULA (0-100, per subject)
--------------------------------
Three weighted components, each 0..1, from data doctypes that already exist.
They mirror the dimensions of the internal end-of-Holiday-Programme "Grade
Readiness Report" (business doc §2: per-topic quiz mastery rolled up to an
overall readiness percentage), extended with the coverage and consistency
signals the report's parent framing already surfaces:

- MASTERY (weight 0.5)   — LMS Lesson Quiz Result: correct answers over ALL
  recorded question outcomes (correct + incorrect + skipped). A skipped
  question earns nothing, exactly as it would in the exam the score claims
  readiness for.
- COVERAGE (weight 0.3)  — LMS Enrollment / LMS Course Progress: the mean
  enrollment progress percentage across the subject's enrolled courses,
  scaled to 0..1. How much of the syllabus has actually been worked through.
- CONSISTENCY (weight 0.2) — LMS Attendance Event: sessions attended over
  all recorded session outcomes (attended + both skip kinds). The
  show-up-every-evening habit the broadcast model is built on.

    score = round(100 * (0.5*mastery + 0.3*coverage + 0.2*consistency))

A component with NO underlying data (no quiz outcomes yet, no attendance
events yet) is treated as ABSENT, not as zero: the remaining weights are
renormalised so a brand-new signal never drags an otherwise-earned score to
the floor. With no components at all there is no score (None) — a credential
must never be minted from zero evidence.

Rounding is half-up (deterministic, and 84.5 reads as 85 to a parent), and
the result is clamped to 0..100.

BANDS (for the card/verify page label; thresholds are product defaults):
    80-100 Exam Ready · 60-79 On Track · 40-59 Building · 0-39 Needs Focus
"""

import math

#: Component weights — must sum to 1. Mastery dominates: the score's claim
#: is exam readiness, and answered-correctly is the closest proxy held.
WEIGHT_MASTERY = 0.5
WEIGHT_COVERAGE = 0.3
WEIGHT_CONSISTENCY = 0.2

#: Band thresholds, highest first: (minimum score, label).
BANDS = (
    (80, "Exam Ready"),
    (60, "On Track"),
    (40, "Building"),
    (0, "Needs Focus"),
)


def mastery_component(correct, incorrect, skipped):
    """Quiz mastery 0..1: correct over every recorded outcome. Skips count
    against mastery (an unanswered exam question earns nothing). None when
    no outcomes exist yet — absent, not zero."""
    total = correct + incorrect + skipped
    if total <= 0:
        return None
    return correct / total


def coverage_component(progress_percents):
    """Syllabus coverage 0..1: the mean of the subject's enrollment progress
    percentages (each 0..100), clamped per course. None when the student has
    no enrollments in the subject."""
    percents = list(progress_percents or [])
    if not percents:
        return None
    clamped = [min(max(float(p or 0), 0.0), 100.0) for p in percents]
    return sum(clamped) / (100.0 * len(clamped))


def consistency_component(attended, skipped_answered, skipped_unanswered):
    """Attendance consistency 0..1: attended over every recorded session
    outcome. Both skip kinds count as missed sessions (answering the skip
    gate is better behaviour, but the session was still missed — same stance
    as alert_rules). None when no events exist yet."""
    total = attended + skipped_answered + skipped_unanswered
    if total <= 0:
        return None
    return attended / total


def readiness_band(score):
    """The display label for a 0..100 score (card + verify page)."""
    for minimum, label in BANDS:
        if score >= minimum:
            return label
    return BANDS[-1][1]


def readiness_score(mastery, coverage, consistency):
    """Combine the components into the 0-100 Readiness Score.

    Each argument is the component value 0..1, or None when that signal has
    no underlying data yet. Absent components drop out and the remaining
    weights renormalise; all-absent returns None (no credential without
    evidence).

    Returns {"score": int 0..100, "band": str, "components": {...}} where
    components maps each PRESENT component name to its rounded percentage.
    """
    weighted = [
        ("mastery", mastery, WEIGHT_MASTERY),
        ("coverage", coverage, WEIGHT_COVERAGE),
        ("consistency", consistency, WEIGHT_CONSISTENCY),
    ]
    present = [(name, value, weight) for name, value, weight in weighted if value is not None]
    if not present:
        return None

    total_weight = sum(weight for _, _, weight in present)
    raw = sum(value * weight for _, value, weight in present) / total_weight
    score = int(min(max(math.floor(raw * 100 + 0.5), 0), 100))
    return {
        "score": score,
        "band": readiness_band(score),
        "components": {
            name: int(min(max(math.floor(value * 100 + 0.5), 0), 100))
            for name, value, _ in present
        },
    }
