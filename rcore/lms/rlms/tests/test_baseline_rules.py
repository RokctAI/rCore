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

"""Decision #31's last-year comparison maths, pinned standalone (no frappe,
no site — `python -m unittest tests.test_baseline_rules`).

Loaded by file path rather than package import, matching
test_alert_rules.py: workspace python modules import through an `rcore`
placeholder and only resolve inside a composed app; baseline_rules.py is
deliberately frappe-free so this test runs anywhere python does."""

import importlib.util
import os
import unittest
from datetime import datetime

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "baseline_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_baseline_rules", _MODULE_PATH)
baseline_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(baseline_rules)


def _event(when, outcome=baseline_rules.ATTENDED):
    return (when, outcome)


class TestYearAnchor(unittest.TestCase):
    def test_same_date_one_year_back(self):
        self.assertEqual(
            baseline_rules.year_anchor(datetime(2026, 8, 13, 15, 30), 2025),
            datetime(2025, 8, 13, 15, 30),
        )

    def test_feb_29_maps_to_feb_28_in_non_leap_year(self):
        self.assertEqual(
            baseline_rules.year_anchor(datetime(2028, 2, 29, 9, 0), 2027),
            datetime(2027, 2, 28, 9, 0),
        )


class TestWindowBounds(unittest.TestCase):
    # Thursday 2025-08-14 — the windows must mirror the client's
    # ProfileNotifier._summaryFor, shifted a year back: same calendar day,
    # Monday-start week, calendar month, each ending the day after anchor.
    anchor = datetime(2025, 8, 14, 15, 30)

    def test_day_is_the_anchor_calendar_day(self):
        self.assertEqual(
            baseline_rules.window_bounds(self.anchor, "day"),
            (datetime(2025, 8, 14), datetime(2025, 8, 15)),
        )

    def test_week_starts_monday(self):
        self.assertEqual(
            baseline_rules.window_bounds(self.anchor, "week"),
            (datetime(2025, 8, 11), datetime(2025, 8, 15)),
        )

    def test_month_starts_on_the_first(self):
        self.assertEqual(
            baseline_rules.window_bounds(self.anchor, "month"),
            (datetime(2025, 8, 1), datetime(2025, 8, 15)),
        )

    def test_unknown_window_refused(self):
        with self.assertRaises(ValueError):
            baseline_rules.window_bounds(self.anchor, "term")


class TestAttendanceRate(unittest.TestCase):
    start = datetime(2025, 8, 1)
    end = datetime(2025, 9, 1)

    def test_rate_is_attended_over_all_events(self):
        # Same definition as the client's AttendanceSummary: skips (either
        # variant) count in the denominator, only Attended in the numerator.
        events = [
            _event(datetime(2025, 8, 5, 15, 0)),
            _event(datetime(2025, 8, 6, 15, 0), "Skipped Answered"),
            _event(datetime(2025, 8, 7, 15, 0), "Skipped Unanswered"),
            _event(datetime(2025, 8, 8, 15, 0)),
        ]
        self.assertEqual(
            baseline_rules.attendance_rate(events, self.start, self.end), 50
        )

    def test_empty_window_is_none_not_zero(self):
        # None lets LastYearBaseline.rateFor fall back to the overall rate —
        # a windowless 0% would read as "attended nothing", which is false.
        events = [_event(datetime(2025, 7, 31, 23, 59))]
        self.assertIsNone(
            baseline_rules.attendance_rate(events, self.start, self.end)
        )

    def test_bounds_are_start_inclusive_end_exclusive(self):
        events = [
            _event(self.start),
            _event(self.end, "Skipped Unanswered"),
        ]
        self.assertEqual(
            baseline_rules.attendance_rate(events, self.start, self.end), 100
        )


class TestYearBaseline(unittest.TestCase):
    now = datetime(2026, 8, 14, 15, 30)

    def test_no_ledger_no_baseline(self):
        # A student with no events last year gets None, never a zeroed dict
        # — the client keeps its own fallback (demo numbers / no card row).
        self.assertIsNone(baseline_rules.year_baseline([], 7, 2025, self.now))

    def test_out_of_year_events_do_not_count(self):
        events = [
            _event(datetime(2024, 12, 31, 23, 0)),
            _event(datetime(2026, 1, 1, 0, 0)),
        ]
        self.assertIsNone(
            baseline_rules.year_baseline(events, 0, 2025, self.now)
        )

    def test_wire_shape_matches_last_year_baseline_from_json(self):
        events = [
            # In the like-for-like day window (2025-08-14): one skip.
            _event(datetime(2025, 8, 14, 15, 0), "Skipped Unanswered"),
            # Rest of the anchor week (Mon 2025-08-11 onward): one attended.
            _event(datetime(2025, 8, 12, 15, 0)),
            # Earlier in the anchor month: one attended.
            _event(datetime(2025, 8, 4, 15, 0)),
            # Elsewhere in the year: one attended.
            _event(datetime(2025, 3, 3, 15, 0)),
        ]
        baseline = baseline_rules.year_baseline(events, 38, 2025, self.now)
        self.assertEqual(
            baseline,
            {
                "year": 2025,
                "attendance_rate_percent": 75,  # 3 of 4
                "rates_by_window": {
                    "day": 0,  # the one same-date event was a skip
                    "week": 50,  # 1 of 2 in the Mon-anchored week
                    "month": 67,  # 2 of 3 in August
                },
                "sessions_attended": 3,
                "sessions_scheduled": 4,
                "quizzes_skipped": 38,
            },
        )

    def test_empty_windows_are_omitted_for_rate_for_fallback(self):
        # One event in March only: day/week/month around the August anchor
        # hold nothing, so rates_by_window must omit them (the client falls
        # back to the overall rate), not report 0%.
        events = [_event(datetime(2025, 3, 3, 15, 0))]
        baseline = baseline_rules.year_baseline(events, 0, 2025, self.now)
        self.assertEqual(baseline["rates_by_window"], {})
        self.assertEqual(baseline["attendance_rate_percent"], 100)

    def test_quizzes_skipped_none_collapses_to_zero(self):
        events = [_event(datetime(2025, 3, 3, 15, 0))]
        baseline = baseline_rules.year_baseline(events, None, 2025, self.now)
        self.assertEqual(baseline["quizzes_skipped"], 0)


if __name__ == "__main__":
    unittest.main()
