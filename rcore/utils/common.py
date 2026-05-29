# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
import requests
import json


def call_control(method, data=None):
    """
    Centralized utility to make secure API calls from a tenant to the control panel.
    Requires 'control_plane_url' and 'api_secret' in site_config.json.
    """
    control_plane_url = frappe.conf.get("control_plane_url")
    api_secret = frappe.conf.get("api_secret")

    if not control_plane_url or not api_secret:
        frappe.log_error(
            "Tenant site not configured for control panel communication.",
            "Control API Error",
        )
        return None

    scheme = frappe.conf.get("control_plane_scheme", "https")
    # Endpoint follows the pattern control.control.api.<method>
    api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.{method}"

    headers = {
        "X-Rokct-Secret": api_secret,
        "X-Rokct-Tenant": frappe.local.site,
        "Accept": "application/json",
    }

    try:
        response = requests.post(api_url, headers=headers, json=data or {}, timeout=10)
        response.raise_for_status()
        return response.json().get("message")
    except Exception as e:
        frappe.log_error(
            f"Control API Call Failed ({method}): {str(e)}", "Control API Error"
        )
        return None


def is_ai_action():
    """
    Checks if the current Frappe request was initiated by the AI agent
    by looking for a specific HTTP header.
    """
    if (
        hasattr(frappe.local, "request")
        and frappe.local.request.headers.get("X-Action-Source") == "AI"
    ):
        return True
    return False
