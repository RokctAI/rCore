# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from rcore.api import query, record_event, get_event_interval


class TestBrainAPI(FrappeTestCase):
    def setUp(self):
        # We'll use mocking for most of these to avoid DB setup overhead
        # for these specific unit tests, but inheritance from FrappeTestCase
        # is kept for consistency with standard Frappe testing.
        pass

    @patch("rcore.api.brain.query.frappe.has_permission")
    @patch("rcore.api.brain.query.frappe.get_doc")
    def test_query_success(self, mock_get_doc, mock_has_permission):
        mock_has_permission.return_value = True

        mock_engram = MagicMock()
        mock_engram.as_dict.return_value = {"summary": "Test Summary"}
        mock_get_doc.return_value = mock_engram

        result = query("ToDo", "TODO-001")

        self.assertEqual(result["summary"], "Test Summary")
        self.assertIn("brain_version", result)
        mock_has_permission.assert_called_with("ToDo", "read", doc="TODO-001")

    @patch("rcore.api.brain.query.frappe.has_permission")
    def test_query_permission_denied(self, mock_has_permission):
        mock_has_permission.return_value = False

        with self.assertRaises(frappe.PermissionError):
            query("ToDo", "TODO-001")

    @patch("rcore.api.brain.query.frappe.has_permission")
    @patch("rcore.api.brain.query.frappe.get_doc")
    def test_query_not_found(self, mock_get_doc, mock_has_permission):
        mock_has_permission.return_value = True
        mock_get_doc.side_effect = frappe.DoesNotExistError

        with self.assertRaises(frappe.NotFound):
            query("ToDo", "NON-EXISTENT")

    @patch("rcore.utils.engram_builder.process_event_in_realtime")
    @patch("rcore.api.brain.record_event.frappe.session")
    def test_record_event_success(self, mock_session, mock_process):
        mock_session.user = "test@example.com"

        result = record_event("Action failed", "ToDo", "TODO-001", is_ai_action=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Event recorded.")

        # Verify process_event_in_realtime was called with a MockDoc-like object
        args, _ = mock_process.call_args
        mock_doc = args[0]
        self.assertEqual(mock_doc.doctype, "ToDo")
        self.assertEqual(mock_doc.name, "TODO-001")
        self.assertEqual(args[1], "Action failed")

    @patch("rcore.api.brain.get_event_interval.frappe.get_doc")
    def test_get_event_interval_success(self, mock_get_doc):
        mock_engram = MagicMock()
        mock_engram.summary = (
            "Created by Admin on 2025-01-01\n"
            "Submitted by Admin on 2025-01-02\n"
            "Paid by Admin on 2025-01-05\n"
        )
        mock_get_doc.return_value = mock_engram

        result = get_event_interval("ToDo", "TODO-001", "Submitted", "Paid")

        self.assertEqual(result["interval_days"], 3)

    @patch("rcore.api.brain.get_event_interval.frappe.get_doc")
    def test_get_event_interval_missing_event(self, mock_get_doc):
        mock_engram = MagicMock()
        mock_engram.summary = "Created by Admin on 2025-01-01"
        mock_get_doc.return_value = mock_engram

        result = get_event_interval("ToDo", "TODO-001", "Submitted", "Paid")

        self.assertIn("error", result)
        self.assertIn("Could not find one or more events", result["error"])


if __name__ == "__main__":
    import unittest

    unittest.main()
