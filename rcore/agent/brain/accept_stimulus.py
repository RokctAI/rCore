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

import json
import frappe
import sys
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient
from rcore.agent.brain.record_event import record_event

@frappe.whitelist()
def accept_stimulus(stimulus_name: str, template_name: str = "Default") -> dict:
    """
    Claims a stimulus for the current user and triggers associated workflows.
    """
    trace_id = frappe.form_dict.get("trace_id") or "accept-stimulus-trace"
    sys.stderr.write(f"[Trace: {trace_id}] accept_stimulus called with {stimulus_name}\n")

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
                from rcore.telemetry.utils import call_control
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
