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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, nowdate

from rcore.polaris.rlending.decision_engine.scorecard import (
    build_loan_history_records,
    score_repayment_history,
)

# tenant context check.

#: Loan statuses that mean the applicant currently has an open exposure.
#: Everything that is not terminally settled counts as active — conservative:
#: an in-flight application/loan blocks a new one (doc gate 2). Terminal
#: statuses: Closed / Settled (repaid) and Written Off (defaulted — no longer
#: active, but it devastates the repayment-history component instead).
ACTIVE_LOAN_STATUSES = (
    "Draft",
    "Approved",
    "Sanctioned",
    "Partially Disbursed",
    "Disbursed",
    "Active",
    "Loan Closure Requested",
)


class LoanHistoryAnalyzer:
    """
    A service to analyze an applicant's own past `Loan` / `Loan Repayment`
    records and compute the repayment-history metrics for the credit scorecard
    (design doc: polaris/docs/credit-risk-algorithm.md, component 1 + gate 2).

    Parallel in shape to `PaasOrderAnalyzer`; all the actual scoring math is
    pure and lives in `decision_engine/scorecard.py`.
    """

    def __init__(self, applicant):
        self.applicant = applicant
        self.loans = []
        self.repayments = []
        self.metrics = {}
        self.history_available = False

    def analyze(self):
        """
        Main method to trigger the analysis process.
        """
        self._fetch_loan_history()
        self._calculate_metrics()
        return self.metrics

    def _fetch_loan_history(self):
        if not frappe.db.exists("DocType", "Loan"):
            # Cannot distinguish "no history" from "cannot query" — leave
            # history_available False so the scorecard fail-honests to Pending
            # instead of treating this as a clean cold start.
            return
        self.history_available = True

        self.loans = frappe.get_all(
            "Loan",
            filters={"applicant": self.applicant},
            fields=[
                "name",
                "status",
                "disbursement_date",
                "closure_date",
                "repayment_periods",
                "posting_date",
            ],
        )

        loan_names = [loan.get("name") for loan in self.loans]
        if loan_names and frappe.db.exists("DocType", "Loan Repayment"):
            self.repayments = frappe.get_all(
                "Loan Repayment",
                filters={"against_loan": ["in", loan_names], "docstatus": 1},
                fields=["against_loan", "posting_date"],
            )

    def _calculate_metrics(self):
        if not self.history_available:
            self.metrics = {
                "has_active_loan": None,
                "active_loan_count": None,
                "completed_loan_count": None,
                "repayment_history_score": None,
                "loan_history": None,
            }
            return

        active_loans = [
            loan for loan in self.loans if loan.get("status") in ACTIVE_LOAN_STATUSES
        ]

        as_of = getdate(nowdate())
        history_records = build_loan_history_records(
            self.loans, self.repayments, as_of
        )

        self.metrics = {
            "has_active_loan": 1 if active_loans else 0,
            "active_loan_count": len(active_loans),
            "completed_loan_count": len(history_records),
            # None (not 0) when there is no history at all: the cold-start
            # signal the scorecard needs — the doc forbids conflating "no
            # history" with "scored zero".
            "repayment_history_score": score_repayment_history(history_records),
            "loan_history": history_records,
        }
