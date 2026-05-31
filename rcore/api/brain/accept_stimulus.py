import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def accept_stimulus(stimulus_name, template_name="Default"):
    """
    Claims a stimulus for the current user and triggers associated workflows.
    """
    stimulus = frappe.get_doc("Stimulus", stimulus_name)
    if stimulus.claimed_by:
        frappe.throw(f"This stimulus has already been claimed by {stimulus.claimed_by}.", title="Already Claimed")

    try:
        stimulus.claimed_by = frappe.session.user
        stimulus.status = "Claimed"
        stimulus.save(ignore_permissions=True)

        record_event(
            message=f"Stimulus {stimulus_name} claimed by {frappe.session.user}.",
            reference_doctype="Stimulus",
            reference_name=stimulus_name,
            is_ai_action=True
        )

        tasks_to_create = []
        if stimulus.custom_workflow_json:
            try:
                raw_data = json.loads(stimulus.custom_workflow_json)
                tasks_to_create = raw_data.get("tasks", [])
            except: pass
            
        if not tasks_to_create:
            try:
                from rcore.utils.common import call_control
                opportunities = call_control("get_public_opportunities", {
                    "opportunity_type": "tenders", 
                    "filters": json.dumps({"slug": stimulus_name}) 
                })
                if opportunities:
                    tasks_to_create = opportunities[0].get("tasks", [])
            except: pass

        if frappe.db.exists("DocType", "Task"):
            for task_template in tasks_to_create:
                subject = task_template.get("subject") if isinstance(task_template, dict) else task_template
                offset = task_template.get("due_date_offset_days", 7) if isinstance(task_template, dict) else 7
                
                frappe.get_doc({
                    "doctype": "Task",
                    "subject": subject,
                    "exp_start_date": frappe.utils.nowdate(),
                    "exp_end_date": frappe.utils.add_to_date(frappe.utils.nowdate(), days=offset),
                    "_assign": frappe.session.user
                }).insert(ignore_permissions=True)

        frappe.db.commit()
        return {"status": "success", "message": f"Stimulus {stimulus_name} claimed and tasks created."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Failed to claim stimulus {stimulus_name}")
        frappe.throw(f"An error occurred while claiming the stimulus: {e}")
