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

"""The Board's coverage assembly (decision #32), pinned standalone (no
frappe, no site — `python -m unittest tests.test_board_coverage`).

Loaded by file path rather than package import, matching
test_time_gates.py: workspace python modules import through an `rcore`
placeholder and only resolve inside a composed app; board_coverage.py is
deliberately frappe-free so this test runs anywhere python does."""

import importlib.util
import os
import unittest
from datetime import datetime, timedelta

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "board_coverage.py")
_spec = importlib.util.spec_from_file_location("rlms_board_coverage", _MODULE_PATH)
board_coverage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(board_coverage)


NOW = datetime(2026, 8, 13, 10, 0)

CHAPTERS = [
    {"name": "ch-1", "title": "Algebra", "sequence": 1},
    {"name": "ch-2", "title": "Geometry", "sequence": 2},
]

LESSONS = [
    {"name": "l-1", "chapter": "ch-1", "title": "Factorising", "sequence": 1, "session_id": "s-1"},
    {"name": "l-2", "chapter": "ch-1", "title": "Quadratics", "sequence": 2, "session_id": "s-2"},
    {"name": "l-3", "chapter": "ch-2", "title": "Triangles", "sequence": 1, "session_id": "s-3"},
    {"name": "l-4", "chapter": "ch-2", "title": "Circles", "sequence": 2, "session_id": "s-4"},
]


def build(**overrides):
    kwargs = dict(
        subject_label="Mathematics",
        chapters=CHAPTERS,
        lessons=LESSONS,
        completed_lessons=set(),
        attended_session_ids=set(),
        session_schedule={},
        cohort_progress=[],
        now=NOW,
    )
    kwargs.update(overrides)
    return board_coverage.build_term(**kwargs)


def flat_bands(term):
    return [b for t in term["topics"] for b in t["bands"]]


class TestBandAssignment(unittest.TestCase):
    def test_completed_lessons_are_covered_current_is_first_gap(self):
        term = build(completed_lessons={"l-1"})
        self.assertEqual(flat_bands(term), ["covered", "current", "upcoming", "upcoming"])

    def test_attended_session_counts_as_covered_too(self):
        # Watching live and finishing the lesson are BOTH honest coverage.
        term = build(attended_session_ids={"s-1"})
        self.assertEqual(flat_bands(term), ["covered", "current", "upcoming", "upcoming"])

    def test_nothing_covered_puts_current_on_the_first_band(self):
        term = build()
        self.assertEqual(flat_bands(term), ["current", "upcoming", "upcoming", "upcoming"])

    def test_all_covered_has_no_current_band(self):
        term = build(completed_lessons={"l-1", "l-2", "l-3", "l-4"})
        self.assertEqual(flat_bands(term), ["covered"] * 4)

    def test_current_sits_at_the_first_gap_even_past_later_coverage(self):
        # A student who jumped ahead: the camera still sits at the first gap.
        term = build(completed_lessons={"l-1", "l-3"})
        self.assertEqual(flat_bands(term), ["covered", "current", "covered", "upcoming"])

    def test_topics_follow_chapter_order_and_carry_titles(self):
        term = build()
        self.assertEqual([t["name"] for t in term["topics"]], ["Algebra", "Geometry"])
        self.assertEqual([len(t["bands"]) for t in term["topics"]], [2, 2])

    def test_chapter_without_lessons_is_skipped_not_an_empty_row(self):
        term = build(chapters=CHAPTERS + [{"name": "ch-3", "title": "Empty", "sequence": 3}])
        self.assertEqual([t["name"] for t in term["topics"]], ["Algebra", "Geometry"])

    def test_label_is_the_calendar_quarter_term(self):
        self.assertEqual(build()["label"], "Term 3 · Mathematics")
        self.assertEqual(
            build(now=datetime(2026, 2, 1))["label"], "Term 1 · Mathematics"
        )


class TestEmptyCourse(unittest.TestCase):
    def test_no_lessons_means_no_map(self):
        # None, not an empty canvas: the client falls through to the honest
        # coming-soon state (decision #47).
        self.assertIsNone(build(lessons=[]))
        self.assertIsNone(build(chapters=[], lessons=[]))

    def test_completely_empty_inputs_are_tolerated(self):
        self.assertIsNone(
            board_coverage.build_term(
                subject_label="Mathematics",
                chapters=None,
                lessons=None,
                completed_lessons=None,
                attended_session_ids=None,
                session_schedule=None,
                cohort_progress=None,
                now=NOW,
            )
        )


class TestLiveNow(unittest.TestCase):
    def test_topic_is_live_during_its_sessions_window(self):
        term = build(session_schedule={"s-3": NOW - timedelta(minutes=30)})
        self.assertEqual([t["live_now"] for t in term["topics"]], [False, True])

    def test_live_from_the_first_second(self):
        self.assertTrue(board_coverage.is_live_now(NOW, NOW))

    def test_not_live_before_start_or_after_the_window(self):
        self.assertFalse(board_coverage.is_live_now(NOW + timedelta(minutes=1), NOW))
        self.assertFalse(
            board_coverage.is_live_now(NOW - board_coverage.LIVE_NOW_WINDOW, NOW)
        )

    def test_unscheduled_session_is_never_live(self):
        self.assertFalse(board_coverage.is_live_now(None, NOW))
        term = build(session_schedule={})
        self.assertEqual([t["live_now"] for t in term["topics"]], [False, False])


class TestCohortRange(unittest.TestCase):
    def test_percentiles_map_onto_band_counts(self):
        # 8 cohort members over 4 bands: nearest-rank 25th pct = 2nd value,
        # 75th pct = 6th value of the sorted list.
        progress = [0, 10, 25, 40, 50, 60, 80, 100]
        low, high = board_coverage.cohort_band_range(progress, 4)
        self.assertEqual((low, high), (round(10 / 100 * 4), round(60 / 100 * 4)))

    def test_single_member_cohort_collapses_to_one_point(self):
        self.assertEqual(board_coverage.cohort_band_range([50], 10), (5, 5))

    def test_empty_cohort_is_null_null_never_invented(self):
        self.assertEqual(board_coverage.cohort_band_range([], 10), (None, None))
        self.assertEqual(board_coverage.cohort_band_range(None, 10), (None, None))
        term = build(cohort_progress=[])
        self.assertIsNone(term["cohort_low"])
        self.assertIsNone(term["cohort_high"])

    def test_none_progress_reads_as_zero_and_values_clamp(self):
        low, high = board_coverage.cohort_band_range([None, 250, -10], 10)
        self.assertEqual((low, high), (0, 10))

    def test_range_lands_in_the_term_dict(self):
        term = build(cohort_progress=[0, 10, 25, 40, 50, 60, 80, 100])
        self.assertEqual(term["cohort_low"], round(10 / 100 * 4))
        self.assertEqual(term["cohort_high"], round(60 / 100 * 4))


class TestContractShape(unittest.TestCase):
    """The dict IS the JSON contract with the client's BoardTerm.fromJson —
    key names here must match board_models.dart exactly."""

    def test_top_level_keys(self):
        term = build(completed_lessons={"l-1"}, cohort_progress=[50])
        self.assertEqual(
            set(term.keys()), {"label", "cohort_low", "cohort_high", "topics"}
        )

    def test_topic_keys_and_band_vocabulary(self):
        term = build(completed_lessons={"l-1"})
        for topic in term["topics"]:
            self.assertEqual(set(topic.keys()), {"name", "live_now", "bands"})
            for band in topic["bands"]:
                self.assertIn(band, ("covered", "current", "upcoming"))


if __name__ == "__main__":
    unittest.main()
