# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

class TestBrainHooks(FrappeTestCase):
    @patch("rcore.utils.engram_builder.process_event_in_realtime")
    def test_hook_trigger_on_submit(self, mock_process):
        # Create a document that is submittable (e.g., Task if customized, or use a generic one)
        # Note: We just need to check if the hook path in hooks.py is triggered.
        # doc_events = {"*": {"on_submit": "..."}}
        
        doc = frappe.get_doc({
            "doctype": "Note",
            "title": "Hook Test Note",
            "content": "Testing hooks"
        }).insert()
        
        # Simulate submit event
        doc.run_method("on_submit")
        
        # Verify hook was triggered
        self.assertTrue(mock_process.called)
        args, _ = mock_process.call_args
        self.assertEqual(args[0].doctype, "Note")
        self.assertEqual(args[1], "on_submit")

    @patch("rcore.utils.engram_builder.process_event_in_realtime")
    def test_hook_trigger_on_trash(self, mock_process):
        doc = frappe.get_doc({
            "doctype": "Note",
            "title": "Trash Hook Test",
            "content": "Testing trash hook"
        }).insert()
        
        doc.delete()
        
        # Verify hook was triggered
        self.assertTrue(mock_process.called)
        args, _ = mock_process.call_args
        self.assertEqual(args[1], "on_trash")

if __name__ == "__main__":
    import unittest
    unittest.main()
