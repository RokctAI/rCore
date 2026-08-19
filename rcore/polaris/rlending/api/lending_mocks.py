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

from typing import Any, Optional
import frappe
import json


@frappe.whitelist()
def check_loan_eligibility(id_number: str, amount: float, lang: str='en') -> Any:
    """
    Checks if a user is eligible for a loan.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # This is a placeholder for the actual scorecard logic.
    is_eligible = True
    loan_eligibility_check = frappe.get_doc(
        {
            "doctype": "Loan Eligibility Check",
            "id_number": id_number,
            "amount": amount,
            "is_eligible": is_eligible,
        }
    )
    loan_eligibility_check.insert(ignore_permissions=True)
    return {"is_eligible": is_eligible}


@frappe.whitelist()
def check_loan_history_eligibility(lang: str='en') -> Any:
    """
    Checks if a user is eligible for a loan based on their loan history.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # This is a placeholder for the actual scorecard logic.
    return {"has_disqualifying_history": False}


@frappe.whitelist()
def mark_application_as_rejected(financial_details: dict, lang: str='en') -> Any:
    """
    Marks a loan application as rejected.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # This is a placeholder for the actual scorecard logic.
    return {"status": "success"}


@frappe.whitelist()
def check_financial_eligibility(monthly_income: float, grocery_expenses: float, other_expenses: float, existing_credits: float, lang: str='en') -> Any:
    """
    Checks if a user is financially eligible for a loan.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # This is a placeholder for the actual scorecard logic.
    return {"is_eligible": True}


@frappe.whitelist()
def save_incomplete_loan_application(financial_details: dict, lang: str='en') -> Any:
    """
    Saves an incomplete loan application as a draft.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    loan_application = frappe.get_doc(
        {
            "doctype": "Loan Application",
            "status": "Draft",
            # ... save other details from financial_details ...
        }
    )
    loan_application.insert(ignore_permissions=True)
    return {"name": loan_application.name}


@frappe.whitelist()
def fetch_saved_application(lang: str='en') -> Any:
    """
    Fetches a saved loan application.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    loan_application = frappe.get_list(
        "Loan Application",
        filters={"customer": user, "status": "Draft"},
        limit=1,
    )
    if loan_application:
        return frappe.get_doc("Loan Application", loan_application[0].name)
    return {}


@frappe.whitelist()
def fetch_saved_applications(lang: str='en') -> Any:
    """
    Fetches all saved loan applications for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    loan_applications = frappe.get_list(
        "Loan Application",
        filters={"customer": user, "status": "Draft"},
    )
    return loan_applications


@frappe.whitelist()
def create_loan_application(financial_details: dict, lang: str='en') -> Any:
    """
    Creates a new loan application.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    loan_application = frappe.get_doc(
        {
            "doctype": "Loan Application",
            "status": "Submitted",
            # Map fields
        }
    )
    loan_application.insert(ignore_permissions=True)
    return {"name": loan_application.name}


@frappe.whitelist()
def disburse_loan(loan_id: str, lang: str='en') -> Any:
    """
    Disburses a loan.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    return {"status": "success", "message": "Loan disbursed."}


@frappe.whitelist()
def get_my_loan_applications(lang: str='en') -> Any:
    """
    Fetches all loan applications for the user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    user = frappe.session.user
    return frappe.get_list("Loan Application", filters={"customer": user})
