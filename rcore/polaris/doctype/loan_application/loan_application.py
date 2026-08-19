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

import math

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, rounded


def get_monthly_repayment_amount(loan_amount, rate_of_interest, repayment_periods):
    """
    Standard monthly-amortizing EMI formula. Ported verbatim from Frappe Lending's
    `loan_repayment_schedule/utils.py:get_monthly_repayment_amount`, trimmed to the
    "Monthly" frequency case since that's the only one `rlending` ever used.
    """
    if rate_of_interest:
        monthly_interest_rate = flt(rate_of_interest) / (12 * 100)
        return math.ceil(
            (loan_amount * monthly_interest_rate * (1 + monthly_interest_rate) ** repayment_periods)
            / ((1 + monthly_interest_rate) ** repayment_periods - 1)
        )
    return math.ceil(flt(loan_amount) / repayment_periods)


class LoanApplication(Document):
    """
    Polaris's own Loan Application doctype - forked from Frappe Lending's
    `Loan Application` (see corporate/polaris/docs/fork-lending-full-backend-plan.md, Phase 2).

    Folds in what used to be a separate override layer
    (overrides/loan_application.py, now removed) directly, since there is no more
    vendor base class to override:
    - KYC validation (Lead check)
    - Ringfencing rules (mobile app logic)
    - Auto-disburse on approval

    Deliberately NOT ported from upstream: Employee-branch validation,
    sanctioned-amount-limit aggregation, and the before_save() auto-Customer/
    Contact/Address creation flow - none of these are exercised anywhere in
    rlending's or RokctAI_frontend's actual usage today.

    Secured-loan collateral capture (is_secured_loan/description/
    declared_asset_value) WAS added later (secured-lending-brief.md) once
    real evidence surfaced that the live application form
    (RokctAI_frontend/app/handson/all/lending/application/new/page.tsx)
    already captures it - this is Polaris's own single-asset repossession
    model, not a port of upstream's multi-asset pledge/LTV system.
    """

    def validate(self):
        self.validate_loan_amount()
        if self.is_term_loan:
            self.validate_repayment_method()
            self.get_repayment_details()
        self.validate_loan_product()
        self.validate_secured_loan()
        self.set_ringfencing_rules()
        self.validate_kyc()

    def on_update(self):
        if self.status == "Approved" and self.get_db_value("status") != "Approved":
            # Auto-disburse on approval
            from importlib import import_module

            # Doctype trees compose verbatim; derive the "<app>.polaris" root from __name__.
            disburse_loan = import_module(
                __name__.split(".doctype.")[0] + ".rlending.api.loan"
            ).disburse_loan

            disburse_loan(self.name)

    def validate_loan_amount(self):
        if not self.loan_amount:
            frappe.throw(_("Loan Amount is mandatory"))

        maximum_loan_limit = frappe.db.get_value(
            "Loan Product", self.loan_product, "maximum_loan_amount"
        )
        if maximum_loan_limit and self.loan_amount > maximum_loan_limit:
            frappe.throw(
                _("Loan Amount cannot exceed Maximum Loan Amount of {0}").format(maximum_loan_limit)
            )

    def validate_loan_product(self):
        product_company = frappe.get_value("Loan Product", self.loan_product, "company")
        if product_company and product_company != self.company:
            frappe.throw(
                _("Please select a Loan Product for company {0}").format(frappe.bold(self.company))
            )
        if not self.rate_of_interest:
            self.rate_of_interest = frappe.db.get_value(
                "Loan Product", self.loan_product, "rate_of_interest"
            )
        if not self.is_secured_loan:
            # The real frontend (application/new/page.tsx) derives its `isSecured` UI
            # flag from Loan Product.is_secured and never actually includes
            # is_secured_loan in the submitted payload - so this is inferred here,
            # not just defaulted, otherwise every application from the live form
            # would silently save as unsecured regardless of the product chosen.
            self.is_secured_loan = frappe.db.get_value(
                "Loan Product", self.loan_product, "is_secured"
            )

    def validate_secured_loan(self):
        if self.is_secured_loan and not self.description:
            frappe.throw(_("Collateral description is mandatory for secured loans"))

    def validate_repayment_method(self):
        if self.repayment_method == "Repay Over Number of Periods" and not self.repayment_periods:
            frappe.throw(_("Please enter Repayment Periods"))

        if self.repayment_method == "Repay Fixed Amount per Period":
            if not self.repayment_amount:
                frappe.throw(_("Please enter Repayment Amount"))
            if self.repayment_amount > self.loan_amount:
                frappe.throw(_("Monthly Repayment Amount cannot be greater than Loan Amount"))

    def get_repayment_details(self):
        """Ported from upstream LoanApplication.get_repayment_details/calculate_payable_amount."""
        if self.repayment_method == "Repay Over Number of Periods":
            self.repayment_amount = get_monthly_repayment_amount(
                self.loan_amount, self.rate_of_interest, self.repayment_periods
            )

        if self.repayment_method == "Repay Fixed Amount per Period":
            monthly_interest_rate = flt(self.rate_of_interest) / (12 * 100)
            if monthly_interest_rate:
                min_repayment_amount = self.loan_amount * monthly_interest_rate
                if self.repayment_amount - min_repayment_amount <= 0:
                    frappe.throw(
                        _("Repayment Amount must be greater than {0}").format(
                            flt(min_repayment_amount, 2)
                        )
                    )
                self.repayment_periods = math.ceil(
                    (math.log(self.repayment_amount) - math.log(self.repayment_amount - min_repayment_amount))
                    / (math.log(1 + monthly_interest_rate))
                )
            else:
                self.repayment_periods = self.loan_amount / self.repayment_amount

        self.calculate_payable_amount()

    def calculate_payable_amount(self):
        balance_amount = self.loan_amount
        self.total_payable_amount = 0
        self.total_payable_interest = 0

        while balance_amount > 0:
            interest_amount = rounded(balance_amount * flt(self.rate_of_interest) / (12 * 100))
            balance_amount = rounded(balance_amount + interest_amount - self.repayment_amount)
            self.total_payable_interest += interest_amount

        self.total_payable_amount = self.loan_amount + self.total_payable_interest

    def set_ringfencing_rules(self):
        """
        Rules:
        - If is_from_mobile and skip_documents, it is automatically Ring-Fenced and NOT Withdrawable.
        - This ensures manual entries or documented mobile applications can still be withdrawable.
        """
        if self.get("is_from_mobile") and self.get("skip_documents"):
            self.is_ring_fenced = 1
            self.is_withdrawable = 0
        else:
            if not self.get("is_ring_fenced"):
                self.is_withdrawable = 1
                self.is_ring_fenced = 0
            else:
                self.is_withdrawable = 0

    def validate_kyc(self):
        """
        Withdrawable loans REQUIRE a Verified KYC Status.
        """
        if not self.get("is_withdrawable"):
            return

        if self.applicant_type == "Customer":
            customer_email = frappe.db.get_value("Customer", self.applicant, "email_id")
            customer_mobile = frappe.db.get_value("Customer", self.applicant, "mobile_no")

            lead = None
            if customer_email:
                lead = frappe.db.get_value("Lead", {"email_id": customer_email}, "name")
            if not lead and customer_mobile:
                lead = frappe.db.get_value("Lead", {"mobile_no": customer_mobile}, "name")

            if lead:
                kyc_status = frappe.db.get_value("Lead", lead, "kyc_status")
                if kyc_status != "Verified":
                    frappe.throw(
                        _(
                            "KYC Verification is required for withdrawable loans. Current status: {0}"
                        ).format(kyc_status)
                    )
