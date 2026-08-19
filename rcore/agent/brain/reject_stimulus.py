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

@frappe.whitelist()
def reject_stimulus(stimulus_name: str) -> dict:
    """
    Dismisses a stimulus for the current user.
    """
    trace_id = frappe.form_dict.get("trace_id") or "reject-stimulus-trace"
    sys.stderr.write(f"[Trace: {trace_id}] reject_stimulus called with {stimulus_name}\n")

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
