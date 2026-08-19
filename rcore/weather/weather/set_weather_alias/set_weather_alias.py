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


def set_weather_alias(original: Any, corrected: Any) -> Any:
    """
    Proxy endpoint to teach the Control Plane a weather alias.
    Ensures that learnings are centralized and shared (Global Brain).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not original or not corrected:
        frappe.throw("Original and Corrected names are required.")

    # Get connection details
    control_plane_url = frappe.conf.get("control_plane_url")
    api_secret = frappe.conf.get("api_secret")

    if not control_plane_url or not api_secret:
        # If not connected to Control Plane, we fall back to Local Learning
        # This allows standalone tenants to still work.
        service_path = "control.control.weather.set_weather_alias"
        return frappe.call(service_path, original=original, corrected=corrected)

    # Construct the secure API call to Control Plane
    scheme = frappe.conf.get("control_plane_scheme", "https")
    # Note: Target the definition in weather.py which is whitelisted
    api_url = f"{scheme}://{control_plane_url}/api/method/control.control.weather.set_weather_alias"
    headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site, "Accept": "application/json"}

    # We use POST for state-changing operations
    try:
        response = frappe.make_post_request(
            api_url,
            headers=headers,
            data={"original": original, "corrected": corrected},
        )
        return response
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Weather Alias Proxy Error")
        frappe.throw(f"Failed to sync alias to Global Brain: {e}")
