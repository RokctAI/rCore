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
Requires a real site with a secured Loan Product (is_secured=1) configured -
run post-compose against a live bench. See
corporate/polaris/docs/secured-lending-report.md for the full mocked-
controller equivalent that was actually executed during development (no
live Frappe site available in this source repo).
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from rcore.polaris.rlending.api.loan import disburse_loan
from rcore.polaris.rlending.asset_realisation import realise_pawn_asset, release_security


class TestSecuredLending(FrappeTestCase):
    def setUp(self):
        if not frappe.db.exists("Loan Product", "TEST-SECURED-PROD"):
            frappe.get_doc(
                {
                    "doctype": "Loan Product",
                    "product_code": "TEST-SECURED-PROD",
                    "product_name": "Test Secured Product",
                    "rate_of_interest": 24,
                    "currency": "ZAR",
                    "is_secured": 1,
                }
            ).insert(ignore_permissions=True)

    def _make_application(self, description="Test aircon unit, serial ABC123"):
        app = frappe.get_doc(
            {
                "doctype": "Loan Application",
                "applicant_type": "Customer",
                "applicant": frappe.db.get_value("Customer", {}, "name"),
                "company": frappe.defaults.get_global_default("company"),
                "loan_product": "TEST-SECURED-PROD",
                "loan_amount": 3000,
                "description": description,
            }
        )
        app.insert(ignore_permissions=True)
        self.assertEqual(app.is_secured_loan, 1)
        app.status = "Approved"
        app.save(ignore_permissions=True)
        return app

    def test_secured_application_requires_description(self):
        app = frappe.get_doc(
            {
                "doctype": "Loan Application",
                "applicant_type": "Customer",
                "applicant": frappe.db.get_value("Customer", {}, "name"),
                "company": frappe.defaults.get_global_default("company"),
                "loan_product": "TEST-SECURED-PROD",
                "loan_amount": 3000,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            app.insert(ignore_permissions=True)

    def test_disbursement_creates_pledged_asset(self):
        app = self._make_application()
        disburse_loan(app.name)

        loan_name = frappe.db.get_value("Loan", {"loan_application": app.name}, "name")
        asset_name = frappe.db.get_value("Pledged Asset", {"loan": loan_name}, "name")
        self.assertTrue(asset_name)
        asset = frappe.get_doc("Pledged Asset", asset_name)
        self.assertEqual(asset.status, "Pledged")
        self.assertEqual(asset.description, app.description)

    def test_repossess_and_release_are_mutually_exclusive(self):
        app = self._make_application()
        disburse_loan(app.name)
        loan_name = frappe.db.get_value("Loan", {"loan_application": app.name}, "name")

        with self.assertRaises(frappe.ValidationError):
            release_security(loan_name)  # not paid off yet

        realise_pawn_asset(loan_name, "Repossessed Inventory")

        asset_name = frappe.db.get_value("Pledged Asset", {"loan": loan_name}, "name")
        asset = frappe.get_doc("Pledged Asset", asset_name)
        self.assertEqual(asset.status, "Repossessed")

        with self.assertRaises(frappe.ValidationError):
            release_security(loan_name)  # already repossessed
