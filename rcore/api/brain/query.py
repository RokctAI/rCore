# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def query(doctype, name):
    """
    A secure API endpoint for an AI model to query the Brain's memory.
    Ensures security is enforced by checking for read permission.
    """
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(
            f"You do not have permission to access the memory of {doctype} {name}",
            frappe.PermissionError,
        )

    try:
        engram_name = f"{doctype}-{name}"
        engram_doc = frappe.get_doc("Engram", engram_name)
        response_data = engram_doc.as_dict()
        response_data["brain_version"] = brain_version
        return response_data
    except frappe.DoesNotExistError:
        frappe.throw(f"No Engram found for {doctype} {name}", frappe.NotFound)
    except Exception as e:
        frappe.throw(f"An error occurred while querying the Brain: {e}")
