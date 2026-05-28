# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
from frappe.utils import getdate, now_datetime
from datetime import timedelta
try:
    from rcore.utils.subscription_checker import check_subscription_feature
    from rcore.utils import is_ai_action
except ImportError:
    # Fallback if rcore is not installed
    def check_subscription_feature(feature_name):
        def decorator(func):
            return func
        return decorator
    
    def is_ai_action():
        return False

def get_document_title(doctype, name):
    """ Fetches the title of a document based on common title fields. """
    if not frappe.db.exists(doctype, name):
        return name
    try:
        title_fields = ["title", "subject", "full_name", "name"]
        doc_meta = frappe.get_meta(doctype)
        for field in title_fields:
            if doc_meta.has_field(field):
                return frappe.db.get_value(doctype, name, field) or name
        return name
    except Exception:
        return name

def _get_field_changes(doc):
    """
    Compares the document with its state before saving to find changed fields.
    Returns a human-readable string of the most important changes.
    """
    if not hasattr(doc, "_doc_before_save") or not doc._doc_before_save:
        return None

    changes = []
    old_doc = doc._doc_before_save

    # Define a list of fields we consider important enough to log.
    # This avoids logging minor changes like 'modified_by'.
    important_fields = ["status", "workflow_state", "amount", "total", "grand_total", "due_date", "expected_start_date", "expected_end_date"]

    doc_meta = frappe.get_meta(doc.doctype)
    for field in important_fields:
        if doc_meta.has_field(field):
            old_value = old_doc.get(field)
            new_value = doc.get(field)
            if old_value != new_value:
                # Format the change nicely
                field_label = doc_meta.get_label(field)
                changes.append(f"{field_label} changed from '{old_value}' to '{new_value}'")

    return "; ".join(changes) if changes else None

def _get_allowed_roles(doc):
    """
    Returns a list of all roles that have read permission for the given document.
    This includes roles with blanket permissions and roles from document shares.
    """
    allowed_roles = set()

    doc_meta = frappe.get_meta(doc.doctype)
    # Get roles from standard permissions
    for p in doc_meta.permissions:
        if p.read:
            allowed_roles.add(p.role)

    # Get roles from shares
    shares = frappe.get_all("DocShare", fields=["user", "share_name"], filters={"share_doctype": doc.doctype, "share_name": doc.name, "read": 1})
    for share in shares:
        user_roles = frappe.get_roles(share.user)
        for role in user_roles:
            allowed_roles.add(role)

    return list(allowed_roles)

def get_brain_module_doctypes():
    """
    Fetches a list of all doctypes belonging to the 'Brain' module.
    The result is cached for 24 hours to improve performance.
    """
    brain_doctypes = frappe.cache().get_value("brain_module_doctypes")
    if brain_doctypes is None:
        try:
            brain_doctypes = frappe.get_all("DocType", filters={"module": "Brain"}, pluck="name")
            # Cache for 72 hours
            frappe.cache().set_value("brain_module_doctypes", brain_doctypes, expires_in_sec=259200)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Failed to fetch Brain module doctypes")
            # Fallback to a hardcoded list in case of an error
            brain_doctypes = ["Engram"]
    return brain_doctypes

def get_excluded_doctypes_from_control():
    """
    Fetches the list of excluded doctypes from the control panel.
    Caches the result to avoid repeated API calls.
    """
    excluded = frappe.cache().get_value("brain_excluded_doctypes")
    if excluded is None:
        try:
            control_plane_url = frappe.conf.get("control_plane_url")
            api_secret = frappe.conf.get("api_secret")
            if not control_plane_url or not api_secret:
                return []

            scheme = frappe.conf.get("control_plane_scheme", "https")
            api_url = f"{scheme}://{control_plane_url}/api/v1/method/control.control.api.system.get_brain_exclusions"
            headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}

            response = frappe.make_get_request(api_url, headers=headers)
            excluded = response.get("message", [])

            # Cache for 72 hours, as this list is unlikely to change often.
            frappe.cache().set_value("brain_excluded_doctypes", excluded, expires_in_sec=259200)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Failed to fetch brain exclusions from control panel")
            excluded = []
    return excluded

@check_subscription_feature("Memory")
def process_event_in_realtime(doc, method):
    """
    This is the main "storytelling engine". It's called by hooks and
    instantly updates the Engram for a document in real-time.
    """
    # --- Exclusion Logic ---
    # Exclude events triggered by the scheduler to prevent logging of background jobs.
    if getattr(frappe.flags, "in_scheduler", False):
        return

    # Exclude relayed emails from being logged to the brain's memory.
    if frappe.flags.get("is_email_relay"):
        return

    # Fetch all exclusion lists
    brain_doctypes = get_brain_module_doctypes()
    control_excluded = get_excluded_doctypes_from_control()
    
    # Combine the lists for a comprehensive exclusion policy.
    # We include common error/log doctypes to prevent junk memory.
    ignored_doctypes = set(brain_doctypes + control_excluded + [
        "Email Queue", 
        "API Error Log", 
        "Error Log", 
        "Error Snapshot", 
        "Scheduled Job Log",
        "Activity Log",
        "Access Log",
        "Version",
        "Tenant Error Log"
    ])

    if doc.doctype in ignored_doctypes or "Error" in doc.doctype:
        return

    # --- Module Exclusion Logic ---
    # Fetch the module of the document and check if it's in the ignored modules list.
    ignored_modules = {"Lending", "CRM", "HRMS", "Loan Management", "HR", "Payroll"}
    try:
        doc_module = frappe.db.get_value("DocType", doc.doctype, "module")
        if doc_module in ignored_modules:
            return
    except Exception:
        pass

    try:
        # Determine event details
        if doc.doctype == "Email Queue":
            if doc.status != "Sent":
                return
            event_name = "Emailed"
            ref_doctype = doc.reference_doctype
            ref_name = doc.reference_name
            user_name = frappe.db.get_value("User", doc.owner, "full_name") or doc.owner
        else:
            event_name = method.replace('on_', '').capitalize()
            ref_doctype = doc.doctype
            ref_name = doc.name
            user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

        # Get or Create Engram
        engram_name = f"{ref_doctype}-{ref_name}"
        try:
            engram_doc = frappe.get_doc("Engram", engram_name)
        except frappe.DoesNotExistError:
            engram_doc = frappe.new_doc("Engram")
            engram_doc.reference_doctype = ref_doctype
            engram_doc.reference_name = ref_name
            engram_doc.name = engram_name
            engram_doc.reference_title = get_document_title(ref_doctype, ref_name)

            # Get the module for the reference doctype and store it for filtering.
            module = frappe.db.get_value("DocType", ref_doctype, "module")
            engram_doc.module = module

            # Denormalize permissions only on creation
            allowed_roles = _get_allowed_roles(doc)
            for role in allowed_roles:
                engram_doc.append("permissions", {"role": role})

        # --- Real-Time Storytelling Logic ---
        # Check if the last activity was recent (within 24 hours) and by the same user
        is_recent_activity = False
        if engram_doc.last_activity_date:
            time_difference = now_datetime() - engram_doc.last_activity_date
            if time_difference < timedelta(hours=24):
                is_recent_activity = True

        last_line = engram_doc.summary.split('\n')[-1] if engram_doc.summary else ""

        # We compound the event if the activity is recent and by the same user.
        if is_recent_activity and engram_doc.last_modifying_user == frappe.session.user:
            # This logic is now simpler and more robust, as it doesn't need to parse the string.
            # We just append the new event to the summary.
            new_line = f"{event_name} by {user_name} on {getdate(doc.modified).strftime('%Y-%m-%d')}."
            if event_name == "Update":
                changes = _get_field_changes(doc)
                if changes:
                    new_line = new_line.strip('.') + f" ({changes})."

            if is_ai_action():
                new_line = new_line.strip('.') + " (via AI)."

            engram_doc.summary += f"\n{new_line}"
        else:
            # It's a new session, so we add a new line
            event_date = getdate(doc.modified).strftime("%Y-%m-%d")
            if event_name == "Emailed":
                summary_line = f"Emailed on {event_date}."
            else:
                summary_line = f"{event_name} by {user_name} on {event_date}."

            # Add context for 'Update' events
            if event_name == "Update":
                changes = _get_field_changes(doc)
                if changes:
                    summary_line = summary_line.strip('.') + f" ({changes})."

            engram_doc.summary = (engram_doc.summary + "\n" + summary_line) if engram_doc.summary else summary_line

        # Update involved users
        involved = set(engram_doc.get("involved_users", "").split(", ") if engram_doc.get("involved_users") else [])
        involved.add(user_name)
        engram_doc.involved_users = ", ".join(sorted(list(filter(None, involved))))

        engram_doc.last_activity_date = doc.modified
        engram_doc.last_modifying_user = frappe.session.user
        
        # Make memory storage robust: ignore link validation errors (e.g. if User/Role is deleted)
        engram_doc.flags.ignore_links = True
        engram_doc.save(ignore_permissions=True)

        # --- Vector Upsert (New) ---
        # Added to handle Document Activity Logs (not just Chat Summaries)
        try:
            from rcore.services.llm_service import embed_text
            if engram_doc.summary:
                # Context Injection: "Invoice INV-001 (Overdue): ..."
                # This gives MiniLM the "Type" knowledge the user asked for.
                context_text = f"{engram_doc.reference_doctype} {engram_doc.reference_name} ({engram_doc.reference_title}):\n{engram_doc.summary}"
                vector = embed_text(context_text)
                
                if vector:
                    # Only create savepoint and rollback if we are actually attempting the write
                    try:
                        frappe.db.savepoint("vector_update")
                        frappe.db.sql("""
                            UPDATE tabEngram 
                            SET embedding = %s 
                            WHERE name = %s
                        """, (str(vector), engram_doc.name))
                    except Exception as sql_e:
                        frappe.db.rollback(save_point="vector_update")
                        frappe.log_error(f"Failed to write vector for {engram_doc.name}: {sql_e}", "Engram Vector Error")

        except Exception as e:
            # If embedding fails (e.g. API error), just log it, don't rollback the Engram creation
            frappe.log_error(f"Autovectorization skipped for {engram_doc.name}: {e}")

    except Exception:
        frappe.log_error(frappe.get_traceback(), f"Failed to update Engram for {doc.doctype} {doc.name}")