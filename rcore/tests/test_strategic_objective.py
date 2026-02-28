# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestStrategicObjective(FrappeTestCase):
    def setUp(self):
        # Create a Vision link target if it doesn't exist
        if not frappe.db.exists("Vision", "Test Vision"):
            frappe.get_doc({
                "doctype": "Vision",
                "title": "Test Vision",
                "description": "Test Vision Description"
            }).insert(ignore_permissions=True)

        # Create a Pillar to link to
        if not frappe.db.exists("Pillar", "Test Pillar For Strat"):
            self.pillar = frappe.get_doc({
                "doctype": "Pillar",
                "title": "Test Pillar For Strat",
                "vision": "Test Vision"
            }).insert(ignore_permissions=True)
        else:
            self.pillar = frappe.get_doc("Pillar", "Test Pillar For Strat")

    def tearDown(self):
        frappe.db.rollback()

    def test_create_strat_obj(self):
        obj = frappe.get_doc({
            "doctype": "Strategic Objective",
            "title": "Test Strat Obj",
            "pillar": self.pillar.name
        }).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("Strategic Objective", obj.name))
        self.assertEqual(obj.pillar, self.pillar.name)

    def test_update_strat_obj(self):
        obj = frappe.get_doc({
            "doctype": "Strategic Objective",
            "title": "Test Obj Update",
            "pillar": self.pillar.name
        }).insert(ignore_permissions=True)

        obj.description = "New Desc"
        obj.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.get_value(
                "Strategic Objective",
                obj.name,
                "description"),
            "New Desc")
