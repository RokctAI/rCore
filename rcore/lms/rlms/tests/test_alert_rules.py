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

"""P3.2 partner alert threshold — the rule the brief is most specific about:
alert on the SECOND CONSECUTIVE skip, never on every skip.

Loaded by file path rather than package import on purpose: every other
python test in this workspace imports through an `rcore` placeholder
and therefore only runs inside a composed app. alert_rules.py is
deliberately frappe-free, so this test runs anywhere python does —
`python -m unittest` from the repo, no bench, no site, no substitution.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "alert_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_alert_rules", _MODULE_PATH)
alert_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(alert_rules)

ATTENDED = alert_rules.ATTENDED
SKIP = "Skipped Unanswered"
SKIP_ANSWERED = "Skipped Answered"


class TestSkipAlertThreshold(unittest.TestCase):
    """Window lists are NEWEST FIRST; index 0 is the skip just recorded."""

    def test_first_skip_after_attendance_is_silent(self):
        # The explicit product rule: one skip is normal life, no alert.
        self.assertIs(
            alert_rules.evaluate_skip_alert([SKIP, ATTENDED, ATTENDED, ATTENDED]),
            alert_rules.NONE,
        )

    def test_second_consecutive_skip_breaks_the_streak(self):
        self.assertEqual(
            alert_rules.evaluate_skip_alert([SKIP, SKIP, ATTENDED, ATTENDED]),
            alert_rules.STREAK_BREAK,
        )

    def test_answered_skip_still_counts_as_a_skip(self):
        # Answering the skip gate is better behaviour, but it is still a
        # missed session — the streak breaks either way.
        self.assertEqual(
            alert_rules.evaluate_skip_alert(
                [SKIP, SKIP_ANSWERED, ATTENDED, ATTENDED]
            ),
            alert_rules.STREAK_BREAK,
        )

    def test_three_skips_in_the_window_escalates(self):
        self.assertEqual(
            alert_rules.evaluate_skip_alert([SKIP, SKIP, ATTENDED, SKIP]),
            alert_rules.REPEATED,
        )

    def test_all_skips_escalates(self):
        self.assertEqual(
            alert_rules.evaluate_skip_alert([SKIP, SKIP, SKIP, SKIP]),
            alert_rules.REPEATED,
        )

    def test_very_first_event_ever_is_silent(self):
        # A brand-new student whose first recorded event is a skip has no
        # pattern to break yet.
        self.assertIs(alert_rules.evaluate_skip_alert([SKIP]), alert_rules.NONE)

    def test_empty_window_is_silent(self):
        self.assertIs(alert_rules.evaluate_skip_alert([]), alert_rules.NONE)

    def test_attendance_resets_the_pattern(self):
        # Skip, then attended, then skip again: the most recent skip follows
        # an attended session, so it is a first skip again — silent.
        self.assertIs(
            alert_rules.evaluate_skip_alert([SKIP, ATTENDED, SKIP, ATTENDED]),
            alert_rules.NONE,
        )


if __name__ == "__main__":
    unittest.main()
