import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def reject_stimulus(stimulus_name):
    """
    Dismisses a stimulus for the current user.
    """
    stimulus = frappe.get_doc("Stimulus", stimulus_name)
    user = frappe.session.user

    if any(d.user == user for d in stimulus.get("dismissed_by", [])):
        return {"status": "success", "message": "Stimulus already dismissed."}

    try:
        stimulus.append("dismissed_by", {"user": user})
        stimulus.save(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": f"Stimulus {stimulus_name} dismissed."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Failed to dismiss stimulus {stimulus_name}")
        frappe.throw(f"An error occurred while dismissing the stimulus: {e}")
