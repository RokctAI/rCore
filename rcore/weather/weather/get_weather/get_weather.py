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


def get_weather(location: str) -> Any:
    """
    Proxy endpoint to get weather data from the control site, with tenant-side caching.
    This follows the same authentication pattern as other tenant-to-control-panel APIs.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not location:
        frappe.throw("Location is a required parameter.")

    # Use a different cache key for the proxy to avoid conflicts
    cache_key = f"weather_proxy_{location.lower().replace(' ', '_')}"
    cached_data = frappe.cache().get_value(cache_key)

    if cached_data:
        return cached_data

    # Get connection details from site config (set during tenant provisioning)
    control_plane_url = frappe.conf.get("control_plane_url")
    api_secret = frappe.conf.get("api_secret")

    if not control_plane_url or not api_secret:
        frappe.log_error(
            "Tenant site is not configured to communicate with the control panel.",
            "Weather Proxy Error",
        )
        frappe.throw(
            "Platform communication is not configured.", title="Configuration Error"
        )

    # Construct the secure API call
    scheme = frappe.conf.get("control_plane_scheme", "https")
    api_url = (
        f"{scheme}://{control_plane_url}/api/method/control.control.api.get_weather"
    )
    headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site, "Accept": "application/json"}

    try:
        # Use frappe.make_get_request which is a wrapper around requests
        # and handles logging and exceptions in a standard way.
        response = frappe.make_get_request(
            api_url, headers=headers, params={"location": location}
        )

        # Cache the successful response for 10 minutes on the tenant site
        frappe.cache().set_value(cache_key, response, expires_in_sec=600)

        return response

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Weather Proxy API Error")
        frappe.throw(
            f"An error occurred while fetching weather data from the control plane: {e}"
        )
