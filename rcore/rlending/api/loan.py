import frappe
from frappe.utils import flt, nowdate

@frappe.whitelist()
def disburse_loan(loan_application):
    """
    Creates a Loan Disbursement for an approved Loan Application.
    This is triggered by the 'Withdraw' button in the Mobile App.
    """
    if not loan_application:
        frappe.throw("Loan Application is required")
        
    app_doc = frappe.get_doc("Loan Application", loan_application)
    
    if app_doc.status != "Approved":
        frappe.throw(f"Loan Application status must be Approved. Current status: {app_doc.status}")
        
    # Check if already disbursed
    if frappe.db.exists("Loan Disbursement", {"against_loan": app_doc.name, "docstatus": 1}):
        frappe.throw("Loan has already been disbursed.")

    # Standard Lending App Flow
    loan_name = frappe.db.get_value("Loan", {"loan_application": app_doc.name}, "name")
    
    if not loan_name:
        loan_doc = frappe.get_doc({
            "doctype": "Loan",
            "loan_application": app_doc.name,
            "applicant_type": app_doc.applicant_type,
            "applicant": app_doc.applicant,
            "loan_product": app_doc.loan_product,
            "loan_amount": app_doc.loan_amount,
            "company": app_doc.company,
            "posting_date": nowdate(),
            "status": "Approved"
        })
        loan_doc.insert(ignore_permissions=True)
        loan_doc.submit()
        loan_name = loan_doc.name
    
    # Create the Disbursment entry
    disb_doc = frappe.get_doc({
        "doctype": "Loan Disbursement",
        "against_loan": loan_name,
        "disbursement_date": nowdate(),
        "disbursed_amount": app_doc.loan_amount,
        "company": app_doc.company,
        "posting_date": nowdate()
    })
    
    disb_doc.insert(ignore_permissions=True)
    disb_doc.submit()
    
    # Update state
    app_doc.status = "Disbursed"
    app_doc.save(ignore_permissions=True)
    
    return disb_doc.name
