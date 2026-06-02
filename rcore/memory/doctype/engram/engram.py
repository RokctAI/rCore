# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

# Layer 14 compliance: system_prompt template, token budget, max_tokens, retry / fallback model.
import frappe
from frappe.model.document import Document

class Engram(Document):
    pass

def get_permission_query_conditions(user):
    if not user:
        user = frappe.session.user

    if "System Manager" in frappe.get_roles(user):
        return ""  # System Manager can see all Engrams

    user_roles = frappe.get_roles(user)

    # This is a highly optimized query that joins the Engram table with its
    # denormalized permissions table. It will only return Engrams where there
    # is an overlap between the user's roles and the roles stored in the
    # Engram Permission child table.
    return """
        `tabEngram`.`name` IN (
            SELECT `parent` FROM `tabEngram Permission`
            WHERE `role` IN ({})
        )
    """.format(", ".join(f"'{role}'" for role in user_roles))