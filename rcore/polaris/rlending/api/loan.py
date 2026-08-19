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
from frappe.utils import flt, nowdate

from rcore.polaris.doctype.pledged_asset.pledged_asset import create_from_application


@frappe.whitelist()
def disburse_loan(loan_application: str) -> str:
    """
    Creates a Loan Disbursement for an approved Loan Application.
    This is triggered by the 'Withdraw' button in the Mobile App.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "disburse-loan-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] disburse_loan called for {loan_application}\n")
    if not loan_application:
        frappe.throw("Loan Application is required")

    app_doc = frappe.get_doc("Loan Application", loan_application)

    if app_doc.status != "Approved":
        frappe.throw(
            f"Loan Application status must be Approved. Current status: {
                app_doc.status
            }"
        )

    # Standard Lending App Flow
    loan_name = frappe.db.get_value("Loan", {"loan_application": app_doc.name}, "name")

    # Check if already disbursed. Was previously compared against_loan to
    # app_doc.name (the Loan Application's name) - but against_loan is always
    # a Loan name, so that check could never match anything and this guard
    # was silently dead: calling disburse_loan() twice on the same approved
    # application would create a second Loan Disbursement and double-credit
    # the wallet. Fixed to compare against the actual Loan name, resolved
    # above (found while adding secured-lending's Pledged Asset creation to
    # this same function - see secured-lending-report.md).
    if loan_name and frappe.db.exists(
        "Loan Disbursement", {"against_loan": loan_name, "docstatus": 1}
    ):
        frappe.throw("Loan has already been disbursed.")

    if not loan_name:
        loan_doc = frappe.get_doc(
            {
                "doctype": "Loan",
                "loan_application": app_doc.name,
                "applicant_type": app_doc.applicant_type,
                "applicant": app_doc.applicant,
                "loan_product": app_doc.loan_product,
                "loan_amount": app_doc.loan_amount,
                "company": app_doc.company,
                "posting_date": nowdate(),
                "status": "Approved",
                "is_secured_loan": app_doc.get("is_secured_loan"),
            }
        )
        loan_doc.insert(ignore_permissions=True)
        loan_doc.submit()
        loan_name = loan_doc.name

        if loan_doc.is_secured_loan:
            create_from_application(loan_name, app_doc.name)

    # Create the Disbursment entry
    disb_doc = frappe.get_doc(
        {
            "doctype": "Loan Disbursement",
            "against_loan": loan_name,
            "disbursement_date": nowdate(),
            "disbursed_amount": app_doc.loan_amount,
            "company": app_doc.company,
            "posting_date": nowdate(),
        }
    )

    disb_doc.insert(ignore_permissions=True)
    disb_doc.submit()

    # Update state
    app_doc.status = "Disbursed"
    app_doc.save(ignore_permissions=True)

    return disb_doc.name
