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

"""Pure streak rules (decision #42 gap 4 — visible streaks).

Deliberately frappe-free: `api/engagement.py` does the querying, this
module does the DECIDING, same split as alert_rules.py. The definition is
the one the partner weekly report already uses — consecutive attended
live sessions, newest first — extracted here so the student-facing
surface and the partner report agree on what a streak IS.

No energy-gating and no streak freezes (decision #42: punitive mechanics
are wrong for a paid/sponsor product). A streak is purely a positive
counter; breaking it costs nothing beyond the counter resetting.
"""

ATTENDED = "Attended"


def current_streak(outcomes):
    """Consecutive [ATTENDED] outcomes counting back from the most recent
    event. [outcomes] is the student's attendance-event outcome history,
    NEWEST FIRST (`LMS Attendance Event.outcome` labels)."""
    streak = 0
    for outcome in outcomes:
        if outcome != ATTENDED:
            break
        streak += 1
    return streak


def best_streak(outcomes):
    """The longest run of consecutive [ATTENDED] outcomes anywhere in the
    history. Order (newest/oldest first) does not change the answer."""
    best = run = 0
    for outcome in outcomes:
        if outcome == ATTENDED:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best


def compute_streaks(outcomes):
    """Both numbers in one pass shape: `{"current": int, "best": int}`.
    [outcomes] NEWEST FIRST."""
    return {"current": current_streak(outcomes), "best": best_streak(outcomes)}
