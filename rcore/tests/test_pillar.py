# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPillar(FrappeTestCase):
    def setUp(self):
        # Create a Vision to link to
        if not frappe.db.exists("Vision", "Test Vision"):
            self.vision = frappe.get_doc({
                "doctype": "Vision",
                "title": "Test Vision"
            }).insert(ignore_permissions=True)
        else:
            self.vision = frappe.get_doc("Vision", "Test Vision")

    def tearDown(self):
        frappe.db.rollback()

    def test_create_pillar(self):
        pillar = frappe.get_doc({
            "doctype": "Pillar",
            "title": "Test Pillar",
            "description": "Test Description",
            "vision": self.vision.name
        }).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("Pillar", pillar.name))
        self.assertEqual(pillar.vision, self.vision.name)

    def test_update_pillar(self):
        pillar = frappe.get_doc({
            "doctype": "Pillar",
            "title": "Test Pillar Update",
            "vision": self.vision.name
        }).insert(ignore_permissions=True)

        pillar.description = "Updated Description"
        pillar.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.get_value(
                "Pillar",
                pillar.name,
                "description"),
            "Updated Description")

    def test_delete_pillar(self):
        pillar = frappe.get_doc({
            "doctype": "Pillar",
            "title": "Test Pillar Delete",
            "vision": self.vision.name
        }).insert(ignore_permissions=True)

        pillar.delete(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Pillar", pillar.name))
