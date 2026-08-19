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

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from rcore.polaris.doctype.loan_application.loan_application import (
    LoanApplication,
    get_monthly_repayment_amount,
)


class TestLoanApplicationMath(FrappeTestCase):
    def test_emi_matches_standard_annuity_formula(self):
        # 10,000 @ 24% p.a., 12 monthly periods -> known-good EMI of 946
        # (cross-checked independently against the standard amortization formula).
        self.assertEqual(get_monthly_repayment_amount(10000, 24, 12), 946)

    def test_zero_rate_falls_back_to_flat_division(self):
        self.assertEqual(get_monthly_repayment_amount(1200, 0, 12), 100)


class TestLoanApplicationRingfencing(FrappeTestCase):
    def _make_app(self, **fields):
        app = LoanApplication.__new__(LoanApplication)
        app.__dict__.update(fields)
        return app

    def test_mobile_skip_documents_is_ring_fenced_and_not_withdrawable(self):
        app = self._make_app(is_from_mobile=1, skip_documents=1, is_ring_fenced=0, is_withdrawable=0)
        app.set_ringfencing_rules()
        self.assertEqual(app.is_ring_fenced, 1)
        self.assertEqual(app.is_withdrawable, 0)

    def test_normal_application_is_withdrawable(self):
        app = self._make_app(is_from_mobile=0, skip_documents=0, is_ring_fenced=0, is_withdrawable=0)
        app.set_ringfencing_rules()
        self.assertEqual(app.is_ring_fenced, 0)
        self.assertEqual(app.is_withdrawable, 1)

    def test_explicitly_ring_fenced_is_not_withdrawable(self):
        app = self._make_app(is_from_mobile=0, skip_documents=0, is_ring_fenced=1, is_withdrawable=1)
        app.set_ringfencing_rules()
        self.assertEqual(app.is_withdrawable, 0)


class TestLoanApplicationKyc(FrappeTestCase):
    def _make_app(self, **fields):
        app = LoanApplication.__new__(LoanApplication)
        app.__dict__.update(fields)
        return app

    def test_non_withdrawable_skips_kyc_check(self):
        app = self._make_app(is_withdrawable=0, applicant_type="Customer", applicant="CUST-1")
        # Should return without touching frappe.db at all.
        app.validate_kyc()

    @patch("rcore.polaris.doctype.loan_application.loan_application.frappe.db.get_value")
    @patch("rcore.polaris.doctype.loan_application.loan_application.frappe.throw")
    def test_withdrawable_without_verified_kyc_throws(self, mock_throw, mock_get_value):
        mock_throw.side_effect = Exception("blocked")

        def get_value_side_effect(doctype, filters, *args, **kwargs):
            if doctype == "Customer" and filters == "CUST-1":
                return "cust@example.com"
            if doctype == "Lead" and filters == {"email_id": "cust@example.com"}:
                return "LEAD-1"
            if doctype == "Lead" and filters == "LEAD-1":
                return "Pending"
            return None

        mock_get_value.side_effect = get_value_side_effect

        app = self._make_app(is_withdrawable=1, applicant_type="Customer", applicant="CUST-1")
        with self.assertRaises(Exception):
            app.validate_kyc()
        mock_throw.assert_called_once()
