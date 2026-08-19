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
# See license.txt

"""
Pure-python tests for the credit scorecard core
(rlending/decision_engine/scorecard.py).

Unlike this directory's FrappeTestCase suites (which import via the
`rcore` template placeholder and only run post-compose against a live
bench), scorecard.py imports nothing from frappe and has no templated imports,
so these tests run directly in this source repo:

    python3 polaris/frappe/src/tests/test_credit_scorecard.py
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rlending.decision_engine.scorecard import (  # noqa: E402
    COLD_START_WEIGHTS,
    COMPONENT_WEIGHTS,
    DEFAULT_BANDS,
    REASON_ACTIVE_LOAN,
    REASON_KYC_INCOMPLETE,
    build_loan_history_records,
    derive_cold_start_weights,
    evaluate_application,
    map_score_to_band,
    per_loan_credit,
    score_affordability_ratio,
    score_amount_to_income,
    score_kyc_quality,
    score_repayment_history,
)


def make_inputs(**overrides):
    """A fully-scoreable applicant; individual tests break specific pieces."""
    inputs = {
        "kyc_complete": 1,
        "has_active_loan": 0,
        "monthly_income": 10000.0,
        "monthly_expenses": 4000.0,
        "monthly_repayment": 1500.0,
        "loan_amount": 5000.0,
        "max_loan_amount": 10000.0,
        "loan_history": [{"outcome": "repaid", "days_late": 0, "age_days": 0}],
        "kyc_quality_checks": {"a": True, "b": True, "c": True},
    }
    inputs.update(overrides)
    return inputs


def make_config(**overrides):
    config = {
        "min_disposable_income": 1000.0,
        "first_loan_max_amount": 2000.0,
    }
    config.update(overrides)
    return config


class TestWeights(unittest.TestCase):
    def test_doc_weights_are_45_30_15_10_and_sum_to_100(self):
        self.assertEqual(COMPONENT_WEIGHTS["repayment_history_score"], 45.0)
        self.assertEqual(COMPONENT_WEIGHTS["affordability_ratio_score"], 30.0)
        self.assertEqual(COMPONENT_WEIGHTS["amount_to_income_score"], 15.0)
        self.assertEqual(COMPONENT_WEIGHTS["kyc_quality_score"], 10.0)
        self.assertEqual(sum(COMPONENT_WEIGHTS.values()), 100.0)

    def test_cold_start_redistributes_component_1_into_2_and_3_only(self):
        self.assertEqual(COLD_START_WEIGHTS["repayment_history_score"], 0.0)
        self.assertEqual(COLD_START_WEIGHTS["affordability_ratio_score"], 60.0)
        self.assertEqual(COLD_START_WEIGHTS["amount_to_income_score"], 30.0)
        # Component 4 is explicitly not a recipient in the doc.
        self.assertEqual(COLD_START_WEIGHTS["kyc_quality_score"], 10.0)
        self.assertEqual(sum(COLD_START_WEIGHTS.values()), 100.0)

    def test_cold_start_derivation_is_proportional_for_custom_weights(self):
        derived = derive_cold_start_weights(
            {
                "repayment_history_score": 40.0,
                "affordability_ratio_score": 20.0,
                "amount_to_income_score": 20.0,
                "kyc_quality_score": 20.0,
            }
        )
        self.assertEqual(derived["repayment_history_score"], 0.0)
        self.assertEqual(derived["affordability_ratio_score"], 40.0)
        self.assertEqual(derived["amount_to_income_score"], 40.0)
        self.assertEqual(derived["kyc_quality_score"], 20.0)


class TestRepaymentHistoryComponent(unittest.TestCase):
    def test_on_time_full_repayment_gets_full_credit(self):
        self.assertEqual(
            per_loan_credit({"outcome": "repaid", "days_late": 0}), 100.0
        )

    def test_late_repayment_scales_down_linearly(self):
        self.assertEqual(
            per_loan_credit({"outcome": "repaid", "days_late": 15}), 50.0
        )
        self.assertEqual(
            per_loan_credit({"outcome": "repaid", "days_late": 30}), 0.0
        )
        self.assertEqual(
            per_loan_credit({"outcome": "repaid", "days_late": 90}), 0.0
        )

    def test_default_is_heavily_negative(self):
        self.assertEqual(per_loan_credit({"outcome": "defaulted"}), -100.0)

    def test_unverifiable_timeliness_earns_zero_not_full_credit(self):
        self.assertEqual(per_loan_credit({"outcome": "unverifiable"}), 0.0)

    def test_no_history_returns_none_not_a_neutral_score(self):
        self.assertIsNone(score_repayment_history([]))
        self.assertIsNone(score_repayment_history(None))

    def test_single_default_clamps_to_zero_component_score(self):
        score = score_repayment_history(
            [{"outcome": "defaulted", "age_days": 0}]
        )
        self.assertEqual(score, 0.0)

    def test_default_drags_down_an_otherwise_perfect_record(self):
        score = score_repayment_history(
            [
                {"outcome": "repaid", "days_late": 0, "age_days": 0},
                {"outcome": "defaulted", "age_days": 0},
            ]
        )
        self.assertEqual(score, 0.0)  # (100 - 100) / 2

    def test_recent_default_weighs_more_than_old_default(self):
        recent_default = score_repayment_history(
            [
                {"outcome": "defaulted", "age_days": 0},
                {"outcome": "repaid", "days_late": 0, "age_days": 730},
            ]
        )
        old_default = score_repayment_history(
            [
                {"outcome": "defaulted", "age_days": 730},
                {"outcome": "repaid", "days_late": 0, "age_days": 0},
            ]
        )
        self.assertLess(recent_default, old_default)


class TestOtherComponents(unittest.TestCase):
    def test_affordability_ratio_curve(self):
        # ratio 0.25 of disposable income -> 75
        self.assertEqual(score_affordability_ratio(1500, 10000, 4000), 75.0)
        # repayment consumes all disposable income -> 0
        self.assertEqual(score_affordability_ratio(6000, 10000, 4000), 0.0)
        # beyond -> still 0, never negative
        self.assertEqual(score_affordability_ratio(9000, 10000, 4000), 0.0)
        # no disposable income at all -> 0
        self.assertEqual(score_affordability_ratio(100, 4000, 4000), 0.0)
        self.assertEqual(score_affordability_ratio(100, 3000, 4000), 0.0)

    def test_amount_to_income_curve(self):
        self.assertEqual(score_amount_to_income(5000, 10000), 50.0)
        self.assertEqual(score_amount_to_income(10000, 10000), 0.0)
        self.assertEqual(score_amount_to_income(20000, 10000), 0.0)
        self.assertEqual(score_amount_to_income(5000, 0), 0.0)

    def test_kyc_quality_is_graduated_and_thin_data_scores_zero(self):
        self.assertEqual(score_kyc_quality({"a": True, "b": True}), 100.0)
        self.assertEqual(score_kyc_quality({"a": True, "b": False}), 50.0)
        self.assertEqual(score_kyc_quality({"a": False, "b": False}), 0.0)
        self.assertEqual(score_kyc_quality({}), 0.0)


class TestHardGates(unittest.TestCase):
    def test_missing_kyc_declines_with_doc_reason_no_score_override(self):
        result = evaluate_application(make_inputs(kyc_complete=0), make_config())
        self.assertEqual(result["decision"], "Decline")
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["max_allowed_amount"], 0)
        self.assertEqual(result["reasons"][0]["code"], "kyc_incomplete")
        self.assertEqual(result["reasons"][0]["reason"], REASON_KYC_INCOMPLETE)
        self.assertEqual(REASON_KYC_INCOMPLETE, "KYC verification incomplete")

    def test_active_loan_declines_with_doc_reason(self):
        result = evaluate_application(make_inputs(has_active_loan=1), make_config())
        self.assertEqual(result["decision"], "Decline")
        self.assertEqual(result["reasons"][0]["code"], "active_loan")
        self.assertEqual(result["reasons"][0]["reason"], REASON_ACTIVE_LOAN)
        self.assertEqual(
            REASON_ACTIVE_LOAN, "Existing active loan must be settled first"
        )

    def test_disposable_income_below_floor_declines(self):
        # disposable = 500 < min 1000
        result = evaluate_application(
            make_inputs(monthly_income=5000, monthly_expenses=4500, monthly_repayment=100),
            make_config(),
        )
        self.assertEqual(result["decision"], "Decline")
        self.assertEqual(result["reasons"][0]["code"], "affordability_floor")

    def test_disposable_income_exactly_at_floor_declines(self):
        # Seeded rule is "Greater Than minDisposableIncome": equality fails.
        result = evaluate_application(
            make_inputs(monthly_income=5000, monthly_expenses=4000, monthly_repayment=100),
            make_config(min_disposable_income=1000.0),
        )
        self.assertEqual(result["decision"], "Decline")
        self.assertEqual(result["reasons"][0]["code"], "affordability_floor")

    def test_repayment_burden_breaching_floor_declines(self):
        # disposable 5000, repayment 4500 leaves 500 < min 1000
        result = evaluate_application(
            make_inputs(monthly_income=10000, monthly_expenses=5000, monthly_repayment=4500),
            make_config(),
        )
        self.assertEqual(result["decision"], "Decline")
        self.assertEqual(result["reasons"][0]["code"], "repayment_unaffordable")


class TestFailHonestPending(unittest.TestCase):
    def assert_pending_with(self, result, code):
        self.assertEqual(result["decision"], "Pending")
        self.assertIsNone(result["score"])
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["max_allowed_amount"], 0)
        self.assertIn(code, [r["code"] for r in result["reasons"]])

    def test_unseeded_min_disposable_income_pends(self):
        result = evaluate_application(
            make_inputs(), make_config(min_disposable_income=None)
        )
        self.assert_pending_with(result, "min_disposable_income_not_configured")

    def test_missing_income_pends(self):
        result = evaluate_application(
            make_inputs(monthly_income=None), make_config()
        )
        self.assert_pending_with(result, "monthly_income_missing")

    def test_zero_income_pends_rather_than_fabricating_a_score(self):
        # Currency fields default to 0, so 0 is indistinguishable from unset.
        result = evaluate_application(make_inputs(monthly_income=0), make_config())
        self.assert_pending_with(result, "monthly_income_missing")

    def test_missing_expenses_pends(self):
        result = evaluate_application(
            make_inputs(monthly_expenses=None), make_config()
        )
        self.assert_pending_with(result, "monthly_expenses_missing")

    def test_zero_expenses_pends_rather_than_maximizing_disposable_income(self):
        # Frappe coerces unset Currency fields to 0 on save, so declared-0 is
        # indistinguishable from unset. Treating it as scored would grant the
        # applicant maximum disposable income — instead it pends (mirrors the
        # zero-income handling; errs toward Pending, never approval).
        result = evaluate_application(
            make_inputs(monthly_expenses=0), make_config()
        )
        self.assert_pending_with(result, "monthly_expenses_missing")

    def test_negative_expenses_pends(self):
        result = evaluate_application(
            make_inputs(monthly_expenses=-100), make_config()
        )
        self.assert_pending_with(result, "monthly_expenses_missing")

    def test_positive_expenses_are_still_scored(self):
        result = evaluate_application(
            make_inputs(monthly_expenses=4000.0), make_config()
        )
        self.assertEqual(result["decision"], "Approve")
        self.assertEqual(result["score"], 85)

    def test_underivable_repayment_burden_pends(self):
        result = evaluate_application(
            make_inputs(monthly_repayment=None), make_config()
        )
        self.assert_pending_with(result, "repayment_burden_unavailable")

    def test_unavailable_loan_history_pends(self):
        # None means "could not be determined" — distinct from [] (cold start).
        result = evaluate_application(
            make_inputs(loan_history=None), make_config()
        )
        self.assert_pending_with(result, "loan_history_unavailable")

    def test_multiple_blockers_are_all_reported(self):
        result = evaluate_application(
            make_inputs(monthly_income=None, monthly_repayment=None),
            make_config(min_disposable_income=None),
        )
        codes = [r["code"] for r in result["reasons"]]
        self.assertIn("min_disposable_income_not_configured", codes)
        self.assertIn("monthly_income_missing", codes)
        self.assertIn("repayment_burden_unavailable", codes)

    def test_gate_declines_take_precedence_over_pending(self):
        # Gates 1-2 need no config; a definite decline beats "Pending".
        result = evaluate_application(
            make_inputs(kyc_complete=0, monthly_income=None),
            make_config(min_disposable_income=None),
        )
        self.assertEqual(result["decision"], "Decline")


class TestScoringAndBands(unittest.TestCase):
    def test_worked_example_established_borrower_scores_85(self):
        # history 100 (0.45*100=45) + affordability 75 (0.30*75=22.5)
        # + amount-to-income 50 (0.15*50=7.5) + kyc 100 (0.10*100=10) = 85
        result = evaluate_application(make_inputs(), make_config())
        self.assertEqual(result["score"], 85)
        self.assertEqual(result["decision"], "Approve")
        self.assertEqual(result["risk_level"], "Very Low Risk")
        self.assertTrue(result["is_eligible"])
        self.assertFalse(result["cold_start"])
        # 80-100 band: requested amount, no config-max clause in the doc.
        self.assertEqual(result["max_allowed_amount"], 5000.0)

    def test_worked_example_cold_start_scores_70_and_is_capped(self):
        # weights 0/60/30/10: 0.60*75 + 0.30*50 + 0.10*100 = 70
        result = evaluate_application(
            make_inputs(loan_history=[]), make_config()
        )
        self.assertEqual(result["score"], 70)
        self.assertTrue(result["cold_start"])
        self.assertTrue(result["is_eligible"])
        # 60-79 band grants min(requested, config max) = 5000, then the
        # cold-start firstLoanMaxAmount ceiling (2000) applies regardless.
        self.assertEqual(result["max_allowed_amount"], 2000.0)

    def test_cold_start_without_first_loan_cap_pends(self):
        result = evaluate_application(
            make_inputs(loan_history=[]),
            make_config(first_loan_max_amount=None),
        )
        self.assertEqual(result["decision"], "Pending")
        self.assertIn(
            "first_loan_max_amount_not_configured",
            [r["code"] for r in result["reasons"]],
        )

    def test_score_40_lands_in_reduced_band_with_half_amount(self):
        # defaulted history -> 0 (0.45*0=0); affordability ratio 0.1 -> 90
        # (0.30*90=27); amount ratio 0.8 -> 20 (0.15*20=3); kyc 100 (10) = 40
        result = evaluate_application(
            make_inputs(
                loan_history=[{"outcome": "defaulted", "age_days": 0}],
                monthly_income=10000,
                monthly_expenses=4000,
                monthly_repayment=600,
                loan_amount=8000,
                max_loan_amount=10000,
            ),
            make_config(),
        )
        self.assertEqual(result["score"], 40)
        self.assertTrue(result["is_eligible"])
        self.assertEqual(result["risk_level"], "Medium Risk")
        # reduced fraction (0.5) of min(requested 8000, config max 10000)
        self.assertEqual(result["max_allowed_amount"], 4000.0)

    def test_fractional_score_truncates_down_and_39_declines(self):
        # history defaulted -> 0; kyc empty -> 0; affordability ~99.99983
        # (0.30*x ~ 29.99995); amount ratio 0.34 -> 66 (0.15*66=9.9);
        # raw ~ 39.89995 -> int() 39 -> decline band.
        result = evaluate_application(
            make_inputs(
                loan_history=[{"outcome": "defaulted", "age_days": 0}],
                kyc_quality_checks={},
                monthly_income=10000,
                monthly_expenses=4000,
                monthly_repayment=0.01,
                loan_amount=3400,
            ),
            make_config(),
        )
        self.assertEqual(result["score"], 39)
        self.assertEqual(result["decision"], "Decline")
        self.assertFalse(result["is_eligible"])
        self.assertEqual(result["max_allowed_amount"], 0)

    def test_60_to_79_band_caps_at_config_max(self):
        result = evaluate_application(
            make_inputs(loan_history=[], max_loan_amount=4000),
            make_config(first_loan_max_amount=100000.0),
        )
        self.assertEqual(result["score"], 70)
        self.assertEqual(result["max_allowed_amount"], 4000.0)

    def test_60_to_79_band_without_config_max_pends(self):
        result = evaluate_application(
            make_inputs(loan_history=[], max_loan_amount=None),
            make_config(first_loan_max_amount=100000.0),
        )
        self.assertEqual(result["decision"], "Pending")
        self.assertIn(
            "max_loan_amount_not_configured",
            [r["code"] for r in result["reasons"]],
        )

    def test_band_boundaries_39_40_59_60_79_80(self):
        self.assertFalse(map_score_to_band(0)["is_eligible"])
        self.assertFalse(map_score_to_band(39)["is_eligible"])
        band_40 = map_score_to_band(40)
        self.assertTrue(band_40["is_eligible"])
        self.assertEqual(band_40["max_amount_policy"], "reduced_fraction")
        self.assertEqual(map_score_to_band(59)["max_amount_policy"], "reduced_fraction")
        band_60 = map_score_to_band(60)
        self.assertEqual(band_60["max_amount_policy"], "requested_up_to_config_max")
        self.assertEqual(map_score_to_band(79)["max_amount_policy"], "requested_up_to_config_max")
        self.assertEqual(map_score_to_band(80)["max_amount_policy"], "requested")
        self.assertEqual(map_score_to_band(100)["max_amount_policy"], "requested")

    def test_default_bands_cover_0_to_100_contiguously(self):
        edges = sorted(
            (band["min_score"], band["max_score"]) for band in DEFAULT_BANDS
        )
        self.assertEqual(edges[0][0], 0)
        self.assertEqual(edges[-1][1], 100)
        for (_, prev_max), (next_min, _) in zip(edges, edges[1:]):
            self.assertEqual(next_min, prev_max + 1)


class TestLoanHistoryRecordBuilding(unittest.TestCase):
    AS_OF = datetime.date(2026, 8, 14)

    def test_open_loans_are_excluded_from_history(self):
        records = build_loan_history_records(
            [{"name": "L1", "status": "Disbursed"}], [], self.AS_OF
        )
        self.assertEqual(records, [])

    def test_written_off_loan_is_a_default(self):
        records = build_loan_history_records(
            [
                {
                    "name": "L1",
                    "status": "Written Off",
                    "closure_date": datetime.date(2026, 8, 14),
                }
            ],
            [],
            self.AS_OF,
        )
        self.assertEqual(records[0]["outcome"], "defaulted")
        self.assertEqual(records[0]["age_days"], 0)

    def test_on_time_closure_from_reconstructed_due_date(self):
        # due = 2025-01-15 + 3 months = 2025-04-15; last repayment 2025-04-10
        records = build_loan_history_records(
            [
                {
                    "name": "L1",
                    "status": "Closed",
                    "disbursement_date": datetime.date(2025, 1, 15),
                    "repayment_periods": 3,
                    "closure_date": datetime.date(2025, 4, 10),
                }
            ],
            [{"against_loan": "L1", "posting_date": datetime.date(2025, 4, 10)}],
            self.AS_OF,
        )
        self.assertEqual(records[0]["outcome"], "repaid")
        self.assertEqual(records[0]["days_late"], 0)

    def test_late_closure_days_late_counted(self):
        records = build_loan_history_records(
            [
                {
                    "name": "L1",
                    "status": "Closed",
                    "disbursement_date": datetime.date(2025, 1, 15),
                    "repayment_periods": 3,
                }
            ],
            [{"against_loan": "L1", "posting_date": datetime.date(2025, 4, 30)}],
            self.AS_OF,
        )
        self.assertEqual(records[0]["outcome"], "repaid")
        self.assertEqual(records[0]["days_late"], 15)

    def test_repaid_loan_without_repayment_rows_is_unverifiable(self):
        records = build_loan_history_records(
            [
                {
                    "name": "L1",
                    "status": "Settled",
                    "disbursement_date": datetime.date(2025, 1, 15),
                    "repayment_periods": 3,
                }
            ],
            [],
            self.AS_OF,
        )
        self.assertEqual(records[0]["outcome"], "unverifiable")

    def test_repaid_loan_without_reconstructable_due_date_is_unverifiable(self):
        records = build_loan_history_records(
            [{"name": "L1", "status": "Closed"}],
            [{"against_loan": "L1", "posting_date": datetime.date(2025, 4, 30)}],
            self.AS_OF,
        )
        self.assertEqual(records[0]["outcome"], "unverifiable")

    def test_iso_date_strings_are_accepted(self):
        records = build_loan_history_records(
            [
                {
                    "name": "L1",
                    "status": "Closed",
                    "disbursement_date": "2025-01-31",
                    "repayment_periods": 1,
                }
            ],
            [{"against_loan": "L1", "posting_date": "2025-02-28"}],
            self.AS_OF,
        )
        # 2025-01-31 + 1 month clamps to 2025-02-28 -> on time
        self.assertEqual(records[0]["outcome"], "repaid")
        self.assertEqual(records[0]["days_late"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
