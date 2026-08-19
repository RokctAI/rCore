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
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient

@frappe.whitelist()
def reject_neurotrophin(neurotrophin_name: str) -> dict:
    """
    Dismisses a neurotrophin for the current user.
    """
    trace_id = frappe.form_dict.get("trace_id") or "reject-neurotrophin-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] reject_neurotrophin called for {neurotrophin_name}\n")
    neurotrophin = frappe.get_doc("Neurotrophin", neurotrophin_name)
    user = frappe.session.user

    if any(d.user == user for d in neurotrophin.get("dismissed_by", [])):
        return {"status": "success", "message": "Funding opportunity already dismissed."}

    try:
        neurotrophin.append("dismissed_by", {"user": user})
        neurotrophin.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": f"Funding Opportunity {neurotrophin_name} dismissed."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Failed to dismiss neurotrophin {neurotrophin_name}")
        frappe.throw(f"An error occurred while dismissing the funding opportunity: {e}")
