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


def create_temporary_support_user(agent_id: str, reason: str, support_email_domain: str) -> Any:
    """
    Creates a temporary support user with a descriptive name and System Manager role. Tenant context trace.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw(
            "This action can only be performed on a tenant site.",
            title="Action Not Allowed",
        )

    # --- Authentication/Authorization ---
    api_secret = frappe.conf.get("api_secret")
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
    if not api_secret or not received_secret:
        frappe.throw(
            "Authentication failed: Missing credentials.", frappe.AuthenticationError
        )
    if received_secret != api_secret:
        frappe.throw(
            "Authentication failed: Invalid credentials.", frappe.AuthenticationError
        )
    # --- End Authentication ---

    # --- Input Validation ---
    if not all([agent_id, reason, support_email_domain]):
        frappe.throw(
            "Agent ID, Reason, and Support Email Domain are required.",
            title="Missing Information",
        )
    # --- End Validation ---

    try:
        # Construct a descriptive email for better audit trails
        support_email = f"support-{agent_id}-{reason}@{support_email_domain}"
        temp_password = frappe.generate_hash(length=16)

        # Check if this exact user already exists (e.g., from a failed previous
        # run)
        if frappe.db.exists("User", support_email):
            frappe.delete_doc(
                "User", support_email, force=True, ignore_permissions=True
            )

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": support_email,
                "first_name": "ROKCT Support",
                "last_name": f"({reason})",
                "send_welcome_email": 0,
                "temporary_user_expires_on": frappe.utils.add_to_date(
                    frappe.utils.now_datetime(), hours=24
                ),
            }
        )
        user.set("new_password", temp_password)
        user.insert(ignore_permissions=True)
        user.add_roles("System Manager")

        # Log this significant security event to the brain
        frappe.call(
            "rcore.agent.brain.record_event.record_event",
            message=f"Temporary support access granted to agent '{agent_id}' for reason: {reason}. User account '{support_email}' created.",
            reference_doctype="User",
            reference_name="Administrator",
        )

        frappe.db.commit()
        return {
            "status": "success",
            "message": {"email": support_email, "password": temp_password},
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(), "Temporary Support User Creation Failed"
        )
        frappe.throw(f"An error occurred during temporary user creation: {e}")
