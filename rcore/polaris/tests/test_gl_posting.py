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
Requires a real site with Loan Product GL accounts configured (loan_account,
interest_income_account, interest_accrued_account) and Company.default_bank_account
set - run post-compose against a live bench. See
corporate/polaris/docs/gl-posting-report.md for the full mocked-controller
equivalent that was actually executed during development (no live Frappe
site/ERPNext available in this source repo), including the full GL trail
produced as evidence.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from rcore.polaris.rlending import gl_posting


class TestGlPosting(FrappeTestCase):
    def setUp(self):
        if not frappe.db.exists("Loan Product", "TEST-GL-PROD"):
            frappe.get_doc(
                {
                    "doctype": "Loan Product",
                    "product_code": "TEST-GL-PROD",
                    "product_name": "Test GL Product",
                    "rate_of_interest": 24,
                    "currency": "ZAR",
                    "loan_account": frappe.db.get_value("Account", {"account_type": "Receivable"}, "name"),
                    "interest_income_account": frappe.db.get_value(
                        "Account", {"account_type": "Income Account"}, "name"
                    ),
                    "interest_accrued_account": frappe.db.get_value(
                        "Account", {"account_type": "Receivable"}, "name"
                    ),
                }
            ).insert(ignore_permissions=True)

    def test_disbursement_blocks_without_gl_accounts(self):
        product = frappe.get_doc(
            {
                "doctype": "Loan Product",
                "product_code": "TEST-NO-GL",
                "product_name": "No GL Config",
                "rate_of_interest": 24,
                "currency": "ZAR",
            }
        )
        product.insert(ignore_permissions=True)

        loan = frappe.get_doc(
            {
                "doctype": "Loan",
                "applicant_type": "Customer",
                "applicant": frappe.db.get_value("Customer", {}, "name"),
                "company": frappe.defaults.get_global_default("company"),
                "loan_product": product.name,
                "loan_amount": 1000,
                "status": "Approved",
            }
        )
        loan.insert(ignore_permissions=True)
        loan.submit()

        disb = frappe.get_doc(
            {
                "doctype": "Loan Disbursement",
                "against_loan": loan.name,
                "disbursed_amount": 1000,
                "disbursement_date": frappe.utils.nowdate(),
                "company": loan.company,
            }
        )
        disb.insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            disb.submit()

    def test_full_lifecycle_reconciles(self):
        loan = frappe.get_doc(
            {
                "doctype": "Loan",
                "applicant_type": "Customer",
                "applicant": frappe.db.get_value("Customer", {}, "name"),
                "company": frappe.defaults.get_global_default("company"),
                "loan_product": "TEST-GL-PROD",
                "loan_amount": 5000,
                "status": "Approved",
            }
        )
        loan.insert(ignore_permissions=True)
        loan.submit()

        disb = frappe.get_doc(
            {
                "doctype": "Loan Disbursement",
                "against_loan": loan.name,
                "disbursed_amount": 5000,
                "disbursement_date": frappe.utils.nowdate(),
                "company": loan.company,
            }
        )
        disb.insert(ignore_permissions=True)
        disb.submit()
        self.assertTrue(disb.journal_entry)

        repay = frappe.get_doc(
            {
                "doctype": "Loan Repayment",
                "against_loan": loan.name,
                "amount_paid": 5000,
            }
        )
        repay.insert(ignore_permissions=True)
        repay.submit()
        self.assertTrue(repay.journal_entry)

        result = gl_posting.reconcile_loan_gl_vs_wallet(loan.name)
        self.assertTrue(result["reconciled"], result)
