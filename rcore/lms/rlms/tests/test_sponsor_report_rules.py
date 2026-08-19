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

"""#42 item 3's sponsor/CSI aggregation maths, pinned standalone.

Loaded by file path rather than package import, matching
test_billing_rules.py (workspace modules import through an `rcore`
placeholder; sponsor_report_rules.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest
from datetime import date, datetime

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "sponsor_report_rules.py"
)
_spec = importlib.util.spec_from_file_location(
    "rlms_sponsor_report_rules", _MODULE_PATH
)
rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rules)


class TestFundedCohort(unittest.TestCase):
    def test_distinct_students_sorted(self):
        rows = [
            {"student": "b@x.com"},
            {"student": "a@x.com"},
            {"student": "b@x.com"},  # a renewal is not a second learner
        ]
        self.assertEqual(rules.funded_students(rows), ["a@x.com", "b@x.com"])

    def test_self_checkout_rows_are_not_the_sponsors_cohort(self):
        rows = [{"student": "s@x.com"}, {"student": "a@x.com"}]
        self.assertEqual(
            rules.funded_students(rows, sponsor="s@x.com"), ["a@x.com"]
        )

    def test_empty_billing_means_empty_cohort(self):
        self.assertEqual(rules.funded_students([]), [])
        self.assertEqual(rules.funded_students(None), [])

    def test_blank_student_rows_are_ignored(self):
        self.assertEqual(rules.funded_students([{"student": ""}]), [])


class TestCoverage(unittest.TestCase):
    def test_counts_distinct_students_covered_today(self):
        today = date(2026, 8, 13)
        periods = [
            {"student": "a@x.com", "start_date": date(2026, 8, 1), "end_date": date(2026, 9, 1)},
            # A second overlapping period for the same student is one
            # covered learner, not two.
            {"student": "a@x.com", "start_date": date(2026, 7, 1), "end_date": date(2026, 8, 31)},
            {"student": "b@x.com", "start_date": date(2026, 6, 1), "end_date": date(2026, 7, 1)},
        ]
        self.assertEqual(rules.coverage_count(periods, today), 1)

    def test_boundary_days_count_as_covered(self):
        periods = [
            {"student": "a@x.com", "start_date": date(2026, 8, 13), "end_date": date(2026, 9, 13)}
        ]
        self.assertEqual(rules.coverage_count(periods, date(2026, 8, 13)), 1)

    def test_datetime_today_is_accepted(self):
        periods = [
            {"student": "a@x.com", "start_date": date(2026, 8, 1), "end_date": date(2026, 9, 1)}
        ]
        self.assertEqual(
            rules.coverage_count(periods, datetime(2026, 8, 13, 10, 30)), 1
        )

    def test_empty_periods(self):
        self.assertEqual(rules.coverage_count([], date(2026, 8, 13)), 0)


class TestSpend(unittest.TestCase):
    _rows = [
        {"student": "a@x.com", "amount": 249, "charged_at": datetime(2026, 6, 15)},
        {"student": "b@x.com", "amount": 249, "charged_at": datetime(2026, 8, 2)},
        {"student": "a@x.com", "amount": 498, "charged_at": datetime(2026, 8, 10)},
    ]

    def test_total_spend(self):
        self.assertEqual(rules.spend_total(self._rows), 996.0)
        self.assertEqual(rules.spend_total([]), 0.0)

    def test_spend_within_period_is_inclusive_by_charged_date(self):
        self.assertEqual(
            rules.spend_in_period(self._rows, date(2026, 8, 1), date(2026, 8, 31)),
            747.0,
        )
        self.assertEqual(
            rules.spend_in_period(self._rows, date(2026, 8, 2), date(2026, 8, 2)),
            249.0,
        )

    def test_undated_charges_are_excluded_from_period_spend(self):
        rows = [{"student": "a@x.com", "amount": 249, "charged_at": None}]
        self.assertEqual(
            rules.spend_in_period(rows, date(2026, 1, 1), date(2026, 12, 31)), 0.0
        )

    def test_students_funded_in_period(self):
        self.assertEqual(
            rules.students_funded_in_period(
                self._rows, date(2026, 8, 1), date(2026, 8, 31)
            ),
            2,
        )
        self.assertEqual(
            rules.students_funded_in_period(
                self._rows, date(2026, 1, 1), date(2026, 1, 31)
            ),
            0,
        )


class TestAttendanceRollup(unittest.TestCase):
    def test_rollup_splits_outcomes_and_rates_against_cohort_slots(self):
        events = (
            [{"outcome": "Attended"}] * 6
            + [{"outcome": "Skipped Answered"}] * 2
            + [{"outcome": "Skipped Unanswered"}] * 2
        )
        # 5 scheduled sessions x 2 learners = 10 seats.
        roll = rules.attendance_rollup(events, 5, 2)
        self.assertEqual(roll["sessions_scheduled"], 5)
        self.assertEqual(roll["scheduled_slots"], 10)
        self.assertEqual(roll["attended"], 6)
        self.assertEqual(roll["skipped_answered"], 2)
        self.assertEqual(roll["skipped_unanswered"], 2)
        self.assertEqual(roll["attendance_rate_percent"], 60)

    def test_zero_scheduled_sessions_reads_zero_rate_not_a_crash(self):
        roll = rules.attendance_rollup([{"outcome": "Attended"}], 0, 3)
        self.assertEqual(roll["attendance_rate_percent"], 0)
        self.assertEqual(roll["scheduled_slots"], 0)

    def test_empty_cohort_is_all_zeros(self):
        roll = rules.attendance_rollup([], 5, 0)
        self.assertEqual(roll["attended"], 0)
        self.assertEqual(roll["attendance_rate_percent"], 0)

    def test_rate_is_capped_at_100(self):
        # Duplicate late-synced events must never report >100%.
        roll = rules.attendance_rollup([{"outcome": "Attended"}] * 4, 1, 2)
        self.assertEqual(roll["attendance_rate_percent"], 100)


class TestEngagementRollup(unittest.TestCase):
    def test_answered_vs_skipped_and_correct_rate(self):
        rows = (
            [{"outcome": "Correct"}] * 6
            + [{"outcome": "Incorrect"}] * 2
            + [{"outcome": "Skipped"}] * 2
        )
        roll = rules.engagement_rollup(rows)
        self.assertEqual(roll["questions_answered"], 8)
        self.assertEqual(roll["questions_skipped"], 2)
        self.assertEqual(roll["engagement_rate_percent"], 80)
        self.assertEqual(roll["correct_rate_percent"], 75)

    def test_no_activity_is_zeros(self):
        roll = rules.engagement_rollup([])
        self.assertEqual(roll["engagement_rate_percent"], 0)
        self.assertEqual(roll["correct_rate_percent"], 0)


class TestReadinessBySubject(unittest.TestCase):
    def test_groups_by_subject_and_computes_readiness_percent(self):
        subject_by_lesson = {"l1": "Mathematics", "l2": "Mathematics", "l3": "Physical Sciences"}
        rows = [
            {"lesson": "l1", "outcome": "Correct"},
            {"lesson": "l1", "outcome": "Incorrect"},
            {"lesson": "l2", "outcome": "Correct"},
            {"lesson": "l2", "outcome": "Correct"},
            {"lesson": "l3", "outcome": "Incorrect"},
            {"lesson": "l3", "outcome": "Skipped"},  # skips are engagement, not readiness
        ]
        out = rules.readiness_by_subject(rows, subject_by_lesson)
        self.assertEqual(out["Mathematics"]["readiness_percent"], 75)
        self.assertEqual(out["Mathematics"]["questions_answered"], 4)
        self.assertEqual(out["Physical Sciences"]["readiness_percent"], 0)

    def test_unmapped_lesson_groups_under_its_own_id(self):
        out = rules.readiness_by_subject([{"lesson": "lx", "outcome": "Correct"}], {})
        self.assertEqual(out["lx"]["readiness_percent"], 100)

    def test_empty_rows_is_empty_dict(self):
        self.assertEqual(rules.readiness_by_subject([], {}), {})


class TestImprovementArc(unittest.TestCase):
    _start = datetime(2026, 5, 1)
    _end = datetime(2026, 8, 1)  # midpoint 2026-06-16

    def test_two_sided_arc_returns_deltas(self):
        rows = (
            # Early half: 50% engaged, 50% correct.
            [
                {"outcome": "Correct", "at": datetime(2026, 5, 10)},
                {"outcome": "Incorrect", "at": datetime(2026, 5, 11)},
                {"outcome": "Skipped", "at": datetime(2026, 5, 12)},
                {"outcome": "Skipped", "at": datetime(2026, 5, 13)},
            ]
            # Late half: 100% engaged, 75% correct.
            + [
                {"outcome": "Correct", "at": datetime(2026, 7, 10)},
                {"outcome": "Correct", "at": datetime(2026, 7, 11)},
                {"outcome": "Correct", "at": datetime(2026, 7, 12)},
                {"outcome": "Incorrect", "at": datetime(2026, 7, 13)},
            ]
        )
        arc = rules.improvement_arc(rows, self._start, self._end)
        self.assertEqual(arc["early"]["engagement_rate_percent"], 50)
        self.assertEqual(arc["late"]["engagement_rate_percent"], 100)
        self.assertEqual(arc["engagement_delta_points"], 50)
        self.assertEqual(arc["correct_delta_points"], 25)

    def test_one_sided_arc_has_no_deltas(self):
        rows = [{"outcome": "Correct", "at": datetime(2026, 7, 10)}]
        arc = rules.improvement_arc(rows, self._start, self._end)
        self.assertIsNone(arc["engagement_delta_points"])
        self.assertIsNone(arc["correct_delta_points"])
        self.assertEqual(arc["late"]["questions_answered"], 1)

    def test_empty_period_has_no_deltas(self):
        arc = rules.improvement_arc([], self._start, self._end)
        self.assertIsNone(arc["engagement_delta_points"])
        self.assertIsNone(arc["correct_delta_points"])


class TestMonthlyTrend(unittest.TestCase):
    def test_every_month_in_the_period_appears_in_order(self):
        trend = rules.monthly_attendance_trend(
            [], [], 3, date(2026, 5, 15), date(2026, 8, 13)
        )
        self.assertEqual(
            [t["month"] for t in trend], ["2026-05", "2026-06", "2026-07", "2026-08"]
        )
        self.assertTrue(all(t["attended"] == 0 for t in trend))

    def test_buckets_scheduled_and_attended_by_month(self):
        scheduled = [datetime(2026, 6, 2, 17), datetime(2026, 6, 9, 17), datetime(2026, 7, 7, 17)]
        events = [
            {"outcome": "Attended", "occurred_at": datetime(2026, 6, 2, 17, 5)},
            {"outcome": "Attended", "occurred_at": datetime(2026, 6, 9, 17, 2)},
            {"outcome": "Skipped Unanswered", "occurred_at": datetime(2026, 7, 7, 18)},
        ]
        trend = rules.monthly_attendance_trend(
            events, scheduled, 1, date(2026, 6, 1), date(2026, 7, 31)
        )
        june, july = trend
        self.assertEqual(june["sessions_scheduled"], 2)
        self.assertEqual(june["attended"], 2)
        self.assertEqual(june["attendance_rate_percent"], 100)
        self.assertEqual(july["skipped"], 1)
        self.assertEqual(july["attendance_rate_percent"], 0)

    def test_year_boundary_iterates_correctly(self):
        trend = rules.monthly_attendance_trend(
            [], [], 1, date(2026, 11, 20), date(2027, 2, 3)
        )
        self.assertEqual(
            [t["month"] for t in trend],
            ["2026-11", "2026-12", "2027-01", "2027-02"],
        )


class TestDataUsage(unittest.TestCase):
    def test_sums_synced_megabytes(self):
        events = [
            {"data_used_mb": 12.5},
            {"data_used_mb": None},  # an unsynced estimate is 0, not a crash
            {"data_used_mb": 7.5},
        ]
        self.assertEqual(rules.total_data_used_mb(events), 20.0)
        self.assertEqual(rules.total_data_used_mb([]), 0.0)


if __name__ == "__main__":
    unittest.main()
