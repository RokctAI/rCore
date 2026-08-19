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


def set_platform_secret(secret: str) -> Any:
    """
    Sets the Platform Sync Secret in the site config.
    Called by Next.js upon Tenant Admin login.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            "Only System Managers can set the Platform Secret.", frappe.PermissionError
        )

    if not secret:
        return

    try:
        site_config_path = frappe.get_site_path("site_config.json")
        with open(site_config_path, "r") as f:
            site_config = json.load(f)

        # Only update if different to avoid file IO spam
        if site_config.get("platform_sync_secret") != secret:
            site_config["platform_sync_secret"] = secret
            with open(site_config_path, "w") as f:
                json.dump(site_config, f, indent=4)

        return {"status": "success"}
    except Exception as e:
        frappe.log_error(f"Failed to set platform secret: {str(e)}")
        return {"status": "error", "message": str(e)}
