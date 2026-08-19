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

def _ensure_custom_fields_exist():
    """
    Explicitly creates custom fields that are required by this script,
    bypassing the need for a full `sync_for` which can be slow and unreliable
    in this context. This makes the script more robust.
    """
    if not frappe.db.exists("Custom Field", "Company-default_fiscal_year"):
        create_custom_field(
            "Company",
            {
                "fieldname": "default_fiscal_year",
                "label": "Default Fiscal Year",
                "fieldtype": "Link",
                "options": "Fiscal Year",
                "insert_after": "credit_limit",
            },
        )

    # Fields for Token Quota Tracking on User
    if not frappe.db.exists("Custom Field", "User-daily_token_usage"):
        create_custom_field(
            "User",
            {
                "fieldname": "daily_token_usage",
                "label": "Daily Token Usage",
                "fieldtype": "Int",
                "default": 0,
                "insert_after": "enabled",
            },
        )
    if not frappe.db.exists("Custom Field", "User-monthly_token_usage"):
        create_custom_field(
            "User",
            {
                "fieldname": "monthly_token_usage",
                "label": "Monthly Token Usage",
                "fieldtype": "Int",
                "default": 0,
                "insert_after": "daily_token_usage",
            },
        )
    if not frappe.db.exists("Custom Field", "User-daily_pro_usage"):
        create_custom_field(
            "User",
            {
                "fieldname": "daily_pro_usage",
                "label": "Daily Pro Usage",
                "fieldtype": "Int",
                "default": 0,
                "insert_after": "monthly_token_usage",
            },
        )
    if not frappe.db.exists("Custom Field", "User-daily_flash_usage"):
        create_custom_field(
            "User",
            {
                "fieldname": "daily_flash_usage",
                "label": "Daily Flash Usage",
                "fieldtype": "Int",
                "default": 0,
                "insert_after": "daily_pro_usage",
            },
        )
    if not frappe.db.exists("Custom Field", "User-last_token_date"):
        create_custom_field(
            "User",
            {
                "fieldname": "last_token_date",
                "label": "Last Token Date",
                "fieldtype": "Date",
                "insert_after": "daily_flash_usage",
            },
        )
    if not frappe.db.exists("Custom Field", "User-ai_seat_assigned"):
        create_custom_field(
            "User",
            {
                "fieldname": "ai_seat_assigned",
                "label": "AI Seat Assigned",
                "fieldtype": "Check",
                "default": 0,
                "insert_after": "last_token_date",
            },
        )

    # Tracing observability fields
    for doctype in ["User", "Company", "Employee", "Customer"]:
        # Only check/create if DocType exists to prevent crash on missing sub-apps
        if doctype == "Employee" and not frappe.db.exists("DocType", "Employee"):
            continue
        if doctype == "Customer" and not frappe.db.exists("DocType", "Customer"):
            continue
        if not frappe.db.exists("Custom Field", f"{doctype}-trace_id"):
            create_custom_field(
                doctype,
                {
                    "fieldname": "trace_id",
                    "label": "Trace ID",
                    "fieldtype": "Data",
                    "insert_after": "status" if doctype != "Company" else "company_name",
                    "read_only": 1,
                },
            )

def _notify_control_of_verification():
    """Makes a secure backend call to the control panel to mark the subscription as verified."""
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            frappe.log_error(
                "Tenant site is not configured to communicate with the control panel.",
                "Verification Notification Error",
            )
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.mark_subscription_as_verified"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        # The site name is implicitly sent via the request's Host header,
        # which the control panel will use to identify the subscription.
        response = requests.post(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        response_json = response.json()

        if response_json.get("status") != "success":
            frappe.log_error(
                f"Failed to notify control panel of verification. Response: {response_json}",
                "Verification Notification Error",
            )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Verification Notification Failed")