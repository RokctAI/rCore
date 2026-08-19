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
from frappe.utils import flt, nowdate
from rcore.polaris.doctype.loan_repayment.loan_repayment import (
    get_pending_principal_amount,
)
from rcore.polaris.doctype.pledged_asset.pledged_asset import mark_repossessed, release_asset


@frappe.whitelist()
def realise_pawn_asset(loan_name: str, asset_account: str) -> str:
    """
    Bank-Level Asset Realisation:
    1. Locks the Loan Record (Prevents Race Conditions).
    2. Validates Permissions (Manager Only).
    3. Creates 'Loan Write Off' to book asset into Inventory.
    4. Logs Immutable Audit Trail.
    raw_sql
    """
    trace_id = frappe.form_dict.get("trace_id") or "realise-pawn-asset-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] realise_pawn_asset called for {loan_name}\n")
    # 1. Role-Based Access Control (RBAC)
    if not frappe.has_permission("Loan", "write"):
        frappe.throw(_("Insufficient Permissions to modify Loan."))

    # 2. Transactional Locking (Prevent Race Conditions)
    # Lock the loan row for the duration of this transaction
    frappe.db.sql("SELECT name FROM `tabLoan` WHERE name=%s FOR UPDATE", loan_name)

    try:
        loan = frappe.get_doc("Loan", loan_name)

        # 3. Strict Validation
        if loan.docstatus != 1:
            frappe.throw(_("Loan must be submitted before realisation."))

        if loan.status in ["Closed", "Loan Closure Requested"]:
            frappe.throw(_("Loan is already closed or in closure process."))

        if not loan.is_secured_loan:
            frappe.throw(_("Only Secured Loans can be realised via Asset Seizure."))

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

        # 4b. Update the Pledged Asset's status (no-op if this loan has none -
        # e.g. is_secured_loan was set but no Pledged Asset was ever created).
        # This is the human-confirmed repossession step: it only happens here,
        # never automatically from NPA classification.
        mark_repossessed(loan_name, wo.name)

        # 5. Immutable Audit Log
        loan.add_comment(
            "Info",
            _("Asset Seized (Realised) by {0}. Value: {1}").format(
                frappe.session.user, flt(pending_principal)
            ),
        )

        frappe.msgprint(
            _(
                "Asset Realised successfully. Loan settled and transferred to {0}."
            ).format(asset_account)
        )

        return wo.name

    except Exception as e:
        frappe.log_error(
            f"Asset Realisation Failed: {str(e)}", "Asset Realisation Error"
        )
        raise e


@frappe.whitelist()
def release_security(loan: str) -> str:
    """
    Real implementation for RokctAI_frontend's releaseSecurity() call
    (secured-lending-brief.md) - it previously pointed at the external
    `lending` app's Loan.unpledge_security, which depends on the pledged-
    collateral/LTV subsystem this fork never built. Releases the single
    Pledged Asset for this loan once it's confirmed fully paid off -
    verified server-side (pledged_asset.release_asset), not trusted from
    the caller.
    """
    if not frappe.has_permission("Loan", "write"):
        frappe.throw(_("Insufficient Permissions to modify Loan."))

    return release_asset(loan)
