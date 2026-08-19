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
def record_event(message: str, reference_doctype: str, reference_name: str, is_ai_action: bool = False) -> dict:
    """
    A secure API endpoint to record a custom event in the Brain's memory.
    """
    trace_id = frappe.form_dict.get("trace_id") or "record-event-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] record_event called for {reference_doctype} {reference_name}\n")
    try:
        class MockDoc:
            def __init__(self):
                self.doctype = reference_doctype
                self.name = reference_name
                self.modified = frappe.utils.now()
                self.owner = frappe.session.user
                self.is_ai_action = is_ai_action
                self._doc_before_save = None

            def has_field(self, fieldname):
                return False

            def get(self, key, default=None):
                return getattr(self, key, default)

            @property
            def meta(self):
                class MockMeta:
                    def get_label(self, f): return f
                return MockMeta()

        mock_doc = MockDoc()

        from rcore.agent.utils.engram_builder import process_event_in_realtime
        process_event_in_realtime(mock_doc, message)

        return {"status": "success", "message": "Event recorded."}
    except Exception as e:
        frappe.log_error(f"Brain: Failed to record event: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred while recording the event: {e}")
