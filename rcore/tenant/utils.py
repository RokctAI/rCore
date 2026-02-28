# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import requests


def _send_via_control_relay(**kwargs):
    """
    Makes a secure backend call to the control panel to relay the email.
    """
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            # If the site isn't configured for relay, we can't proceed.
            raise frappe.ValidationError(
                "Email relay is not configured for this site.")

        # Prepare the arguments for the relay endpoint
        relay_args = {
            "recipients": kwargs.get("recipients"),
            "subject": kwargs.get("subject"),
            "message": kwargs.get("message")
        }

        # The control panel will use the Host header to identify the tenant.
        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.email.relay_email"
        headers = {"X-Rokct-Secret": api_secret}

        response = requests.post(api_url, data=relay_args, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        if response_json.get("status") != "success":
            # If the relay fails, log it and raise an exception to notify the
            # caller.
            frappe.log_error(
                f"Failed to relay email via control panel. Response: {response_json}",
                "Email Relay Error")
            raise frappe.ValidationError(
                "Failed to send email via the central mailer.")

    except Exception as e:
        # Catch any exception and re-raise it to ensure the caller knows the
        # email failed.
        frappe.log_error(frappe.get_traceback(), "Email Relay Failed")
        raise e


def send_tenant_email(**kwargs):
    """
    A centralized utility for sending emails from a tenant site.
    It follows a specific fallback order:
    1. Check for a default outgoing Email Account configured on the tenant site.
    2. If none, attempt to relay the email through the control panel.
    3. If relay is not configured or fails, the operation will fail.
    """
    try:
        # 1. Check if a default outgoing email account is configured and
        # enabled on this site.
        default_account = frappe.db.get_value(
            "Email Account", {
                "default_outgoing": 1, "enable_outgoing": 1})
        if default_account:
            # If a local default exists, use it.
            frappe.sendmail(**kwargs)
            return
    except Exception:
        # This can happen if the database is not yet fully migrated.
        # We can safely ignore this and proceed to the relay.
        pass

    # 2. If no local default is found, try to relay through the control panel.
    print("--- No local email account found. Attempting to relay via control panel. ---")
    _send_via_control_relay(**kwargs)
