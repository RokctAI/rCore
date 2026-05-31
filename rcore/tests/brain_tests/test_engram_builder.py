# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from rcore.utils.engram_builder import process_event_in_realtime, _get_field_changes
from datetime import datetime, timedelta


class TestEngramBuilder(FrappeTestCase):
    def setUp(self):
        self.user = "test_engram@example.com"
        if not frappe.db.exists("User", self.user):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.user,
                    "first_name": "Test",
                    "last_name": "Engram",
                    "roles": [{"role": "System Manager"}],
                }
            ).insert(ignore_permissions=True)
        frappe.set_user(self.user)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_get_field_changes(self):
        # Create real documents for ToDo
        doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "New Description",
                "status": "Open",
                "assigned_by": "test@example.com",
            }
        )
        doc._doc_before_save = frappe.get_doc(
            {
                "doctype": "ToDo",
                "status": "Draft",
                "assigned_by": "test@example.com",  # Ensure _doc_before_save has required fields if any
            }
        )

        changes = _get_field_changes(doc)
        self.assertIn("Status changed from 'Draft' to 'Open'", changes)

    @patch("rcore.utils.engram_builder.get_brain_module_doctypes")
    @patch("rcore.utils.engram_builder.get_excluded_doctypes_from_control")
    def test_process_event_exclusion_logic(self, mock_control, mock_brain):
        mock_rcore.return_value = ["Engram"]
        mock_control.return_value = ["ExcludedDoc"]

        # Capture real get_value
        real_get_value = frappe.db.get_value

        def side_effect(doctype, docname, fieldname=None, **kwargs):
            if doctype == "DocType" and fieldname == "module":
                if docname == "Loan":
                    return "Lending"
                if docname == "ToDo":
                    return "Core"
            return real_get_value(doctype, docname, fieldname, **kwargs)

        with patch(
            "rcore.utils.engram_builder.frappe.db.get_value", side_effect=side_effect
        ):
            # Test brain doctype exclusion
            doc = MagicMock(doctype="Engram")
            process_event_in_realtime(doc, "on_update")
            self.assertFalse(frappe.db.exists("Engram", "Engram-None"))

            # Test control plane exclusion
            doc = MagicMock(doctype="ExcludedDoc")
            process_event_in_realtime(doc, "on_update")
            self.assertFalse(frappe.db.exists("Engram", "ExcludedDoc-None"))

            # Test system module exclusion
            doc = MagicMock(doctype="Loan")
            process_event_in_realtime(doc, "on_update")
            self.assertFalse(frappe.db.exists("Engram", "Loan-None"))

    @patch("rcore.utils.engram_builder.now_datetime")
    @patch("rcore.utils.engram_builder._get_allowed_roles")
    @patch("rcore.services.llm_service.embed_text")  # Patch embedding
    def test_process_event_compounding(self, mock_embed, mock_roles, mock_now):
        mock_roles.return_value = ["System Manager"]
        mock_now.return_value = datetime(2025, 1, 1, 12, 0, 0)
        # Mock successful embedding
        mock_embed.return_value = [0.1] * 384

        doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Compounding ToDo",
            }
        )
        doc.insert(ignore_permissions=True)
        # Ensure the object has the mocked date, overriding system time
        doc.modified = "2025-01-01 12:00:00"

        # 1. Initial event
        process_event_in_realtime(doc, "on_submit")
        engram_name = f"ToDo-{doc.name}"

        engram = frappe.get_doc("Engram", engram_name)
        # DEBUG: Print what we got
        # print(f"DEBUG: Summary is: {engram.summary}")

        # Verify 'Submit' (method name) not 'Submitted'
        self.assertIn("Submit by Test Engram on 2025-01-01.", engram.summary)

        # 2. Compound event (same user, within 24h)
        mock_now.return_value = datetime(2025, 1, 1, 15, 0, 0)
        # Manually update date on object
        doc.modified = "2025-01-01 15:00:00"

        process_event_in_realtime(doc, "on_update")

        engram.reload()
        # print(f"DEBUG: Summary after update is: {engram.summary}")
        self.assertIn(
            "Submit by Test Engram on 2025-01-01.\nUpdate by Test Engram on 2025-01-01.",
            engram.summary,
        )
        self.assertEqual(engram.last_modifying_user, self.user)

    @patch("rcore.utils.engram_builder.now_datetime")
    @patch("rcore.services.llm_service.embed_text")  # Patch embedding
    def test_process_event_new_session(self, mock_embed, mock_now):
        mock_now.return_value = datetime(2025, 1, 1, 12, 0, 0)
        # Mock successful embedding
        mock_embed.return_value = [0.1] * 384

        doc = frappe.get_doc(
            {
                "doctype": "ToDo",
                "description": "Session ToDo",
            }
        )
        doc.insert(ignore_permissions=True)
        # Force the date on object
        doc.modified = "2025-01-01 12:00:00"

        # 1. Initial event
        process_event_in_realtime(doc, "on_submit")

        # 2. New session (after 24h)
        mock_now.return_value = datetime(2025, 1, 3, 12, 0, 0)
        # Force new date on object
        doc.modified = "2025-01-03 12:00:00"

        process_event_in_realtime(doc, "on_update")

        engram_name = f"ToDo-{doc.name}"
        engram = frappe.get_doc("Engram", engram_name)

        # Use simple string split
        lines = engram.summary.strip().split("\n")
        # print(f"DEBUG: Session Summary lines: {lines}")

        self.assertEqual(len(lines), 2)
        # Check first line date
        self.assertIn("2025-01-01", lines[0])
        # Check second line date
        self.assertIn("2025-01-03", lines[1])


if __name__ == "__main__":
    import unittest

    unittest.main()
