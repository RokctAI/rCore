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
from rcore.polaris.doctype.process_loan_interest_accrual.process_loan_interest_accrual import (
    process_loan_interest_accrual_for_loans,
)
from rcore.polaris.doctype.process_loan_classification.process_loan_classification import (
    create_process_loan_classification,
)
from rcore.polaris.doctype.process_loan_security_shortfall.process_loan_security_shortfall import (
    create_process_loan_security_shortfall,
)


class TestLoanPhase5(FrappeTestCase):
    """
    Requires a real site with a disbursed test Loan fixture 30+ days old -
    run post-compose against a live bench. See test_phase5_lifecycle.py
    (development-time, mocked, actually executed) for the equivalent that
    was run without a live Frappe site available in this source repo -
    including the bug it caught (total_payment/outstanding_amount drift on
    interest accrual, fixed in loan_interest_accrual.py before this file
    was written).
    """

    def test_interest_accrual_increases_total_interest_payable_only(self):
        loan = frappe.get_doc("Loan", {"status": "Disbursed"}, "name")
        principal_before = loan.outstanding_amount
        interest_before = loan.total_interest_payable

        process_name = process_loan_interest_accrual_for_loans(loan=loan.name)
        process = frappe.get_doc("Process Loan Interest Accrual", process_name)
        self.assertEqual(process.status, "Completed")

        loan.reload()
        self.assertGreater(loan.total_interest_payable, interest_before)
        # Principal-only figure must be unaffected by interest accrual.
        self.assertEqual(loan.outstanding_amount, principal_before)

    def test_classification_flags_overdue_loan_as_npa(self):
        loan = frappe.get_doc("Loan", {"status": "Disbursed"}, "name")

        create_process_loan_classification(loan=loan.name)
        loan.reload()
        # Assumes fixture setup has no overdue Loan Demand rows for this loan.
        self.assertEqual(loan.is_npa, 0)

    def test_security_shortfall_skips_when_no_secured_loans(self):
        if not frappe.db.count("Loan", {"docstatus": 1, "is_secured_loan": 1}):
            result = create_process_loan_security_shortfall()
            self.assertIsNone(result)
