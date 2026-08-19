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
from rcore.tenant.api.helpers import *


def announce_ready_to_control():
    """
    Called standardly via hooks (after_install) to announce that the tenant
    container is healthy and ready to the Control Hub.
    Reuses ROKCT_BOOTSTRAP_TOKEN (transient env) to authorize.
    """
    import os
    import requests
    token = os.environ.get("ROKCT_BOOTSTRAP_TOKEN")
    control_plane_url = os.environ.get("ROKCT_CONTROL_PLANE_URL") or frappe.conf.get("control_plane_url")
    
    if not token or not control_plane_url:
        return

    scheme = os.environ.get("ROKCT_CONTROL_PLANE_SCHEME") or frappe.conf.get("control_plane_scheme") or "https"
    api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.subscription.announce_tenant_ready"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "site_name": frappe.local.site
    }

    try:
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        frappe.log_error(f"Tenant '{frappe.local.site}' successfully announced readiness to Control Hub.", "Tenant Bootstrap")
    except Exception as e:
        frappe.log_error(f"Tenant '{frappe.local.site}' failed to announce readiness: {e}\n{frappe.get_traceback()}", "Tenant Bootstrap Error")
