# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe

# NOTE: We assume 'decision_engine' folder is in rcore.rlending
# from rcore.rlending.decision_engine.engine import ScoringEngine


@frappe.whitelist()
def get_credit_score(loan_application):
    """
    Calculates the credit score for a given Loan Application.
    Integrates standard application metrics and PaaS alternative data (if available).
    """
    if not loan_application:
        frappe.throw("Loan Application is required")

    app_doc = frappe.get_doc("Loan Application", loan_application)

    # Placeholder for logic migration.
    return {"score": 0, "decision": "Pending", "risk_level": "Unknown"}
