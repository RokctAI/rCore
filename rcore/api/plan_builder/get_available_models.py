# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe


@frappe.whitelist(allow_guest=True)
def get_available_models():
    """
    Returns available AI models configured on the backend (Single Source of Truth)
    """
    models_file = os.path.join(os.path.dirname(__file__), "models.json")
    if os.path.exists(models_file):
        try:
            with open(models_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            frappe.log_error(
                f"Failed to read models.json: {str(e)}", "AI Models Configuration"
            )
    return {}
