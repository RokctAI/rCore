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
def query(doctype: str, name: str) -> dict:
    """
    A secure API endpoint for an AI model to query the Brain's memory.
    Ensures security is enforced by checking for read permission.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "query-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] query called for {doctype} {name}\n")
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(f"You do not have permission to access the memory of {doctype} {name}", frappe.PermissionError)

    try:
        engram_name = f"{doctype}-{name}"
        engram_doc = frappe.get_doc("Engram", engram_name)
        response_data = engram_doc.as_dict()
        response_data['brain_version'] = brain_version
        return response_data
    except frappe.DoesNotExistError:
        frappe.throw(f"No Engram found for {doctype} {name}", frappe.NotFound)
    except Exception as e:
        frappe.throw(f"An error occurred while querying the Brain: {e}")
