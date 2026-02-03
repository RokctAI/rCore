# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestKPI(FrappeTestCase):
    def setUp(self):
        # Create a Strategic Objective to link to
        # Create a Strategic Objective to link to (with full hierarchy)
        if not frappe.db.exists("Vision", "Test Vision"):
             self.vision = frappe.get_doc({"doctype": "Vision", "title": "Test Vision"}).insert(ignore_permissions=True)
        else:
             self.vision = frappe.get_doc("Vision", "Test Vision")

        if not frappe.db.exists("Pillar", "Test Pillar"):
             self.pillar = frappe.get_doc({"doctype": "Pillar", "title": "Test Pillar", "vision": self.vision.name}).insert(ignore_permissions=True)
        else:
             self.pillar = frappe.get_doc("Pillar", "Test Pillar")

        if not frappe.db.exists("Strategic Objective", "Test Strat Obj"):
            self.strat_obj = frappe.get_doc({
                "doctype": "Strategic Objective",
                "title": "Test Strat Obj",
                "pillar": self.pillar.name
            }).insert(ignore_permissions=True)
        else:
            self.strat_obj = frappe.get_doc("Strategic Objective", "Test Strat Obj")

    def tearDown(self):
        frappe.db.rollback()

    def test_create_kpi(self):
        kpi = frappe.get_doc({
            "doctype": "KPI",
            "title": "Test KPI",
            "description": "Test Description",
            "strategic_objective": self.strat_obj.name
        }).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("KPI", kpi.name))
        self.assertEqual(kpi.strategic_objective, self.strat_obj.name)

    def test_update_kpi(self):
        kpi = frappe.get_doc({
            "doctype": "KPI",
            "title": "Test KPI Update",
            "strategic_objective": self.strat_obj.name
        }).insert(ignore_permissions=True)

        kpi.description = "Updated Description"
        kpi.save(ignore_permissions=True)

        self.assertEqual(frappe.db.get_value("KPI", kpi.name, "description"), "Updated Description")

    def test_delete_kpi(self):
        kpi = frappe.get_doc({
            "doctype": "KPI",
            "title": "Test KPI Delete",
            "strategic_objective": self.strat_obj.name
        }).insert(ignore_permissions=True)

        kpi.delete(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("KPI", kpi.name))
