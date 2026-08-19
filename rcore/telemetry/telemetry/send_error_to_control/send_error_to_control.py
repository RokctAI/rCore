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


def send_error_to_control(doc):
    """
    The background job that makes the actual API call to the control panel.
    """
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            # Silently fail if the tenant is not configured to talk to the
            # control panel
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.report_tenant_error"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        data = {"error_details": doc.as_json()}

        requests.post(api_url, headers=headers, json=data, timeout=30)
        # We don't check the response, this is a "fire and forget" operation.
        # If it fails, the control panel will log its own error, and we avoid
        # an infinite loop.

    except Exception:
        # We log the failure to the local error log, but we don't re-throw
        # to prevent a potential infinite loop of error reporting.
        frappe.log_error(
            frappe.get_traceback(), "Failed to forward error to control panel"
        )
