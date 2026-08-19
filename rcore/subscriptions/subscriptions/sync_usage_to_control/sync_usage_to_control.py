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
def sync_usage_to_control(tokens_used, model_name):
    """
    Background job to sync token usage to the control panel.
    """
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        # Stays a DIRECT dotted call, not a platform-gateway cmd: a
        # server-to-control-plane request against a control-app method
        # outside this repo's manifests.
        api_url = f"{scheme}://{control_plane_url}/api/v1/method/control.control.api.report_token_usage_to_control"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        data = {"tokens_used": tokens_used, "model_name": model_name}

        requests.post(api_url, headers=headers, json=data, timeout=30)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sync Usage to Control Failed")
