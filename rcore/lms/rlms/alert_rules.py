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

"""Pure alert-threshold rules for the accountability partner (P3.2).

Deliberately frappe-free: `partner.py` does the querying and the sending,
this module does the DECIDING. Keeping the threshold logic free of frappe
imports is what makes it unit-testable without a bench/site — the rest of
the rlms backend can only be exercised inside a composed app.

The rule (business doc §1 "instant alerts", refined by the P3.2 brief): a
single skip is normal life and never alerts. The signal worth surfacing is
a BROKEN PATTERN — the second consecutive skip. If skips keep accumulating
in the trailing window, the alert escalates to carry a remediation
suggestion.
"""

ATTENDED = "Attended"

#: Skips within the trailing window at/above which the alert escalates to
#: carry the remediation suggestion.
ESCALATE_AT_SKIPS = 3

#: No alert.
NONE = None

#: Second consecutive skip — the attendance streak just broke.
STREAK_BREAK = "streak_break"

#: Skips keep accumulating — add the remediation suggestion.
REPEATED = "repeated"


def evaluate_skip_alert(recent_outcomes):
    """Decide whether a just-recorded skip should alert the partner.

    [recent_outcomes] is the student's trailing outcome window, NEWEST
    FIRST, where index 0 is the skip that was just recorded. Values are the
    `LMS Attendance Event.outcome` labels ("Attended" / "Skipped Answered" /
    "Skipped Unanswered").

    Returns [NONE], [STREAK_BREAK], or [REPEATED].
    """
    if not recent_outcomes:
        return NONE
    # Nothing to compare against, or the previous session was attended:
    # this is a first skip after attendance — normal life, stay quiet.
    if len(recent_outcomes) < 2 or recent_outcomes[1] == ATTENDED:
        return NONE
    skips_in_window = sum(1 for o in recent_outcomes if o != ATTENDED)
    if skips_in_window >= ESCALATE_AT_SKIPS:
        return REPEATED
    return STREAK_BREAK
