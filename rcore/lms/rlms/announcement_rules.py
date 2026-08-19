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

"""Pure audience/window rules for operator announcements (one-way
operator→student posts riding the Glance surface — schedule changes,
holiday programme news; no comments, no stream).

Deliberately frappe-free: `api/announcements.py` does the storage I/O,
this module does the DECIDING — which posts a given student sees right
now, and what counts as a valid audience/window on create. Keeping the
logic out of the API file is what makes it unit-testable without a
bench/site (same split as bite_rules.py / practice_rules.py).

Visibility contract (the student read):
- retired posts are never shown;
- the window gates: `starts_at` in the future hides the post, `ends_at`
  in the past hides it; either side missing means unbounded on that side;
- audience filters narrow, never widen: a post with a grade shows only to
  students with THAT stored grade; a post with a curriculum shows only to
  students with THAT stored curriculum. A student with no stored value
  does not see targeted posts — targeting means "for that audience", and
  an unknown student is not known to be in it. Untargeted posts show to
  everyone.
"""

from datetime import datetime

# Kept in sync with lms_student_profile.py's validate() — same deliberate
# duplication as api/student.py (rules stay import-free of frappe code).
MIN_GRADE = 1
MAX_GRADE = 12

# Display-stable curriculum strings (school-capture brief) — kept in sync
# with api/student.py's CURRICULA and lms_sdk's kSelectableCurricula.
CURRICULA = ("CAPS", "IEB", "Cambridge", "US Common Core")


def as_datetime(value):
    """`value` as a naive datetime, or None. Accepts datetime objects and
    ISO/frappe `YYYY-MM-DD HH:MM:SS` strings; anything unparseable reads as
    "not set" rather than erroring a student surface."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def in_window(starts_at, ends_at, now):
    """Whether `now` falls inside the active window. A missing side is
    unbounded; `ends_at` is exclusive (a post ending 09:00 is gone at
    09:00 sharp)."""
    start = as_datetime(starts_at)
    end = as_datetime(ends_at)
    if start is not None and now < start:
        return False
    if end is not None and now >= end:
        return False
    return True


def matches_audience(post_grade, post_curriculum, grade, curriculum):
    """Whether a student with `grade`/`curriculum` is in the post's
    audience. Empty filters match everyone; a set filter requires the
    student's matching stored value (unknown student value → no match)."""
    if post_grade not in (None, ""):
        try:
            if grade is None or int(post_grade) != int(grade):
                return False
        except (TypeError, ValueError):
            return False
    if post_curriculum not in (None, ""):
        if not curriculum or str(post_curriculum) != str(curriculum):
            return False
    return True


def visible(rows, grade, curriculum, now):
    """The subset of `rows` (dicts with grade/curriculum/starts_at/ends_at
    keys; already excluding retired posts) this student sees right now,
    newest-posted first. Row order is preserved from the caller's
    newest-first query — this only filters."""
    return [
        row
        for row in rows
        if in_window(row.get("starts_at"), row.get("ends_at"), now)
        and matches_audience(row.get("grade"), row.get("curriculum"), grade, curriculum)
    ]


def validate_post(title, body, grade=None, curriculum=None, starts_at=None, ends_at=None):
    """The create gate: the first problem as a message string, or None when
    the post is well-formed. The API layer throws the message verbatim."""
    if not (title or "").strip():
        return "title is required."
    if not (body or "").strip():
        return "body is required."
    if grade not in (None, ""):
        try:
            grade = int(grade)
        except (TypeError, ValueError):
            return "grade must be a number."
        if not (MIN_GRADE <= grade <= MAX_GRADE):
            return f"grade must be between {MIN_GRADE} and {MAX_GRADE}."
    if curriculum not in (None, "") and curriculum not in CURRICULA:
        return "curriculum must be one of: " + ", ".join(CURRICULA)
    start = as_datetime(starts_at)
    end = as_datetime(ends_at)
    if starts_at not in (None, "") and start is None:
        return "starts_at is not a valid date/time."
    if ends_at not in (None, "") and end is None:
        return "ends_at is not a valid date/time."
    if start is not None and end is not None and end <= start:
        return "ends_at must be after starts_at."
    return None
