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

import frappe
import json
from ..utils import api_response


@frappe.whitelist()
def sync_brain_events(events: Any) -> Any:
    """
    Ingests a list of brain events from the mobile app.
    'events' should be a list of dictionaries.
    """
    if isinstance(events, str):
        try:
            events = json.loads(events)
        except Exception:
            frappe.throw("Invalid events format. Expected JSON.")

    if not isinstance(events, list):
        frappe.throw("Events must be a list.")

    ingested_count = 0
    for event_data in events:
        try:
            # Check for required fields
            if not event_data.get(
                    "source") or not event_data.get("event_type"):
                continue

            doc = frappe.get_doc({
                "doctype": "Brain Event",
                "source": event_data.get("source"),
                "event_type": event_data.get("event_type"),
                "entity_id": event_data.get("entity_id"),
                "entity_type": event_data.get("entity_type"),
                "payload": json.dumps(event_data.get("payload", {})),
                "user": frappe.session.user,
                "timestamp": event_data.get("timestamp") or frappe.utils.now()
            })

            # If shop is provided, use it
            if event_data.get("shop"):
                doc.shop = event_data.get("shop")

            doc.insert(ignore_permissions=True)
            ingested_count += 1
        except Exception as e:
            frappe.log_error(
                f"Brain Event Ingestion Failed: {
                    str(e)}", "sync_brain_events")
            continue

    frappe.db.commit()
    return api_response(
        data={"ingested": ingested_count},
        message=f"Successfully ingested {ingested_count} brain events."
    )
