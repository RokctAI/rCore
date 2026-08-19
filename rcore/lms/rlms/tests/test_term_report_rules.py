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

"""Term Report assembly (the weekly report's big sibling), pinned standalone
(no frappe, no site — `python -m unittest tests.test_term_report_rules`).

Loaded by file path rather than package import, matching
test_board_coverage.py: workspace python modules import through an
`rcore` placeholder and only resolve inside a composed app;
term_report_rules.py is deliberately frappe-free and self-contained so this
test runs anywhere python does."""

import importlib.util
import os
import unittest
from datetime import date, datetime

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "term_report_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_term_report_rules", _MODULE_PATH)
term_report_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(term_report_rules)


TERMS_2026, APPROX_2026 = term_report_rules.terms_for_year(2026)


class TestTermsForYear(unittest.TestCase):
    def test_2026_carries_the_gazetted_dbe_dates(self):
        self.assertFalse(APPROX_2026)
        self.assertEqual([t["term"] for t in TERMS_2026], [1, 2, 3, 4])
        self.assertEqual(TERMS_2026[0]["start"], date(2026, 1, 14))
        self.assertEqual(TERMS_2026[0]["end"], date(2026, 3, 27))
        self.assertEqual(TERMS_2026[2]["start"], date(2026, 7, 21))
        self.assertEqual(TERMS_2026[3]["end"], date(2026, 12, 9))

    def test_unknown_year_degrades_to_flagged_quarters(self):
        terms, approximate = term_report_rules.terms_for_year(2031)
        self.assertTrue(approximate)
        self.assertEqual([t["term"] for t in terms], [1, 2, 3, 4])
        self.assertEqual(terms[0]["start"], date(2031, 1, 1))
        self.assertEqual(terms[3]["end"], date(2031, 12, 31))


class TestResolveTerm(unittest.TestCase):
    def test_inside_a_term_answers_that_term(self):
        term = term_report_rules.resolve_term(date(2026, 8, 14), TERMS_2026)
        self.assertEqual(term["term"], 3)

    def test_term_boundary_days_count_as_in_term(self):
        self.assertEqual(
            term_report_rules.resolve_term(date(2026, 7, 21), TERMS_2026)["term"], 3
        )
        self.assertEqual(
            term_report_rules.resolve_term(date(2026, 9, 23), TERMS_2026)["term"], 3
        )

    def test_holiday_gap_answers_the_term_that_just_ended(self):
        # The winter holiday (27 Jun - 20 Jul) reports on term 2 — a term
        # report matters most right after the term closes.
        term = term_report_rules.resolve_term(date(2026, 7, 1), TERMS_2026)
        self.assertEqual(term["term"], 2)

    def test_before_the_year_opens_answers_term_one(self):
        term = term_report_rules.resolve_term(date(2026, 1, 2), TERMS_2026)
        self.assertEqual(term["term"], 1)

    def test_after_the_year_closes_answers_term_four(self):
        term = term_report_rules.resolve_term(date(2026, 12, 20), TERMS_2026)
        self.assertEqual(term["term"], 4)

    def test_requested_term_wins_over_the_calendar(self):
        term = term_report_rules.resolve_term(
            date(2026, 8, 14), TERMS_2026, requested=1
        )
        self.assertEqual(term["term"], 1)
        # String numbers arrive over the wire.
        term = term_report_rules.resolve_term(
            date(2026, 8, 14), TERMS_2026, requested="2"
        )
        self.assertEqual(term["term"], 2)

    def test_invalid_request_falls_back_to_current(self):
        for requested in ("nine", 9, None):
            term = term_report_rules.resolve_term(
                date(2026, 8, 14), TERMS_2026, requested=requested
            )
            self.assertEqual(term["term"], 3)

    def test_empty_terms_answers_none(self):
        self.assertIsNone(term_report_rules.resolve_term(date(2026, 8, 14), []))


class TestTermWindow(unittest.TestCase):
    def test_window_spans_midnight_to_exclusive_day_after_end(self):
        start, end = term_report_rules.term_window(TERMS_2026[2])
        self.assertEqual(start, datetime(2026, 7, 21, 0, 0))
        self.assertEqual(end, datetime(2026, 9, 24, 0, 0))

    def test_summary_is_the_client_contract(self):
        summary = term_report_rules.term_summary(TERMS_2026[2], 2026, False)
        self.assertEqual(
            summary,
            {
                "number": 3,
                "year": 2026,
                "label": "Term 3 2026",
                "start": "2026-07-21",
                "end": "2026-09-23",
                "approximate": False,
            },
        )


class TestAttendanceSummary(unittest.TestCase):
    def test_split_and_rate(self):
        summary = term_report_rules.attendance_summary(
            ["Attended", "Attended", "Skipped Answered", "Skipped Unanswered"]
        )
        self.assertEqual(summary["attended"], 2)
        self.assertEqual(summary["skipped_answered"], 1)
        self.assertEqual(summary["skipped_unanswered"], 1)
        self.assertEqual(summary["sessions_total"], 4)
        self.assertEqual(summary["attendance_rate_percent"], 50)

    def test_no_events_has_no_rate_not_a_zero(self):
        summary = term_report_rules.attendance_summary([])
        self.assertEqual(summary["sessions_total"], 0)
        self.assertIsNone(summary["attendance_rate_percent"])

    def test_unknown_outcomes_are_ignored(self):
        summary = term_report_rules.attendance_summary(["Attended", "Weird"])
        self.assertEqual(summary["sessions_total"], 1)
        self.assertEqual(summary["attendance_rate_percent"], 100)


class TestQuizAccuracyByTopic(unittest.TestCase):
    def test_groups_by_topic_and_counts_skips_against_accuracy(self):
        topics = term_report_rules.quiz_accuracy_by_topic(
            [
                {"topic": "Algebra", "outcome": "Correct"},
                {"topic": "Algebra", "outcome": "Skipped"},
                {"topic": "Geometry", "outcome": "Correct"},
                {"topic": "Geometry", "outcome": "Correct"},
            ]
        )
        by_name = {t["topic"]: t for t in topics}
        # Same stance as readiness mastery: a skip earns nothing.
        self.assertEqual(by_name["Algebra"]["accuracy_percent"], 50)
        self.assertEqual(by_name["Algebra"]["skipped"], 1)
        self.assertEqual(by_name["Geometry"]["accuracy_percent"], 100)
        self.assertEqual(by_name["Geometry"]["questions"], 2)

    def test_weakest_topic_lists_first(self):
        topics = term_report_rules.quiz_accuracy_by_topic(
            [
                {"topic": "Strong", "outcome": "Correct"},
                {"topic": "Weak", "outcome": "Incorrect"},
            ]
        )
        self.assertEqual([t["topic"] for t in topics], ["Weak", "Strong"])

    def test_missing_topic_buckets_as_general(self):
        topics = term_report_rules.quiz_accuracy_by_topic(
            [{"topic": None, "outcome": "Correct"}, {"topic": "  ", "outcome": "Correct"}]
        )
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["topic"], term_report_rules.GENERAL_TOPIC)
        self.assertEqual(topics[0]["questions"], 2)

    def test_no_rows_means_no_topics(self):
        self.assertEqual(term_report_rules.quiz_accuracy_by_topic([]), [])


class TestPracticeTrend(unittest.TestCase):
    def test_no_attempts_means_no_section(self):
        self.assertIsNone(term_report_rules.practice_trend([]))

    def test_too_few_attempts_claims_no_direction(self):
        trend = term_report_rules.practice_trend(["Correct", "Incorrect", "Correct"])
        self.assertEqual(trend["attempts"], 3)
        self.assertEqual(trend["accuracy_percent"], 67)
        self.assertIsNone(trend["direction"])
        self.assertIsNone(trend["early_percent"])

    def test_improving_when_the_late_half_scores_higher(self):
        trend = term_report_rules.practice_trend(
            ["Incorrect", "Incorrect", "Correct", "Correct"]
        )
        self.assertEqual(trend["early_percent"], 0)
        self.assertEqual(trend["late_percent"], 100)
        self.assertEqual(trend["direction"], term_report_rules.IMPROVING)

    def test_slipping_when_the_late_half_scores_lower(self):
        trend = term_report_rules.practice_trend(
            ["Correct", "Correct", "Incorrect", "Skipped"]
        )
        self.assertEqual(trend["direction"], term_report_rules.SLIPPING)

    def test_steady_inside_the_noise_band(self):
        trend = term_report_rules.practice_trend(
            ["Correct", "Incorrect", "Correct", "Incorrect"]
        )
        self.assertEqual(trend["direction"], term_report_rules.STEADY)

    def test_unknown_outcomes_are_ignored(self):
        trend = term_report_rules.practice_trend(["Correct", "Weird"])
        self.assertEqual(trend["attempts"], 1)
        self.assertEqual(trend["accuracy_percent"], 100)


class TestReadinessChange(unittest.TestCase):
    START = {"score": 40, "band": "Building", "components": {}}
    NOW = {"score": 62, "band": "On Track", "components": {}}

    def test_change_needs_both_ends(self):
        change = term_report_rules.readiness_change(self.START, self.NOW)
        self.assertEqual(change["at_term_start"], 40)
        self.assertEqual(change["now"], 62)
        self.assertEqual(change["band_now"], "On Track")
        self.assertEqual(change["change"], 22)

    def test_absent_start_claims_no_change(self):
        change = term_report_rules.readiness_change(None, self.NOW)
        self.assertIsNone(change["at_term_start"])
        self.assertIsNone(change["change"])
        self.assertEqual(change["now"], 62)

    def test_absent_now_claims_no_change(self):
        change = term_report_rules.readiness_change(self.START, None)
        self.assertIsNone(change["now"])
        self.assertIsNone(change["band_now"])
        self.assertIsNone(change["change"])


class TestBoardCoverageSummary(unittest.TestCase):
    LESSONS = [
        {"name": "l-1", "session_id": "s-1"},
        {"name": "l-2", "session_id": "s-2"},
        {"name": "l-3", "session_id": None},
        {"name": "l-4", "session_id": "s-4"},
    ]

    def test_completed_or_attended_both_count_as_covered(self):
        summary = term_report_rules.board_coverage_summary(
            self.LESSONS, {"l-3"}, {"s-1"}
        )
        self.assertEqual(summary["lessons_covered"], 2)
        self.assertEqual(summary["lessons_total"], 4)
        self.assertEqual(summary["coverage_percent"], 50)

    def test_no_lessons_means_no_map(self):
        self.assertIsNone(term_report_rules.board_coverage_summary([], set(), set()))
        self.assertIsNone(
            term_report_rules.board_coverage_summary(None, None, None)
        )

    def test_covered_lesson_is_not_double_counted(self):
        summary = term_report_rules.board_coverage_summary(
            self.LESSONS, {"l-1"}, {"s-1"}
        )
        self.assertEqual(summary["lessons_covered"], 1)


class TestBuildSubjectTermReport(unittest.TestCase):
    def build(self, **overrides):
        kwargs = dict(
            subject="Mathematics",
            attendance_outcomes=["Attended", "Skipped Unanswered"],
            quiz_rows=[{"topic": "Algebra", "outcome": "Correct"}],
            practice_outcomes=["Correct", "Incorrect", "Correct", "Correct"],
            readiness_start={"score": 40, "band": "Building", "components": {}},
            readiness_now={"score": 62, "band": "On Track", "components": {}},
            lessons=[{"name": "l-1", "session_id": "s-1"}],
            completed_lessons={"l-1"},
            attended_session_ids=set(),
        )
        kwargs.update(overrides)
        return term_report_rules.build_subject_term_report(**kwargs)

    def test_contract_shape(self):
        # The dict IS the JSON contract with the client's SubjectTermReport
        # model — key names must match term_report_models.dart exactly.
        report = self.build()
        self.assertEqual(
            set(report.keys()),
            {
                "subject",
                "attendance",
                "quiz_topics",
                "practice",
                "readiness",
                "board",
                "has_activity",
            },
        )
        self.assertEqual(report["subject"], "Mathematics")
        self.assertTrue(report["has_activity"])
        self.assertEqual(report["board"]["coverage_percent"], 100)
        self.assertEqual(report["readiness"]["change"], 22)

    def test_empty_term_is_flagged_inactive_never_invented(self):
        report = self.build(
            attendance_outcomes=[],
            quiz_rows=[],
            practice_outcomes=[],
            readiness_start=None,
            readiness_now=None,
        )
        self.assertFalse(report["has_activity"])
        self.assertIsNone(report["practice"])
        self.assertEqual(report["quiz_topics"], [])
        self.assertIsNone(report["attendance"]["attendance_rate_percent"])

    def test_none_inputs_are_tolerated(self):
        report = self.build(
            attendance_outcomes=None,
            quiz_rows=None,
            practice_outcomes=None,
            readiness_start=None,
            readiness_now=None,
            lessons=None,
            completed_lessons=None,
            attended_session_ids=None,
        )
        self.assertFalse(report["has_activity"])
        self.assertIsNone(report["board"])


if __name__ == "__main__":
    unittest.main()
