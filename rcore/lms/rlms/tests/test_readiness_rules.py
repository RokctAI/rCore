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

"""Decision #42 gap 5 — the Readiness Score formula. The scoring the app
renders (and the shareable credential freezes) must be deterministic and
match the documented weights, so it lives in the frappe-free
readiness_rules.py and is exercised here without a bench/site.

Loaded by file path rather than package import on purpose, same as every
other test in this directory: the packaged module imports through an
`rcore` placeholder inside a composed app, but readiness_rules.py is
deliberately frappe-free, so this test runs anywhere python does.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "readiness_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_readiness_rules", _MODULE_PATH)
readiness_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(readiness_rules)


class TestComponents(unittest.TestCase):
    def test_mastery_is_correct_over_all_outcomes(self):
        # 6 correct, 2 incorrect, 2 skipped: skips count in the denominator —
        # an unanswered exam question earns nothing.
        self.assertAlmostEqual(
            readiness_rules.mastery_component(correct=6, incorrect=2, skipped=2), 0.6
        )

    def test_mastery_with_no_outcomes_is_absent_not_zero(self):
        self.assertIsNone(readiness_rules.mastery_component(0, 0, 0))

    def test_mastery_all_skips_is_zero_not_absent(self):
        # Data exists — a student who skips every question has EARNED a zero.
        self.assertEqual(readiness_rules.mastery_component(0, 0, 5), 0.0)

    def test_coverage_is_mean_progress(self):
        self.assertAlmostEqual(
            readiness_rules.coverage_component([50, 100]), 0.75
        )

    def test_coverage_with_no_enrollments_is_absent(self):
        self.assertIsNone(readiness_rules.coverage_component([]))
        self.assertIsNone(readiness_rules.coverage_component(None))

    def test_coverage_clamps_out_of_range_progress(self):
        # A backend glitch reporting 120% must not mint a >100 credential.
        self.assertAlmostEqual(readiness_rules.coverage_component([120]), 1.0)
        self.assertAlmostEqual(readiness_rules.coverage_component([-10]), 0.0)

    def test_coverage_treats_none_progress_as_zero(self):
        # A brand-new enrollment row with progress NULL counts as 0% covered.
        self.assertAlmostEqual(readiness_rules.coverage_component([None, 100]), 0.5)

    def test_consistency_counts_both_skip_kinds_as_missed(self):
        # Same stance as alert_rules: answering the skip gate is better
        # behaviour, but the session was still missed.
        self.assertAlmostEqual(
            readiness_rules.consistency_component(
                attended=3, skipped_answered=1, skipped_unanswered=1
            ),
            0.6,
        )

    def test_consistency_with_no_events_is_absent(self):
        self.assertIsNone(readiness_rules.consistency_component(0, 0, 0))


class TestReadinessScore(unittest.TestCase):
    def test_documented_weights_apply(self):
        # 0.5*0.8 + 0.3*0.6 + 0.2*0.5 = 0.68 -> 68.
        verdict = readiness_rules.readiness_score(0.8, 0.6, 0.5)
        self.assertEqual(verdict["score"], 68)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(
            readiness_rules.WEIGHT_MASTERY
            + readiness_rules.WEIGHT_COVERAGE
            + readiness_rules.WEIGHT_CONSISTENCY,
            1.0,
        )

    def test_perfect_everything_is_100(self):
        self.assertEqual(readiness_rules.readiness_score(1.0, 1.0, 1.0)["score"], 100)

    def test_nothing_earned_is_0(self):
        self.assertEqual(readiness_rules.readiness_score(0.0, 0.0, 0.0)["score"], 0)

    def test_absent_component_renormalises_instead_of_dragging_down(self):
        # No attendance data yet: mastery 0.8 and coverage 0.6 renormalise
        # over 0.8 total weight -> (0.4 + 0.18) / 0.8 = 0.725 -> 73, NOT
        # 58 (which is what treating the missing signal as zero would give).
        verdict = readiness_rules.readiness_score(0.8, 0.6, None)
        self.assertEqual(verdict["score"], 73)
        self.assertNotIn("consistency", verdict["components"])

    def test_single_component_stands_alone(self):
        verdict = readiness_rules.readiness_score(None, 0.5, None)
        self.assertEqual(verdict["score"], 50)
        self.assertEqual(list(verdict["components"]), ["coverage"])

    def test_all_absent_is_no_score(self):
        # A credential must never be minted from zero evidence.
        self.assertIsNone(readiness_rules.readiness_score(None, None, None))

    def test_rounding_is_half_up(self):
        # mastery-only 0.845 -> 84.5 -> 85 (a parent reads 84.5 as 85).
        self.assertEqual(readiness_rules.readiness_score(0.845, None, None)["score"], 85)

    def test_components_are_rounded_percentages(self):
        verdict = readiness_rules.readiness_score(0.845, 0.6, None)
        self.assertEqual(verdict["components"], {"mastery": 85, "coverage": 60})

    def test_determinism(self):
        # The exact same inputs always mint the exact same score.
        first = readiness_rules.readiness_score(0.731, 0.42, 0.9)
        second = readiness_rules.readiness_score(0.731, 0.42, 0.9)
        self.assertEqual(first, second)


class TestBands(unittest.TestCase):
    def test_band_thresholds(self):
        self.assertEqual(readiness_rules.readiness_band(100), "Exam Ready")
        self.assertEqual(readiness_rules.readiness_band(80), "Exam Ready")
        self.assertEqual(readiness_rules.readiness_band(79), "On Track")
        self.assertEqual(readiness_rules.readiness_band(60), "On Track")
        self.assertEqual(readiness_rules.readiness_band(59), "Building")
        self.assertEqual(readiness_rules.readiness_band(40), "Building")
        self.assertEqual(readiness_rules.readiness_band(39), "Needs Focus")
        self.assertEqual(readiness_rules.readiness_band(0), "Needs Focus")

    def test_score_dict_band_matches_band_function(self):
        verdict = readiness_rules.readiness_score(0.8, 0.6, 0.5)
        self.assertEqual(
            verdict["band"], readiness_rules.readiness_band(verdict["score"])
        )


if __name__ == "__main__":
    unittest.main()
