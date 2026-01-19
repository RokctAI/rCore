# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RoadmapFeature(Document):
    def get_indicator(self, doc):
        if doc.status == "Done" and doc.type == "Bug":
            return ("Red", "bug", "Bug")
        return None

@frappe.whitelist()
def assign_to_jules(docname, feature, explanation):
    """
    Assigns a roadmap feature to the Jules AI assistant via Brain Service.
    """
    try:
        # Step 2: Fetch Creator Details from Parent Roadmap
        feature_doc = frappe.get_doc("Roadmap Feature", docname)
        roadmap = frappe.get_doc("Roadmap", feature_doc.parent)
        
        api_key = roadmap.get_password("jules_api_key")
        source_repo = roadmap.source_repository
        
        if not api_key:
             # FALLBACK to GLOBAL
             settings = frappe.get_single("Roadmap Settings")
             api_key = settings.get_password("jules_api_key")

        if not api_key:
             frappe.throw("Jules API Key is missing (Roadmap & Global). Please configure it in Roadmap Settings.")
             
        if not source_repo:
             frappe.throw("Source Repository is missing on the Roadmap document.")

        # Step 3: Delegate to Brain Service
        # We now explicitly pass the key and source
        prompt = f"Task: {feature}\n\nDetails: {explanation}"
        session = frappe.call("brain.api.start_jules_session", 
            prompt=prompt, 
            source_repo=source_repo, 
            api_key=api_key,
            title=feature,
            require_approval=roadmap.require_jules_approval
        )

        session_id = session.get("name") 

        if not session_id:
             frappe.throw("Failed to create a Jules session. No session ID returned from Brain.")

        # Step 4: Update the document with tracking info
        feature_doc.db_set('status', 'Doing')
        feature_doc.db_set('ai_status', 'Assigned')
        feature_doc.db_set('jules_session_id', session_id)

        frappe.msgprint(f"Task '{feature}' has been successfully assigned to Jules.")
        return "Success"
        
    except Exception as e:
        frappe.log_error(f"Brain Assignment Error: {e}", "Jules Assignment Error")
        frappe.throw(f"Failed to assign task to Jules: {e}")
