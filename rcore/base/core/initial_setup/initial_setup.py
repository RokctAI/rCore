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


def initial_setup(
    email,
    password,
    first_name,
    last_name,
    company_name,
    api_secret,
    control_plane_url,
    currency,
    country,
    verification_token,
    login_redirect_url,
    financial_year_begins_on,
):
    """
    Sets up the first user and company. Setup and provisioning tenant context trace.
    """
    _ensure_custom_fields_exist()

    # --- Validation ---
    params_to_check = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "company_name": company_name,
        "api_secret": api_secret,
        "control_plane_url": control_plane_url,
        "currency": currency,
        "country": country,
        "verification_token": verification_token,
    }

    for param_name, param_value in params_to_check.items():
        if not param_value:
            frappe.throw(
                f"Parameter '{param_name}' is missing or empty.",
                title="Missing Information",
            )

    if login_redirect_url is None:
        frappe.throw(
            "The 'login_redirect_url' parameter must be provided, even if it's an empty string.",
            title="Missing Information",
        )

    try:
        validate_email_address(email, throw=True)
    except frappe.exceptions.ValidationError:
        frappe.throw("You must provide a valid email address.", title="Invalid Email")

    if len(password) < 8:
        frappe.throw(
            "Password must be at least 8 characters long.", title="Weak Password"
        )

    print(
        f"--- ROKCT DEBUG: Attempting to create user {email} with password: {password} ---"
    )

    # The security check is only relevant in an HTTP context.
    # When run via `bench execute`, `frappe.local.request` does not exist.
    if hasattr(frappe.local, "request"):
        received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
        if not received_secret:
            frappe.throw("Missing X-Rokct-Secret header.", frappe.AuthenticationError)
        if received_secret != api_secret:
            frappe.throw(
                "Authentication failed. Secrets do not match.",
                frappe.AuthenticationError,
            )

    # --- End Validation ---

    try:
        # Store control panel details for future communication
        # Manually update site_config.json to bypass potential framework init
        # issues.
        site_config_path = frappe.get_site_path("site_config.json")
        with open(site_config_path, "r") as f:
            site_config = json.load(f)

        site_config["api_secret"] = api_secret
        site_config["control_plane_url"] = control_plane_url

        with open(site_config_path, "w") as f:
            json.dump(site_config, f, indent=4)

        # The Company creation hook requires this Warehouse Type to exist.
        if not frappe.db.exists("Warehouse Type", "Transit"):
            frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(
                ignore_permissions=True
            )

        # Create the new company for the tenant, or get it if it already
        # exists.
        if frappe.db.exists("Company", company_name):
            company = frappe.get_doc("Company", company_name)
        else:
            company = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": company_name,
                    "default_currency": currency,
                    "country": country,
                    "is_group": 0,
                    "chart_of_accounts": "Standard with Numbers",
                }
            )
            company.insert(ignore_permissions=True)

        # Create a Fiscal Year for the new company
        year = getdate(financial_year_begins_on).year
        year_name = f"FY {year}"
        year_start_date = getdate(financial_year_begins_on)
        year_end_date = add_days(year_start_date, 364)

        if not frappe.db.exists("Fiscal Year", year_name):
            frappe.get_doc(
                {
                    "doctype": "Fiscal Year",
                    "year": year_name,
                    "year_start_date": year_start_date,
                    "year_end_date": year_end_date,
                }
            ).insert(ignore_permissions=True)

        # Set the new Fiscal Year as the default for the company
        frappe.db.set_value("Company", company.name, "default_fiscal_year", year_name)

        # Get the timezone from the country to set for the user
        time_zone = "Asia/Kolkata"  # Default timezone
        try:
            country_code = frappe.db.get_value("Country", country, "code")
            if country_code:
                timezones = pytz.country_timezones.get(country_code.upper())
                if timezones:
                    time_zone = timezones[0]
        except Exception:
            # If there's any error, just proceed with the default timezone
            frappe.log_error(
                f"Could not determine timezone for country {country}",
                "Timezone Lookup Failed",
            )

        # Create the first user and link them to the company in a single
        # operation.
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "time_zone": time_zone,
                # Mark onboarding as complete
                "onboarding_status": frappe.as_json({}),
                "send_welcome_email": 0,  # The control plane will send the welcome email
                "email_verification_token": verification_token,  # Use token from control panel
                "user_companies": [{"company": company.name, "is_default": 1}],
            }
        )
        user.set("new_password", password)
        try:
            user.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            # This can happen on a retry if the user was created but the overall
            # transaction failed later.
            frappe.log_error(
                f"Initial setup called for existing user {email}",
                "Tenant Initial Setup Warning",
            )
            return {"status": "warning", "message": f"User {email} already exists."}

        # Explicitly add roles and save the user to ensure the changes are persisted
        # before any subsequent operations in the setup process.
        user.add_roles("System Manager", "Company User")
        user.save(ignore_permissions=True)

        # Mark setup as complete to bypass the wizard for the new tenant
        complete_setup_wizard()

        # Disable signup and set custom login redirect on the new tenant site
        website_settings = frappe.get_doc("Website Settings", "Website Settings")
        website_settings.disable_signup = 1
        if login_redirect_url:
            website_settings.custom_login_redirect_url = login_redirect_url
        website_settings.save(ignore_permissions=True)

        frappe.db.commit()
        return {
            "status": "success",
            "message": "Initial user and company setup complete.",
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Tenant Initial Setup Failed")
        frappe.throw(f"An error occurred during initial setup: {e}")
