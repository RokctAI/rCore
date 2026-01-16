# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json

@frappe.whitelist()
def commit_plan(plan_data):
    """
    Accepts a JSON payload from the frontend and creates the entire "Plan on a Page".
    """
    try:
        data = json.loads(plan_data)

        # 1. Create the Vision
        vision_doc = frappe.new_doc("Vision")
        vision_doc.title = data.get("vision_title")
        vision_doc.description = data.get("vision_description")
        vision_doc.insert(ignore_permissions=True)

        # 2. Create Pillars and their corresponding Objectives and KPIs
        for pillar_data in data.get("pillars", []):
            pillar_doc = frappe.new_doc("Pillar")
            pillar_doc.title = pillar_data.get("title")
            pillar_doc.description = pillar_data.get("description")
            pillar_doc.vision = vision_doc.name
            pillar_doc.insert(ignore_permissions=True)

            for objective_data in pillar_data.get("objectives", []):
                objective_doc = frappe.new_doc("Strategic Objective")
                objective_doc.title = objective_data.get("title")
                objective_doc.description = objective_data.get("description")
                objective_doc.pillar = pillar_doc.name
                objective_doc.insert(ignore_permissions=True)

                for kpi_data in objective_data.get("kpis", []):
                    kpi_doc = frappe.new_doc("KPI")
                    kpi_doc.title = kpi_data.get("title")
                    kpi_doc.description = kpi_data.get("description")
                    kpi_doc.strategic_objective = objective_doc.name
                    kpi_doc.insert(ignore_permissions=True)

        # 3. Link the Vision to the main Plan On A Page singleton document
        plan_doc = frappe.get_doc("Plan On A Page")
        plan_doc.vision = vision_doc.name
        plan_doc.save(ignore_permissions=True) # This will trigger the on_update hook

        return {"status": "success", "message": "Plan on a Page created successfully."}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "commit_plan Error")
        return {"status": "error", "message": str(e)}
