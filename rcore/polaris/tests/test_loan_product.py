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

from rcore.polaris.rlending.api.product import get_loan_product_list


class TestLoanProduct(FrappeTestCase):
    @patch("rcore.polaris.rlending.api.product.frappe.get_all")
    @patch("rcore.polaris.rlending.api.product.frappe.form_dict", {})
    def test_get_loan_product_list_flattens_charges(self, mock_get_all):
        product_row = MagicMock()
        product_row.name = "PROD-1"
        product_row.product_name = "Personal Loan"
        product_row.rate_of_interest = 24.5
        product_row.currency = "ZAR"
        product_row.is_term_loan = 1
        product_row.maximum_loan_amount = 50000
        product_row.min_days_bw_disbursement_first_repayment = 7

        initiation_charge = MagicMock()
        initiation_charge.charge_type = "Initiation Fee"
        initiation_charge.amount = 1207.5
        initiation_charge.percentage = 0

        service_charge = MagicMock()
        service_charge.charge_type = "Monthly Service Fee"
        service_charge.amount = 69
        service_charge.percentage = 0

        def get_all_side_effect(doctype, **kwargs):
            if doctype == "Loan Product":
                return [product_row]
            if doctype == "Loan Charges":
                return [initiation_charge, service_charge]
            return []

        mock_get_all.side_effect = get_all_side_effect

        result = get_loan_product_list()

        self.assertEqual(len(result), 1)
        product = result[0]
        # Forked doctype now carries a real `currency` field (upstream Lending's
        # Loan Product never had one, so this key was previously unpopulated).
        self.assertEqual(product["currency"], "ZAR")
        self.assertEqual(product["initiation_fee"], 1207.5)
        self.assertEqual(product["monthly_service_fee"], 69)
        self.assertEqual(len(product["charges"]), 2)
