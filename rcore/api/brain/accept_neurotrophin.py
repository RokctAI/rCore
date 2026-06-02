import json
import frappe
import sys
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient
from rcore.api.brain.record_event import record_event

@frappe.whitelist()
def accept_neurotrophin(neurotrophin_name: str, template_name: str = "Default") -> dict:
    """
    Accepts a neurotrophin (funding opportunity) and triggers associated workflows.
    """
    trace_id = frappe.form_dict.get("trace_id") or "accept-neurotrophin-trace"
    sys.stderr.write(f"[Trace: {trace_id}] accept_neurotrophin called with {neurotrophin_name}\n")

    neurotrophin = frappe.get_doc("Neurotrophin", neurotrophin_name)
    if neurotrophin.claimed_by:
        frappe.throw(f"This funding opportunity has already been accepted by {neurotrophin.claimed_by}.", title="Already Accepted")

    try:
        neurotrophin.claimed_by = frappe.session.user
        neurotrophin.status = "Accepted"
        neurotrophin.save(ignore_permissions=True)

        record_event(
            message=f"Funding Opportunity {neurotrophin_name} accepted by {frappe.session.user}.",
            reference_doctype="Neurotrophin",
            reference_name=neurotrophin_name,
            is_ai_action=True
        )

        tasks_to_create = []
        if neurotrophin.raw_json:
            try:
                raw_data = json.loads(neurotrophin.raw_json)
                tasks_to_create = raw_data.get("tasks", [])
            except: pass

        if not tasks_to_create:
            try:
                from rcore.utils.common import call_control
                opportunities = call_control("get_public_opportunities", {
                    "opportunity_type": "grants", 
                    "filters": json.dumps({"slug": neurotrophin.slug}) 
                })
                if opportunities:
                    tasks_to_create = opportunities[0].get("tasks", [])
            except: pass

        if frappe.db.exists("DocType", "Task"):
            for task_subject in tasks_to_create:
                subject = task_subject.get("subject") if isinstance(task_subject, dict) else task_subject
                offset = task_subject.get("due_date_offset_days", 7) if isinstance(task_subject, dict) else 7
                
                frappe.get_doc({
                    "doctype": "Task",
                    "subject": subject,
                    "exp_start_date": frappe.utils.nowdate(),
                    "exp_end_date": frappe.utils.add_to_date(frappe.utils.nowdate(), days=offset),
                    "_assign": frappe.session.user
                }).insert(ignore_permissions=True)

        frappe.db.commit()
        return {"status": "success", "message": f"Funding Opportunity {neurotrophin_name} accepted and tasks created."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Failed to accept neurotrophin {neurotrophin_name}")
        frappe.throw(f"An error occurred while accepting the funding opportunity: {e}")
