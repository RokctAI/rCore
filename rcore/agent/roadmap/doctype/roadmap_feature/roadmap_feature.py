# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Any, Optional
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
# tenant context check.

import frappe
from frappe.model.document import Document
from rcore.agent.roadmap.utils import construct_contextual_prompt


class RoadmapFeature(Document):
    def get_indicator(self, doc):
        if doc.status == "Done" and doc.type == "Bug":
            return ("Red", "bug", "Bug")
        return None


# Deliberately NOT @frappe.whitelist(): the body reaches Jules on the
# platform's API key, and the platform does not call AI services on a user's
# behalf. Kept intact for internal callers and `bench execute`; it is no longer
# an HTTP endpoint, and its button is hidden in roadmap_feature.json. Features
# are dispatched as GitHub issues instead — see roadmap/api.py assign_to_github.
def assign_to_jules(docname: Any, feature: Any, explanation: Any) -> Any:
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
            frappe.throw(
                "Jules API Key is missing (Roadmap & Global). Please configure it in Roadmap Settings."
            )

        if not source_repo:
            frappe.throw("Source Repository is missing on the Roadmap document.")

        # Step 3: Delegate to Brain Service
        # We now explicitly pass the key and source
        prompt = construct_contextual_prompt(roadmap, feature_doc, "Building")

        session = frappe.call(
            "rcore.api.start_jules_session",
            prompt=prompt,
            source_repo=source_repo,
            api_key=api_key,
            title=feature,
            require_approval=roadmap.require_jules_approval,
        )

        session_id = session.get("name")

        if not session_id:
            frappe.throw(
                "Failed to create a Jules session. No session ID returned from Brain."
            )

        # Step 4: Update the document with tracking info
        feature_doc.db_set("status", "Doing")
        feature_doc.db_set("ai_status", "Assigned")
        feature_doc.db_set("jules_session_id", session_id)

        frappe.msgprint(f"Task '{feature}' has been successfully assigned to Jules.")
        return "Success"

    except Exception as e:
        frappe.log_error(f"Brain Assignment Error: {e}", "Jules Assignment Error")
        frappe.throw(f"Failed to assign task to Jules: {e}")
