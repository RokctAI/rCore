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

from frappe.tests.utils import FrappeTestCase

from rcore.polaris.doctype.loan.loan import Loan
from rcore.polaris.doctype.loan_balance_adjustment.loan_balance_adjustment import (
    LoanBalanceAdjustment,
)
from rcore.polaris.doctype.loan_repayment.loan_repayment import get_pending_principal_amount
from rcore.polaris.doctype.loan_restructure.loan_restructure import LoanRestructure
from rcore.polaris.doctype.loan_transfer.loan_transfer import LoanTransfer

import frappe


class TestLoanPhase4(FrappeTestCase):
    """
    Requires a real site with a disbursed test Loan fixture - run post-compose
    against a live bench. See test_phase4_lifecycle.py (development-time,
    mocked, actually executed) for the equivalent that was run without a live
    Frappe site available in this source repo.
    """

    def test_balance_adjustment_updates_outstanding_amount(self):
        loan = frappe.get_doc("Loan", {"status": "Disbursed"}, "name")
        before = get_pending_principal_amount(loan)

        adj = frappe.get_doc(
            {
                "doctype": "Loan Balance Adjustment",
                "loan": loan.name,
                "adjustment_type": "Credit Adjustment",
                "amount": 100,
            }
        )
        adj.insert(ignore_permissions=True)
        adj.submit()

        loan.reload()
        self.assertEqual(loan.outstanding_amount, before - 100)

    def test_restructure_only_applies_terms_when_approved(self):
        loan = frappe.get_doc("Loan", {"status": "Disbursed"}, "name")
        original_rate = loan.rate_of_interest

        draft_restructure = frappe.get_doc(
            {
                "doctype": "Loan Restructure",
                "loan": loan.name,
                "status": "Initiated",
                "new_rate_of_interest": 5,
            }
        )
        draft_restructure.insert(ignore_permissions=True)
        draft_restructure.submit()
        loan.reload()
        self.assertEqual(loan.rate_of_interest, original_rate)

        approved_restructure = frappe.get_doc(
            {
                "doctype": "Loan Restructure",
                "loan": loan.name,
                "status": "Approved",
                "new_rate_of_interest": 5,
            }
        )
        approved_restructure.insert(ignore_permissions=True)
        approved_restructure.submit()
        loan.reload()
        self.assertEqual(loan.rate_of_interest, 5)
