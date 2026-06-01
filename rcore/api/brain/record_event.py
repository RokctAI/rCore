# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def record_event(message, reference_doctype, reference_name, is_ai_action=False):
    """
    A secure API endpoint to record a custom event in the Brain's memory.
    """
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
                    def get_label(self, f):
                        return f

                return MockMeta()

        mock_doc = MockDoc()

        from rcore.utils.engram_builder import process_event_in_realtime

        process_event_in_realtime(mock_doc, message)

        return {"status": "success", "message": "Event recorded."}
    except Exception as e:
        frappe.log_error(f"Brain: Failed to record event: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred while recording the event: {e}")
