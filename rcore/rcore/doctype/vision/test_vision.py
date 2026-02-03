# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestVision(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_create_vision(self):
        vision = frappe.get_doc({
            "doctype": "Vision",
            "title": "Test Vision",
            "description": "To be the best."
        }).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("Vision", vision.name))

    def test_update_vision(self):
        vision = frappe.get_doc({
            "doctype": "Vision",
            "title": "Old Vision"
        }).insert(ignore_permissions=True)

        vision.title = "New Vision"
        vision.save(ignore_permissions=True)

        self.assertEqual(frappe.db.get_value("Vision", vision.name, "title"), "New Vision")

    def test_delete_vision(self):
        vision = frappe.get_doc({
            "doctype": "Vision",
            "title": "Delete Me"
        }).insert(ignore_permissions=True)

        vision.delete(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Vision", vision.name))
