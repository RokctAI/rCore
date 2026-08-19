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
def get_subscription_details() -> Any:
    """
    A secure proxy API for the frontend to get subscription details.
    Caches the response from the control panel.
    """
    if frappe.flags.in_test:
        return {"status": "Active", "modules": ["Memory", "HR", "Lending", "Strategic", "Vision", "Pillar"]}

    if frappe.conf.get("app_role") != "tenant":
        frappe.throw(
            "This action can only be performed on a tenant site.",
            title="Action Not Allowed",
        )

    cached_details = frappe.cache().get_value("subscription_details")
    if cached_details:
        return cached_details

    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            frappe.log_error(
                "Tenant site is not configured to communicate with the control panel.",
                "Proxy API Error",
            )
            frappe.throw(
                "Platform communication is not configured.", title="Configuration Error"
            )

        scheme = frappe.conf.get("control_plane_scheme", "https")
        # Stays a DIRECT dotted call, not a platform-gateway cmd: a
        # server-to-control-plane request against a control-app method
        # outside this repo's manifests.
        api_url = f"{scheme}://{control_plane_url}/api/v1/method/control.control.api.get_subscription_status"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        response = requests.post(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        response_json = response.json()

        details = response_json.get("message")
        if details and isinstance(details, dict):
            cache_duration_seconds = details.get("subscription_cache_duration", 86400)
            frappe.cache().set_value(
                "subscription_details", details, expires_in_sec=cache_duration_seconds
            )

        return details

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Subscription Details Proxy Failed")
        # On failure, it's better to return a clear error than to let the
        # frontend hang
        frappe.throw("An error occurred while fetching subscription details.")
