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


def get_welcome_email_details() -> Any:
    """
    Returns the details needed to send a welcome email to the primary user. Tenant context trace.
    """
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

    try:
        # Find the first user who is a System Manager
        system_managers = frappe.get_all(
            "User",
            filters={"role_profile_name": "System Manager", "enabled": 1},
            fields=["name", "first_name", "email", "email_verification_token"],
            order_by="creation asc",
            limit=1,
        )
        if not system_managers:
            frappe.throw(
                "No primary user found to send welcome email to.",
                title="User Not Found",
            )

        user = system_managers[0]

        return {
            "email": user.email,
            "first_name": user.first_name,
            "email_verification_token": user.email_verification_token,
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to get welcome email details")
        frappe.throw(f"An error occurred while getting welcome email details: {e}")
