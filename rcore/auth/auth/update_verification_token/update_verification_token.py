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


def update_verification_token(email: Any, token: Any) -> Any:
    """
    Updates the verification token for a given user. Tenant context trace.
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

    try:
        user = frappe.get_doc("User", email)
        user.email_verification_token = token
        user.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Verification token updated."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Verification Token Failed")
        frappe.throw(f"An error occurred while updating the verification token: {e}")
