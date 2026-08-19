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

"""Decision #42 gap 4 — weekly-league mechanics: point weights, ranking,
cohorting, promotion/demotion at week close, and leaderboard display
names.

Loaded by file path on purpose (same reason as test_alert_rules.py):
league_rules.py is deliberately frappe-free, so this runs anywhere
python does — no bench, no site, no substitution.
"""

import importlib.util
import os
import unittest
from datetime import date

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "league_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_league_rules", _MODULE_PATH)
league_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(league_rules)


class TestWeeklyPoints(unittest.TestCase):
    def test_documented_weights(self):
        # The documented defaults: attendance 10, quiz 5, lesson 5.
        self.assertEqual(league_rules.ATTENDANCE_POINTS, 10)
        self.assertEqual(league_rules.QUIZ_POINTS, 5)
        self.assertEqual(league_rules.LESSON_POINTS, 5)

    def test_blend(self):
        self.assertEqual(
            league_rules.weekly_points(
                attended=3, quizzes_completed=4, lessons_completed=2
            ),
            3 * 10 + 4 * 5 + 2 * 5,
        )

    def test_no_activity_is_zero(self):
        self.assertEqual(league_rules.weekly_points(), 0)


class TestRankStandings(unittest.TestCase):
    def test_orders_by_points_descending(self):
        standings = league_rules.rank_standings({"a": 10, "b": 30, "c": 20})
        self.assertEqual([s["student"] for s in standings], ["b", "c", "a"])
        self.assertEqual([s["rank"] for s in standings], [1, 2, 3])

    def test_ties_share_a_rank_competition_style(self):
        standings = league_rules.rank_standings({"a": 20, "b": 20, "c": 10})
        self.assertEqual([s["rank"] for s in standings], [1, 1, 3])

    def test_tie_display_order_is_stable_by_student_id(self):
        standings = league_rules.rank_standings({"zz": 20, "aa": 20})
        self.assertEqual([s["student"] for s in standings], ["aa", "zz"])

    def test_empty_cohort(self):
        self.assertEqual(league_rules.rank_standings({}), [])


class TestAssignCohorts(unittest.TestCase):
    def test_chunks_of_cohort_size(self):
        students = [f"s{i}" for i in range(65)]
        cohorts = league_rules.assign_cohorts(students)
        self.assertEqual([len(c) for c in cohorts], [30, 30, 5])
        self.assertEqual([s for c in cohorts for s in c], students)

    def test_empty_input_yields_no_cohorts(self):
        self.assertEqual(league_rules.assign_cohorts([]), [])

    def test_rejects_nonsense_size(self):
        with self.assertRaises(ValueError):
            league_rules.assign_cohorts(["a"], cohort_size=0)


class TestCloseCohort(unittest.TestCase):
    def _full_cohort(self):
        # 30 students, points descending so ranks are 1..30.
        return league_rules.rank_standings(
            {f"s{i:02d}": 1000 - i for i in range(30)}
        )

    def test_top_ten_promote_bottom_five_demote(self):
        outcomes = league_rules.close_cohort(self._full_cohort(), "Silver")
        movements = [o["movement"] for o in outcomes]
        self.assertEqual(movements[:10], [league_rules.PROMOTED] * 10)
        self.assertEqual(movements[10:25], [league_rules.STAYED] * 15)
        self.assertEqual(movements[25:], [league_rules.DEMOTED] * 5)
        self.assertEqual(outcomes[0]["next_tier"], "Gold")
        self.assertEqual(outcomes[-1]["next_tier"], "Bronze")

    def test_diamond_top_cannot_promote_further(self):
        outcomes = league_rules.close_cohort(self._full_cohort(), "Diamond")
        self.assertEqual(outcomes[0]["movement"], league_rules.STAYED)
        self.assertEqual(outcomes[0]["next_tier"], "Diamond")
        # The bottom still demotes out of Diamond.
        self.assertEqual(outcomes[-1]["movement"], league_rules.DEMOTED)
        self.assertEqual(outcomes[-1]["next_tier"], "Sapphire")

    def test_bronze_bottom_cannot_demote_further(self):
        outcomes = league_rules.close_cohort(self._full_cohort(), "Bronze")
        self.assertEqual(outcomes[-1]["movement"], league_rules.STAYED)
        self.assertEqual(outcomes[-1]["next_tier"], "Bronze")

    def test_small_cohort_promotion_wins_over_demotion(self):
        # 8 students: everyone is in the top 10, so nobody demotes even
        # though ranks 4..8 fall in the bottom-5 window.
        standings = league_rules.rank_standings(
            {f"s{i}": 100 - i for i in range(8)}
        )
        outcomes = league_rules.close_cohort(standings, "Silver")
        self.assertTrue(
            all(o["movement"] == league_rules.PROMOTED for o in outcomes)
        )

    def test_snapshot_carries_points_and_rank(self):
        standings = league_rules.rank_standings({"a": 50, "b": 40})
        outcomes = league_rules.close_cohort(standings, "Gold")
        self.assertEqual(outcomes[0], {
            "student": "a",
            "points": 50,
            "rank": 1,
            "movement": league_rules.PROMOTED,
            "next_tier": "Sapphire",
        })


class TestWeekStartOf(unittest.TestCase):
    def test_monday_maps_to_itself(self):
        self.assertEqual(
            league_rules.week_start_of(date(2026, 8, 10)), date(2026, 8, 10)
        )

    def test_sunday_maps_back_to_its_monday(self):
        self.assertEqual(
            league_rules.week_start_of(date(2026, 8, 16)), date(2026, 8, 10)
        )


class TestDisplayName(unittest.TestCase):
    def test_first_name_plus_last_initial(self):
        self.assertEqual(league_rules.display_name("Thabo Mokoena"), "Thabo M.")

    def test_middle_names_are_dropped(self):
        self.assertEqual(
            league_rules.display_name("Anna Maria van Wyk"), "Anna W."
        )

    def test_single_word_name_stands_alone(self):
        self.assertEqual(league_rules.display_name("Thabo"), "Thabo")

    def test_empty_name_answers_fallback(self):
        self.assertEqual(league_rules.display_name(""), "Student")
        self.assertEqual(league_rules.display_name(None), "Student")


if __name__ == "__main__":
    unittest.main()
