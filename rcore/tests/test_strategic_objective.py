# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestStrategicObjective(FrappeTestCase):
    def setUp(self):
        # Create a Vision link target if it doesn't exist
        vision_name = frappe.db.get_value("Vision", {"title": "Test Vision"}, "name")
        if not vision_name:
            vision = frappe.get_doc({
                "doctype": "Vision",
                "title": "Test Vision",
                "description": "Test Vision Description"
            }).insert(ignore_permissions=True)
            vision_name = vision.name

        # Create a Pillar to link to
        pillar_name = "Test Pillar For Strat"
        if not frappe.db.exists("Pillar", pillar_name):
            self.pillar = frappe.get_doc({
                "doctype": "Pillar",
                "title": pillar_name,
                "vision": vision_name
            }).insert(ignore_permissions=True)
        else:
            self.pillar = frappe.get_doc("Pillar", pillar_name)
            if self.pillar.vision != vision_name:
                self.pillar.vision = vision_name
                self.pillar.save(ignore_permissions=True)

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
