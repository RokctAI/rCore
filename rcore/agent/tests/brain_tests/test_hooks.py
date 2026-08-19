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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

class TestBrainHooks(FrappeTestCase):
    @patch("rcore.agent.utils.engram_builder.process_event_in_realtime")
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

    @patch("rcore.agent.utils.engram_builder.process_event_in_realtime")
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
