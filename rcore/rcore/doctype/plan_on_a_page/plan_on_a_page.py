# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PlanOnAPage(Document):
    def on_update(self):
        # The main Plan On A Page document is a singleton, so we can get it directly
        plan = frappe.get_doc("Plan On A Page")

        # Fetch the linked Vision
        vision = frappe.get_doc("Vision", plan.vision)
        content = f"Vision: {vision.title}\n{vision.description}\n\n"

        # Fetch the Pillars linked to the Vision
        pillars = frappe.get_all("Pillar", filters={"vision": vision.name}, fields=["name", "title", "description"])
        for p in pillars:
            pillar = frappe.get_doc("Pillar", p.name)
            content += f"Pillar: {pillar.title}\n{pillar.description}\n\n"

            # Fetch the Strategic Objectives linked to the Pillar
            objectives = frappe.get_all("Strategic Objective", filters={"pillar": pillar.name}, fields=["name", "title", "description"])
            for o in objectives:
                objective = frappe.get_doc("Strategic Objective", o.name)
                content += f"Objective: {objective.title}\n{objective.description}\n\n"

                # Fetch the KPIs linked to the Strategic Objective
                kpis = frappe.get_all("KPI", filters={"strategic_objective": objective.name}, fields=["name", "title", "description"])
                for k in kpis:
                    kpi = frappe.get_doc("KPI", k.name)
                    content += f"KPI: {kpi.title}\n{kpi.description}\n\n"

        # Create or update the Engram
        # Create or update the Engram
        # Check if Engram doctype exists (Brain app dependency)
        if frappe.db.exists("DocType", "Engram"):
            engram_name = f"plan-on-a-page-{plan.name}"
            if not frappe.db.exists("Engram", engram_name):
                engram = frappe.new_doc("Engram")
                engram.reference_doctype = "Plan On A Page"
                engram.reference_name = plan.name
                engram.reference_title = "Company Strategic Plan"
                engram.summary = content
                engram.insert(ignore_permissions=True)
            else:
                engram = frappe.get_doc("Engram", engram_name)
                engram.summary = content
                engram.save(ignore_permissions=True)
    
            # Set the permissions for the Engram
            if not engram.has_permission("read", "System Manager"):
                engram.add_permission("read", "System Manager")
                engram.save(ignore_permissions=True)

