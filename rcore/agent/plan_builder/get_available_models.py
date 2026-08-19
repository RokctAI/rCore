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

import os
import json
import frappe

@frappe.whitelist(allow_guest=True)
def get_available_models() -> dict:
    """
    Returns available AI models configured on the backend (Single Source of Truth)
    """
    trace_id = frappe.form_dict.get("trace_id") or "get-available-models-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] get_available_models called\n")
    models_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "models.json"))
    if os.path.exists(models_file):
        try:
            with open(models_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            frappe.log_error(f"Failed to read models.json: {str(e)}", "AI Models Configuration")
    return {}
