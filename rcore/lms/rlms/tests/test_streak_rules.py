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

"""Decision #42 gap 4 — the student-facing streak: consecutive attended
live sessions, newest first, plus the best-ever run.

Loaded by file path on purpose (same reason as test_alert_rules.py):
streak_rules.py is deliberately frappe-free, so this runs anywhere
python does — no bench, no site, no substitution.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "streak_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_streak_rules", _MODULE_PATH)
streak_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(streak_rules)

ATTENDED = streak_rules.ATTENDED
SKIP = "Skipped Unanswered"
SKIP_ANSWERED = "Skipped Answered"


class TestCurrentStreak(unittest.TestCase):
    """Outcome lists are NEWEST FIRST."""

    def test_empty_history_is_zero(self):
        self.assertEqual(streak_rules.current_streak([]), 0)

    def test_counts_consecutive_attended_from_newest(self):
        self.assertEqual(
            streak_rules.current_streak([ATTENDED, ATTENDED, ATTENDED, SKIP]), 3
        )

    def test_most_recent_skip_means_zero(self):
        self.assertEqual(
            streak_rules.current_streak([SKIP, ATTENDED, ATTENDED]), 0
        )

    def test_answered_skip_still_breaks_the_streak(self):
        # Answering the skip gate is better behaviour, but the session was
        # still missed — same rule the alert threshold applies.
        self.assertEqual(
            streak_rules.current_streak([ATTENDED, SKIP_ANSWERED, ATTENDED]), 1
        )

    def test_unbroken_history_counts_everything(self):
        self.assertEqual(streak_rules.current_streak([ATTENDED] * 12), 12)


class TestBestStreak(unittest.TestCase):
    def test_empty_history_is_zero(self):
        self.assertEqual(streak_rules.best_streak([]), 0)

    def test_finds_longest_run_anywhere(self):
        history = [ATTENDED, SKIP, ATTENDED, ATTENDED, ATTENDED, SKIP, ATTENDED]
        self.assertEqual(streak_rules.best_streak(history), 3)

    def test_current_run_can_be_the_best(self):
        history = [ATTENDED, ATTENDED, SKIP, ATTENDED]
        self.assertEqual(streak_rules.best_streak(history), 2)

    def test_all_skips_is_zero(self):
        self.assertEqual(streak_rules.best_streak([SKIP, SKIP_ANSWERED]), 0)


class TestComputeStreaks(unittest.TestCase):
    def test_returns_both_numbers(self):
        history = [SKIP, ATTENDED, ATTENDED, SKIP, ATTENDED]
        self.assertEqual(
            streak_rules.compute_streaks(history), {"current": 0, "best": 2}
        )

    def test_current_never_exceeds_best(self):
        history = [ATTENDED, ATTENDED, ATTENDED]
        result = streak_rules.compute_streaks(history)
        self.assertLessEqual(result["current"], result["best"])
        self.assertEqual(result, {"current": 3, "best": 3})


if __name__ == "__main__":
    unittest.main()
