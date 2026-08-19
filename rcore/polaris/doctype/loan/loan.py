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
from frappe import _
from frappe.model.document import Document


class Loan(Document):
    """
    Polaris's own Loan doctype - forked from Frappe Lending's `Loan`
    (see corporate/polaris/docs/fork-lending-full-backend-plan.md, Phase 3).

    Per the Phase 0 GL decision, this is a plain Document - it does NOT inherit
    ERPNext's AccountsController and does not post GL entries. Running balances
    (disbursed_amount, total_principal_paid, etc.) are maintained directly by
    Loan Disbursement / Loan Repayment / Loan Write Off's on_submit hooks as a
    self-contained sub-ledger.

    Deliberately NOT ported from upstream: co-lending (loan_partner), NPA/IRAC
    classification fields (is_npa, classification_code - Phase 5), limit
    management, restructure tracking, moratorium handling (Phase 4) - none are
    exercised anywhere in rlending's or RokctAI_frontend's actual usage today.
    """

    def validate(self):
        self.validate_loan_amount()
        self.validate_loan_product()

    def validate_loan_amount(self):
        if not self.loan_amount:
            frappe.throw(_("Loan Amount is mandatory"))

    def validate_loan_product(self):
        product_company = frappe.db.get_value("Loan Product", self.loan_product, "company")
        if product_company and product_company != self.company:
            frappe.throw(
                _("Loan Product {0} does not belong to company {1}").format(
                    frappe.bold(self.loan_product), frappe.bold(self.company)
                )
            )
        if not self.rate_of_interest:
            self.rate_of_interest = frappe.db.get_value(
                "Loan Product", self.loan_product, "rate_of_interest"
            )
