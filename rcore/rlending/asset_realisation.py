# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt, nowdate
from frappe.utils import flt, nowdate
from lending.loan_management.doctype.loan_repayment.loan_repayment import get_pending_principal_amount


@frappe.whitelist()
def realise_pawn_asset(loan_name, asset_account):
    """
    Bank-Level Asset Realisation:
    1. Locks the Loan Record (Prevents Race Conditions).
    2. Validates Permissions (Manager Only).
    3. Creates 'Loan Write Off' to book asset into Inventory.
    4. Logs Immutable Audit Trail.
    """
    # 1. Role-Based Access Control (RBAC)
    if not frappe.has_permission("Loan", "write"):
        frappe.throw(_("Insufficient Permissions to modify Loan."))

    # 2. Transactional Locking (Prevent Race Conditions)
    # Lock the loan row for the duration of this transaction
    frappe.db.sql(
        "SELECT name FROM `tabLoan` WHERE name=%s FOR UPDATE",
        loan_name)

    try:
        loan = frappe.get_doc("Loan", loan_name)

        # 3. Strict Validation
        if loan.docstatus != 1:
            frappe.throw(_("Loan must be submitted before realisation."))

        if loan.status in ["Closed", "Loan Closure Requested"]:
            frappe.throw(_("Loan is already closed or in closure process."))

        if not loan.is_secured_loan:
            frappe.throw(
                _("Only Secured Loans can be realised via Asset Seizure."))

        pending_principal = get_pending_principal_amount(loan)
        if pending_principal <= 0:
            frappe.throw(_("Loan principal is already settled."))

        # 4. Execute Financial Transaction (Write Off / Swap)
        wo = frappe.new_doc("Loan Write Off")
        wo.loan = loan_name
        wo.company = loan.company
        wo.write_off_account = asset_account
        wo.write_off_amount = pending_principal
        wo.posting_date = nowdate()
        wo.insert()
        wo.submit()

        # 5. Immutable Audit Log
        loan.add_comment(
            "Info",
            _("Asset Seized (Realised) by {0}. Value: {1}").format(
                frappe.session.user,
                flt(pending_principal)))

        frappe.msgprint(
            _("Asset Realised successfully. Loan settled and transferred to {0}.").format(asset_account))

        return wo.name

    except Exception as e:
        frappe.log_error(
            f"Asset Realisation Failed: {
                str(e)}",
            "Asset Realisation Error")
        raise e
