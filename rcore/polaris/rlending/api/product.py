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


@frappe.whitelist()
def get_loan_product_list() -> list:
    """
    Returns a list of Loan Products with their fees flattened or nested for the Frontend.
    Fixes mismatch between 'product_name' and 'loan_product_name'.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "get-loan-product-list-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] get_loan_product_list called\n")
    products = frappe.get_all(
        "Loan Product",
        fields=[
            "name",
            "product_name",
            "rate_of_interest",
            "currency",
            "is_term_loan",
            "is_secured",
            "maximum_loan_amount",
            "min_days_bw_disbursement_first_repayment",
        ],
    )

    result = []
    for p in products:
        # 1. Fetch Charges
        charges = frappe.get_all(
            "Loan Charges",
            filters={"parent": p.name},
            fields=["charge_type", "amount", "percentage"],
        )

        # 2. Try to identify standard fees
        initiation_fee = 0.0
        service_fee = 0.0

        # Heuristic: You might want to customize this logic if you use
        # different Item names
        for c in charges:
            c_name = c.charge_type.lower()
            if "initiation" in c_name:
                initiation_fee = c.amount
            elif "service" in c_name:
                service_fee = c.amount

        result.append(
            {
                "name": p.name,
                "loan_product_name": p.product_name,  # Frontend Compatibility
                "product_name": p.product_name,
                "rate_of_interest": p.rate_of_interest,
                "currency": p.currency,
                "is_term_loan": p.is_term_loan,
                "is_secured": p.is_secured,
                "maximum_loan_amount": p.maximum_loan_amount,
                "min_days_bw_disbursement_first_repayment": p.min_days_bw_disbursement_first_repayment,
                # Flattened Fees for easy access
                "initiation_fee": initiation_fee,
                "monthly_service_fee": service_fee,
                # Full charges array if needed
                "charges": charges,
            }
        )

    return result
