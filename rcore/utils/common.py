import frappe


def is_ai_action():
    """
    Checks if the current Frappe request was initiated by the AI agent
    by looking for a specific HTTP header.
    """
    if hasattr(frappe.local, "request") and frappe.local.request.headers.get(
            "X-Action-Source") == "AI":
        return True
    return False
