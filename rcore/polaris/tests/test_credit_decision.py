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
FrappeTestCase suite for the frappe-facing credit-decision wiring
(rlending/api/decision.py, LoanHistoryAnalyzer, seeds). Like this directory's
other suites, imports use the `rcore` template placeholder, so these run
post-compose against a live bench, not in this source repo. The pure scoring
math itself is covered by test_credit_scorecard.py, which does run here.
"""

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from rcore.polaris.rlending.api.decision import (
    _get_kyc_complete,
    _get_kyc_quality_checks,
    _get_monthly_repayment,
    _load_scoring_config,
)
from rcore.polaris.rlending.decision_engine.analyzers.loan_history_analyzer import (
    LoanHistoryAnalyzer,
)


def _make_app(**fields):
    app = MagicMock()
    app.get.side_effect = lambda key, default=None: fields.get(key, default)
    app.applicant_type = fields.get("applicant_type", "Customer")
    app.applicant = fields.get("applicant", "CUST-1")
    return app


class TestKycGateWiring(FrappeTestCase):
    @patch("rcore.polaris.rlending.api.decision.frappe.db.get_value")
    def test_verified_crm_lead_passes_gate(self, mock_get_value):
        def side_effect(doctype, filters, *args, **kwargs):
            if doctype == "Customer" and args[:1] == ("email_id",):
                return "cust@example.com"
            if doctype == "Customer" and args[:1] == ("mobile_no",):
                return None
            if doctype == "Lead" and filters == {"email_id": "cust@example.com"}:
                return "LEAD-1"
            if doctype == "Lead" and filters == "LEAD-1":
                return "Verified"
            return None

        mock_get_value.side_effect = side_effect
        self.assertEqual(_get_kyc_complete(_make_app()), 1)

    @patch("rcore.polaris.rlending.api.decision.frappe.db.get_value")
    def test_unverified_kyc_fails_gate(self, mock_get_value):
        def side_effect(doctype, filters, *args, **kwargs):
            if doctype == "Customer" and args[:1] == ("email_id",):
                return "cust@example.com"
            if doctype == "Lead" and filters == {"email_id": "cust@example.com"}:
                return "LEAD-1"
            if doctype == "Lead" and filters == "LEAD-1":
                return "Pending"
            return None

        mock_get_value.side_effect = side_effect
        self.assertEqual(_get_kyc_complete(_make_app()), 0)

    @patch("rcore.polaris.rlending.api.decision.frappe.db.get_value")
    def test_no_crm_lead_fails_gate_conservatively(self, mock_get_value):
        mock_get_value.return_value = None
        self.assertEqual(_get_kyc_complete(_make_app()), 0)

    def test_non_customer_applicant_fails_gate_conservatively(self):
        # No verification path exists for Employee applicants today; the gate
        # must not silently pass them.
        self.assertEqual(
            _get_kyc_complete(_make_app(applicant_type="Employee")), 0
        )


class TestRepaymentBurdenWiring(FrappeTestCase):
    def test_prefers_computed_emi(self):
        app = _make_app(repayment_amount=946, total_payable_amount=11352, repayment_periods=12)
        self.assertEqual(_get_monthly_repayment(app), 946.0)

    def test_falls_back_to_total_payable_over_periods(self):
        app = _make_app(repayment_amount=0, total_payable_amount=12000, repayment_periods=12)
        self.assertEqual(_get_monthly_repayment(app), 1000.0)

    def test_returns_none_when_underivable(self):
        # Fail-honest: the scorecard turns None into an explicit Pending.
        app = _make_app(repayment_amount=0, total_payable_amount=0, repayment_periods=0)
        self.assertIsNone(_get_monthly_repayment(app))


class TestKycQualityChecklist(FrappeTestCase):
    def test_well_formed_optional_fields_all_pass(self):
        checks = _get_kyc_quality_checks(
            _make_app(
                applicant_name="Jane Doe",
                applicant_email_address="jane@example.com",
                applicant_phone_number="+27 82 123 4567",
            )
        )
        self.assertTrue(all(checks.values()))

    def test_thin_application_fails_all_checks(self):
        checks = _get_kyc_quality_checks(_make_app())
        self.assertFalse(any(checks.values()))

    def test_malformed_email_and_phone_fail(self):
        checks = _get_kyc_quality_checks(
            _make_app(
                applicant_name="Jane Doe",
                applicant_email_address="not-an-email",
                applicant_phone_number="12",
            )
        )
        self.assertTrue(checks["applicant_name_present"])
        self.assertFalse(checks["email_well_formed"])
        self.assertFalse(checks["phone_well_formed"])


class TestScoringConfigLoading(FrappeTestCase):
    @patch("rcore.polaris.rlending.api.decision.frappe.get_all")
    @patch("rcore.polaris.rlending.api.decision.frappe.db.exists")
    def test_unseeded_site_yields_no_floor_and_doc_weights(self, mock_exists, mock_get_all):
        mock_exists.return_value = False
        config = _load_scoring_config()
        # No invented affordability floor or first-loan cap: the scorecard
        # will return Pending, never a fabricated pass.
        self.assertIsNone(config["min_disposable_income"])
        self.assertIsNone(config["first_loan_max_amount"])
        self.assertEqual(sum(config["weights"].values()), 100.0)
        self.assertEqual(config["weights"]["repayment_history_score"], 45.0)
        mock_get_all.assert_not_called()

    @patch("rcore.polaris.rlending.api.decision.frappe.get_all")
    @patch("rcore.polaris.rlending.api.decision.frappe.db.exists")
    def test_enabled_disposable_income_rule_supplies_the_floor(self, mock_exists, mock_get_all):
        mock_exists.side_effect = lambda doctype, name=None: name == "Scoring Rule"

        rule = MagicMock()
        rule.metric_name = "disposable_income"
        rule.threshold = 2500
        rule.weight = 0
        rule.is_knockout = 1
        mock_get_all.return_value = [rule]

        config = _load_scoring_config()
        self.assertEqual(config["min_disposable_income"], 2500.0)

    @patch("rcore.polaris.rlending.api.decision.frappe.get_all")
    @patch("rcore.polaris.rlending.api.decision.frappe.db.exists")
    def test_disabled_config_rows_stay_unset(self, mock_exists, mock_get_all):
        # load_rules-style filter is enabled=1, so disabled seed rows never
        # appear here; absent rows must stay None.
        mock_exists.side_effect = lambda doctype, name=None: name == "Scoring Rule"
        mock_get_all.return_value = []
        config = _load_scoring_config()
        self.assertIsNone(config["min_disposable_income"])
        self.assertIsNone(config["first_loan_max_amount"])


class TestLoanHistoryAnalyzer(FrappeTestCase):
    @patch(
        "rcore.polaris.rlending.decision_engine.analyzers.loan_history_analyzer.frappe"
    )
    def test_missing_loan_doctype_fail_honests_to_unavailable(self, mock_frappe):
        mock_frappe.db.exists.return_value = False
        metrics = LoanHistoryAnalyzer("CUST-1").analyze()
        self.assertIsNone(metrics["has_active_loan"])
        self.assertIsNone(metrics["loan_history"])
        self.assertIsNone(metrics["repayment_history_score"])

    @patch(
        "rcore.polaris.rlending.decision_engine.analyzers.loan_history_analyzer.frappe"
    )
    def test_no_loans_is_a_clean_cold_start(self, mock_frappe):
        mock_frappe.db.exists.return_value = True
        mock_frappe.get_all.return_value = []
        metrics = LoanHistoryAnalyzer("CUST-1").analyze()
        self.assertEqual(metrics["has_active_loan"], 0)
        self.assertEqual(metrics["loan_history"], [])
        self.assertIsNone(metrics["repayment_history_score"])

    @patch(
        "rcore.polaris.rlending.decision_engine.analyzers.loan_history_analyzer.frappe"
    )
    def test_open_loan_sets_active_flag(self, mock_frappe):
        mock_frappe.db.exists.return_value = True

        def get_all(doctype, **kwargs):
            if doctype == "Loan":
                return [{"name": "L1", "status": "Disbursed"}]
            return []

        mock_frappe.get_all.side_effect = get_all
        metrics = LoanHistoryAnalyzer("CUST-1").analyze()
        self.assertEqual(metrics["has_active_loan"], 1)
        # Open loans are not history — the gate handles them.
        self.assertEqual(metrics["loan_history"], [])


class TestGetCreditScoreEndpoint(FrappeTestCase):
    @patch("rcore.polaris.rlending.api.decision._load_scoring_config")
    @patch("rcore.polaris.rlending.api.decision.PaasOrderAnalyzer")
    @patch("rcore.polaris.rlending.api.decision.LoanHistoryAnalyzer")
    @patch("rcore.polaris.rlending.api.decision._get_kyc_complete")
    @patch("rcore.polaris.rlending.api.decision.frappe")
    def test_unseeded_config_returns_explicit_pending_not_a_score(
        self, mock_frappe, mock_kyc, mock_history, mock_paas, mock_config
    ):
        from rcore.polaris.rlending.api.decision import get_credit_score

        app = _make_app(
            monthly_income=10000,
            monthly_expenses=4000,
            repayment_amount=1500,
            loan_amount=5000,
        )
        app.name = "LA-0001"
        app.loan_product = "LP-1"
        mock_frappe.get_doc.return_value = app
        mock_frappe.db.get_value.return_value = 10000
        mock_frappe.form_dict.get.return_value = "trace"
        mock_kyc.return_value = 1
        mock_history.return_value.analyze.return_value = {
            "has_active_loan": 0,
            "loan_history": [],
            "repayment_history_score": None,
        }
        mock_paas.return_value.analyze.return_value = {"total_transactions": 0}
        mock_config.return_value = {
            "min_disposable_income": None,
            "first_loan_max_amount": None,
        }

        result = get_credit_score("LA-0001")
        self.assertEqual(result["decision"], "Pending")
        self.assertIsNone(result["score"])
        self.assertIn(
            "min_disposable_income_not_configured",
            [r["code"] for r in result["reasons"]],
        )
        self.assertEqual(result["alternative_data"], {"total_transactions": 0})
