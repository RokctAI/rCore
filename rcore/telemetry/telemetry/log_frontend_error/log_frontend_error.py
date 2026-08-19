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
import frappe
import os
import json
import pytz
import requests
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import validate_email_address, get_url, nowdate
from frappe.utils.data import add_days, getdate
from frappe.utils.install import complete_setup_wizard
from rcore.comms.tenant_utils import send_tenant_email
from rcore.core.helpers import *


@frappe.whitelist()
def log_frontend_error(error_message: Any, context: Any=None) -> Any:
    """
    Logs an error from the frontend to the backend, now integrated with the Brain module.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw(
            "This action can only be performed on a tenant site.",
            title="Action Not Allowed",
        )

    if (
        not error_message
        or not isinstance(error_message, str)
        or not error_message.strip()
    ):
        return {
            "status": "error",
            "message": "error_message must be a non-empty string.",
        }

    try:
        # Default document to link the error to is the user's profile
        reference_doctype = "User"
        reference_name = frappe.session.user

        # Construct a more descriptive message for the brain
        brain_message = f"Frontend Error: {error_message}"

        if context:
            try:
                context_data = json.loads(context)
                if isinstance(context_data, dict):
                    # If the context provides a more specific document, use it
                    reference_doctype = context_data.get("doctype", reference_doctype)
                    reference_name = context_data.get("name", reference_name)

                    url = context_data.get("url")
                    if url:
                        brain_message += f" at URL: {url}"
            except json.JSONDecodeError:
                # If context is not valid JSON, just append it to the message
                brain_message += f" | Context: {context}"

        # Call the brain's API to record the event
        frappe.call(
            "rcore.agent.brain.record_event.record_event",
            message=brain_message,
            reference_doctype=reference_doctype,
            reference_name=reference_name,
        )

        return {"status": "success", "message": "Error logged successfully."}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to log frontend error")
        return {"status": "error", "message": "Failed to log error to backend."}
