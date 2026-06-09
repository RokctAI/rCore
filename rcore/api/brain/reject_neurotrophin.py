# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def reject_neurotrophin(neurotrophin_name: str) -> dict:
    """
    Dismisses a neurotrophin for the current user.
    """
    trace_id = frappe.form_dict.get("trace_id") or "reject-neurotrophin-trace"
    import sys

    sys.stderr.write(
        f"[Trace: {trace_id}] reject_neurotrophin called for {neurotrophin_name}\n"
    )
    neurotrophin = frappe.get_doc("Neurotrophin", neurotrophin_name)
    user = frappe.session.user

    if any(d.user == user for d in neurotrophin.get("dismissed_by", [])):
        return {
            "status": "success",
            "message": "Funding opportunity already dismissed.",
        }

    try:
        neurotrophin.append("dismissed_by", {"user": user})
        neurotrophin.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": "success",
            "message": f"Funding Opportunity {neurotrophin_name} dismissed.",
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed to dismiss neurotrophin {neurotrophin_name}",
        )
        frappe.throw(f"An error occurred while dismissing the funding opportunity: {e}")
