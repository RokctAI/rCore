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

import frappe
from frappe.tests.utils import FrappeTestCase

from rcore.polaris.doctype.loan.loan import Loan
from rcore.polaris.doctype.loan_disbursement.loan_disbursement import LoanDisbursement
from rcore.polaris.doctype.loan_repayment.loan_repayment import (
    LoanRepayment,
    get_pending_principal_amount,
)
from rcore.polaris.doctype.loan_write_off.loan_write_off import LoanWriteOff


class TestLoanLifecycle(FrappeTestCase):
    """
    Full sub-ledger lifecycle: application -> disbursement -> repayments ->
    payoff, and separately -> write-off. Requires a real site (Loan Product
    fixture, Company, Customer) - run post-compose against a live bench.
    See corporate/polaris/docs/fork-lending-full-backend-plan.md Phase 3 for
    the plain-Python equivalent that was actually executed during development
    (no live Frappe site available in this source repo).
    """

    def setUp(self):
        if not frappe.db.exists("Loan Product", "TEST-PROD"):
            frappe.get_doc(
                {
                    "doctype": "Loan Product",
                    "product_code": "TEST-PROD",
                    "product_name": "Test Product",
                    "rate_of_interest": 24,
                    "currency": "ZAR",
                }
            ).insert(ignore_permissions=True)

    def test_disbursement_and_full_repayment_closes_loan(self):
        loan = frappe.get_doc(
            {
                "doctype": "Loan",
                "applicant_type": "Customer",
                "applicant": frappe.db.get_value("Customer", {}, "name") or "CUST-TEST",
                "company": frappe.defaults.get_global_default("company"),
                "loan_product": "TEST-PROD",
                "loan_amount": 10000,
                "status": "Approved",
            }
        )
        loan.insert(ignore_permissions=True)
        loan.submit()

        disb = frappe.get_doc(
            {
                "doctype": "Loan Disbursement",
                "against_loan": loan.name,
                "disbursed_amount": 10000,
                "disbursement_date": frappe.utils.nowdate(),
                "company": loan.company,
            }
        )
        disb.insert(ignore_permissions=True)
        disb.submit()

        loan.reload()
        self.assertEqual(loan.disbursed_amount, 10000)
        self.assertEqual(loan.status, "Disbursed")

        repay = frappe.get_doc(
            {
                "doctype": "Loan Repayment",
                "against_loan": loan.name,
                "amount_paid": 10000,
            }
        )
        repay.insert(ignore_permissions=True)
        repay.submit()

        loan.reload()
        self.assertEqual(loan.total_principal_paid, 10000)
        self.assertEqual(loan.status, "Closed")
        self.assertEqual(get_pending_principal_amount(loan), 0)
