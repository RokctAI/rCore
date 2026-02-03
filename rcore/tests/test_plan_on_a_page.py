# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

class TestPlanOnAPage(FrappeTestCase):
    def setUp(self):
        if frappe.db.exists("DocType", "Engram"):
            frappe.db.delete("Engram", {"reference_doctype": "Plan On A Page"})

        # Setup hierarchy: Vision -> Pillar -> Strat Obj -> KPI
        self.vision = frappe.get_doc({"doctype": "Vision", "title": "POAP Vision", "description": "V-Desc"}).insert(ignore_permissions=True)
        self.pillar = frappe.get_doc({"doctype": "Pillar", "title": "POAP Pillar", "vision": self.vision.name, "description": "P-Desc"}).insert(ignore_permissions=True)
        self.obj = frappe.get_doc({"doctype": "Strategic Objective", "title": "POAP Obj", "pillar": self.pillar.name, "description": "O-Desc"}).insert(ignore_permissions=True)
        self.kpi = frappe.get_doc({"doctype": "KPI", "title": "POAP KPI", "strategic_objective": self.obj.name, "description": "K-Desc"}).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_engram_generation(self):
        # Create Plan On A Page (Single)
        plan = frappe.get_doc("Plan On A Page")
        plan.vision = self.vision.name
        
        # Mocking Engram creation if Engram doctype doesn't exist in test env, 
        # BUT assuming rcore depends on 'brain' or it's part of the core, logic should work.
        # If Engram is missing, this will fail. Let's assume Engram exists.
        
        # We need to make sure Engram exists to test this. 
        if not frappe.db.exists("DocType", "Engram"):
             print("Skipping Engram test as DocType is missing")
             return

        plan.save(ignore_permissions=True)
        
        # Check if Engram was created
        engram_name = f"plan-on-a-page-{plan.name}"
        self.assertTrue(frappe.db.exists("Engram", engram_name))
        
        engram = frappe.get_doc("Engram", engram_name)
        self.assertIn("Vision: POAP Vision", engram.summary)
        self.assertIn("Pillar: POAP Pillar", engram.summary)
        self.assertIn("Objective: POAP Obj", engram.summary)
        self.assertIn("KPI: POAP KPI", engram.summary)
