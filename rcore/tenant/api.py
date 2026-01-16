# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import os
import json
import pytz
import requests
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import validate_email_address, get_url, nowdate
from frappe.utils.data import add_days, getdate
from frappe.utils.install import complete_setup_wizard
from rcore.tenant.utils import send_tenant_email

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
        create_custom_field("User", {
            "fieldname": "daily_token_usage", "label": "Daily Token Usage", "fieldtype": "Int", "default": 0, "insert_after": "enabled"
        })
    if not frappe.db.exists("Custom Field", "User-monthly_token_usage"):
        create_custom_field("User", {
            "fieldname": "monthly_token_usage", "label": "Monthly Token Usage", "fieldtype": "Int", "default": 0, "insert_after": "daily_token_usage"
        })
    if not frappe.db.exists("Custom Field", "User-daily_pro_usage"):
        create_custom_field("User", {
            "fieldname": "daily_pro_usage", "label": "Daily Pro Usage", "fieldtype": "Int", "default": 0, "insert_after": "monthly_token_usage"
        })
    if not frappe.db.exists("Custom Field", "User-daily_flash_usage"):
        create_custom_field("User", {
            "fieldname": "daily_flash_usage", "label": "Daily Flash Usage", "fieldtype": "Int", "default": 0, "insert_after": "daily_pro_usage"
        })
    if not frappe.db.exists("Custom Field", "User-last_token_date"):
        create_custom_field("User", {
            "fieldname": "last_token_date", "label": "Last Token Date", "fieldtype": "Date", "insert_after": "daily_flash_usage"
        })
    if not frappe.db.exists("Custom Field", "User-ai_seat_assigned"):
        create_custom_field("User", {
            "fieldname": "ai_seat_assigned", "label": "AI Seat Assigned", "fieldtype": "Check", "default": 0, "insert_after": "last_token_date"
        })

def forward_error_to_control(doc, method):
    """
    This function is called by a hook when a new API Error Log is created.
    It enqueues a background job to send the error to the control panel.
    """
    if frappe.conf.get("app_role") == "tenant":
        frappe.enqueue(
            "rcore.tenant.api.send_error_to_control",
            doc=doc,
            now=True  # Send immediately
        )

def send_error_to_control(doc):
    """
    The background job that makes the actual API call to the control panel.
    """
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            # Silently fail if the tenant is not configured to talk to the control panel
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.report_tenant_error"

        headers = {"X-Rokct-Secret": api_secret}
        data = {"error_details": doc.as_json()}

        requests.post(api_url, headers=headers, json=data)
        # We don't check the response, this is a "fire and forget" operation.
        # If it fails, the control panel will log its own error, and we avoid an infinite loop.

    except Exception:
        # We log the failure to the local error log, but we don't re-throw
        # to prevent a potential infinite loop of error reporting.
        frappe.log_error(frappe.get_traceback(), "Failed to forward error to control panel")


@frappe.whitelist()
def record_token_usage(tokens_used: int, model_name: str = "flash"):
    """
    Records usage against the User doctype custom fields, split by model type.
    """
    if frappe.conf.get("app_role") != "tenant":
        # Allow recording on Control Panel without sync, or just pass silently.
        # Assuming control users are unlimited/untracked or handled locally.
        return {"status": "success"}

    try:
        _ensure_custom_fields_exist()
        subscription_details = get_subscription_details()
        is_per_seat_plan = subscription_details.get("is_per_seat_plan", 0)
        tracker_user = frappe.session.user if is_per_seat_plan else "Administrator"

        user_doc = frappe.get_doc("User", tracker_user)

        # Daily Reset Logic
        if str(user_doc.last_token_date) != nowdate():
            user_doc.daily_token_usage = 0
            user_doc.daily_pro_usage = 0
            user_doc.daily_flash_usage = 0
            user_doc.last_token_date = nowdate()

        # Total aggregation
        user_doc.daily_token_usage = (user_doc.daily_token_usage or 0) + tokens_used
        user_doc.monthly_token_usage = (user_doc.monthly_token_usage or 0) + tokens_used

        # Split aggregation
        # Split aggregation
        # We check for "pro" keyword which covers "gemini-3-pro" or "gemini-1.5-pro"
        # Everything else (including "flash", "gemini-2.5-flash", "gemini-1.5-flash") counts as Flash.
        if "pro" in model_name.lower() and "flash" not in model_name.lower():
             user_doc.daily_pro_usage = (user_doc.daily_pro_usage or 0) + tokens_used
        else:
             user_doc.daily_flash_usage = (user_doc.daily_flash_usage or 0) + tokens_used

        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Sync to Control Panel
        frappe.enqueue(
            "control.control.tenant.api.sync_usage_to_control",
            queue="short",
            tokens_used=tokens_used,
            model_name=model_name
        )

        return {"status": "success"}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Token Usage Recording Failed")
        raise

@frappe.whitelist()
def get_token_usage():
    """
    Returns usage breakdown for Pro and Flash.
    """
    is_tenant = frappe.conf.get("app_role") == "tenant"

    if not is_tenant:
        # Mock unlimited for Control Panel / Dev
        return {
            "daily_pro_limit": -1,
            "daily_pro_remaining": 999999,
            "daily_flash_limit": -1,
            "daily_flash_remaining": 999999,
            "is_pro_unlimited": True,
            "is_flash_unlimited": True,
            "seat_limit_exceeded": False
        }

    try:
        _ensure_custom_fields_exist()
        subscription_details = get_subscription_details()
        monthly_limit = subscription_details.get("monthly_token_limit", 0) # Base/Flash Limit
        monthly_paid_limit = subscription_details.get("monthly_paid_token_limit", 0) # Pro Limit
        is_per_seat_plan = subscription_details.get("is_per_seat_plan", 0)

        # Seat Assignment Logic
        seat_limit_exceeded = False
        if is_per_seat_plan:
            current_user = frappe.session.user
            if frappe.db.exists("User", current_user):
                user_val = frappe.db.get_value("User", current_user, "ai_seat_assigned")
                if not user_val:
                    # Not assigned, try to assign
                    user_quantity = subscription_details.get("user_quantity", 0) or 0
                    base_user_count = subscription_details.get("base_user_count", 0) or 0
                    limit = max(user_quantity, base_user_count)

                    used_seats = frappe.db.count("User", filters={"ai_seat_assigned": 1})

                    if used_seats < limit:
                        # Auto-assign
                        frappe.db.set_value("User", current_user, "ai_seat_assigned", 1)
                        frappe.db.commit()
                    else:
                        seat_limit_exceeded = True

        # Calculate daily limits
        daily_flash_limit = monthly_limit // 30 if monthly_limit > 0 else 0
        daily_pro_limit = monthly_paid_limit // 30 if monthly_paid_limit > 0 else 0

        tracker_user = frappe.session.user if is_per_seat_plan else "Administrator"

        daily_pro_usage = 0
        daily_flash_usage = 0

        if frappe.db.exists("User", tracker_user):
            user_doc = frappe.get_doc("User", tracker_user)
            if str(user_doc.last_token_date) != nowdate():
                daily_pro_usage = 0
                daily_flash_usage = 0
            else:
                daily_pro_usage = user_doc.daily_pro_usage or 0
                daily_flash_usage = user_doc.daily_flash_usage or 0

        daily_pro_remaining = daily_pro_limit - daily_pro_usage if daily_pro_limit > 0 else -1
        daily_flash_remaining = daily_flash_limit - daily_flash_usage if daily_flash_limit > 0 else -1

        return {
            "daily_pro_limit": daily_pro_limit,
            "daily_pro_remaining": daily_pro_remaining,
            "daily_flash_limit": daily_flash_limit,
            "daily_flash_remaining": daily_flash_remaining,
            "is_pro_unlimited": monthly_paid_limit == 0,
            "is_flash_unlimited": monthly_limit == 0,
            "seat_limit_exceeded": seat_limit_exceeded
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Token Usage Failed")
        return {
            "daily_flash_remaining": 0,
            "is_flash_unlimited": False
        }

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
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.report_token_usage_to_control"

        headers = {"X-Rokct-Secret": api_secret}
        data = {"tokens_used": tokens_used, "model_name": model_name}

        requests.post(api_url, headers=headers, json=data)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sync Usage to Control Failed")

def _notify_control_of_verification():
    """Makes a secure backend call to the control panel to mark the subscription as verified."""
    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            frappe.log_error("Tenant site is not configured to communicate with the control panel.", "Verification Notification Error")
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.mark_subscription_as_verified"

        headers = {"X-Rokct-Secret": api_secret}
        # The site name is implicitly sent via the request's Host header,
        # which the control panel will use to identify the subscription.
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        if response_json.get("status") != "success":
            frappe.log_error(f"Failed to notify control panel of verification. Response: {response_json}", "Verification Notification Error")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Verification Notification Failed")


def initial_setup(email, password, first_name, last_name, company_name, api_secret, control_plane_url, currency, country, verification_token, login_redirect_url, financial_year_begins_on):
    """
    Sets up the first user and company.
    This is called by the control panel during provisioning.
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
            frappe.throw(f"Parameter '{param_name}' is missing or empty.", title="Missing Information")

    if login_redirect_url is None:
        frappe.throw("The 'login_redirect_url' parameter must be provided, even if it's an empty string.", title="Missing Information")

    try:
        validate_email_address(email, throw=True)
    except frappe.exceptions.ValidationError:
        frappe.throw("You must provide a valid email address.", title="Invalid Email")

    if len(password) < 8:
        frappe.throw("Password must be at least 8 characters long.", title="Weak Password")

    print(f"--- ROKCT DEBUG: Attempting to create user {email} with password: {password} ---")

    # The security check is only relevant in an HTTP context.
    # When run via `bench execute`, `frappe.local.request` does not exist.
    if hasattr(frappe.local, "request"):
        received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
        if not received_secret:
            frappe.throw("Missing X-Rokct-Secret header.", frappe.AuthenticationError)
        if received_secret != api_secret:
            frappe.throw("Authentication failed. Secrets do not match.", frappe.AuthenticationError)

    # --- End Validation ---

    try:
        # Store control panel details for future communication
        # Manually update site_config.json to bypass potential framework init issues.
        site_config_path = frappe.get_site_path("site_config.json")
        with open(site_config_path, "r") as f:
            site_config = json.load(f)

        site_config["api_secret"] = api_secret
        site_config["control_plane_url"] = control_plane_url

        with open(site_config_path, "w") as f:
            json.dump(site_config, f, indent=4)

        # The Company creation hook requires this Warehouse Type to exist.
        if not frappe.db.exists("Warehouse Type", "Transit"):
            frappe.get_doc({"doctype": "Warehouse Type", "name": "Transit"}).insert(ignore_permissions=True)

        # Create the new company for the tenant, or get it if it already exists.
        if frappe.db.exists("Company", company_name):
            company = frappe.get_doc("Company", company_name)
        else:
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": currency,
                "country": country,
                "is_group": 0,
                "chart_of_accounts": "Standard with Numbers"
            })
            company.insert(ignore_permissions=True)

        # Create a Fiscal Year for the new company
        year = getdate(financial_year_begins_on).year
        year_name = f"FY {year}"
        year_start_date = getdate(financial_year_begins_on)
        year_end_date = add_days(year_start_date, 364)

        if not frappe.db.exists("Fiscal Year", year_name):
            frappe.get_doc({
                "doctype": "Fiscal Year",
                "year": year_name,
                "year_start_date": year_start_date,
                "year_end_date": year_end_date,
            }).insert(ignore_permissions=True)

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
            frappe.log_error(f"Could not determine timezone for country {country}", "Timezone Lookup Failed")

        # Create the first user and link them to the company in a single operation.
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "time_zone": time_zone,
            "onboarding_status": frappe.as_json({}),  # Mark onboarding as complete
            "send_welcome_email": 0, # The control plane will send the welcome email
            "email_verification_token": verification_token, # Use token from control panel
            "user_companies": [{
                "company": company.name,
                "is_default": 1
            }]
        })
        user.set("new_password", password)
        try:
            user.insert(ignore_permissions=True)
        except frappe.DuplicateEntryError:
            # This can happen on a retry if the user was created but the overall
            # transaction failed later.
            frappe.log_error(f"Initial setup called for existing user {email}", "Tenant Initial Setup Warning")
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
        return {"status": "success", "message": "Initial user and company setup complete."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Tenant Initial Setup Failed")
        frappe.throw(f"An error occurred during initial setup: {e}")

@frappe.whitelist(allow_guest=True)
def verify_my_email(token):
    """
    Verify a user's email address using a token from their welcome email.
    """
    if not token:
        frappe.respond_as_web_page("Invalid Link", "The verification link is missing a token.", indicator_color='red')
        return

    user = frappe.db.get_value("User", {"email_verification_token": token}, ["name", "enabled"])
    if not user:
        frappe.respond_as_web_page("Invalid Link", "This verification link is invalid or has already been used.", indicator_color='red')
        return

    if not user.enabled:
        frappe.respond_as_web_page("Account Disabled", "Your account has been disabled. Please contact support.", indicator_color='red')
        return

    user_doc = frappe.get_doc("User", user.name)
    user_doc.email_verification_token = None  # Invalidate the token
    user_doc.email_verified_at = frappe.utils.now_datetime()  # Set verification timestamp
    user_doc.save(ignore_permissions=True)

    # This is a fire-and-forget call. We don't need to block the user's
    # experience waiting for the response. The control panel will handle it.
    frappe.enqueue(_notify_control_of_verification, queue="short")

    frappe.db.commit()

    frappe.respond_as_web_page(
        "Email Verified!",
        "Thank you for verifying your email address. You can now log in to your account.",
        indicator_color='green'
    )


@frappe.whitelist()
def resend_verification_email(email: str):
    """
    Resends the verification email for a given user.
    Can be called by the user themselves or a System Manager.
    """
    # Security: Ensure the logged-in user is the one requesting the resend, or is an admin.
    if frappe.session.user != email and "System Manager" not in frappe.get_roles():
        frappe.throw("You are not authorized to perform this action for another user.", frappe.PermissionError)

    try:
        user = frappe.get_doc("User", email)
        if user.email_verified_at:
            return {"status": "success", "message": "Email is already verified."}

        # Generate and store a new verification token
        token = frappe.generate_hash(length=48)
        user.email_verification_token = token
        user.save(ignore_permissions=True)

        # Get company name for email context
        default_company_link = next((d for d in user.user_companies if d.is_default), None)
        company_name = default_company_link.company if default_company_link else "Your Company"

        # Prepare context and send the email
        verification_url = get_url(f"/api/method/rcore.tenant.api.verify_my_email?token={token}")
        email_context = {
            "first_name": user.first_name,
            "company_name": company_name,
            "verification_url": verification_url
        }
        send_tenant_email(
            recipients=[user.email],
            template="Resend Verification",
            args=email_context,
            now=True
        )
        frappe.db.commit()
        return {"status": "success", "message": "Verification email sent."}
    except frappe.DoesNotExistError:
        return {"status": "error", "message": "User not found."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Resend Verification Email Failed")
        frappe.throw(f"An error occurred while resending the verification email: {e}")

@frappe.whitelist()
def get_visions():
    return frappe.get_all("Vision", fields=["name", "title", "description"])

@frappe.whitelist()
def get_pillars():
    return frappe.get_all("Pillar", fields=["name", "title", "description", "vision"])

@frappe.whitelist()
def get_strategic_objectives():
    return frappe.get_all("Strategic Objective", fields=["name", "title", "description", "pillar"])

@frappe.whitelist()
def get_kpis():
    return frappe.get_all("KPI", fields=["name", "title", "description", "strategic_objective"])

@frappe.whitelist()
def get_plan_on_a_page():
    return frappe.get_doc("Plan On A Page")

@frappe.whitelist()
def get_personal_mastery_goals():
    return frappe.get_all("Personal Mastery Goal", fields=["name", "title", "description"])

@frappe.whitelist()
def create_temporary_support_user(agent_id: str, reason: str, support_email_domain: str):
    """
    Creates a temporary support user with a descriptive name and System Manager role.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    # --- Authentication/Authorization ---
    api_secret = frappe.conf.get("api_secret")
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
    if not api_secret or not received_secret:
        frappe.throw("Authentication failed: Missing credentials.", frappe.AuthenticationError)
    if received_secret != api_secret:
        frappe.throw("Authentication failed: Invalid credentials.", frappe.AuthenticationError)
    # --- End Authentication ---

    # --- Input Validation ---
    if not all([agent_id, reason, support_email_domain]):
        frappe.throw("Agent ID, Reason, and Support Email Domain are required.", title="Missing Information")
    # --- End Validation ---

    try:
        # Construct a descriptive email for better audit trails
        support_email = f"support-{agent_id}-{reason}@{support_email_domain}"
        temp_password = frappe.generate_hash(length=16)

        # Check if this exact user already exists (e.g., from a failed previous run)
        if frappe.db.exists("User", support_email):
            frappe.delete_doc("User", support_email, force=True, ignore_permissions=True)


        user = frappe.get_doc({
            "doctype": "User",
            "email": support_email,
            "first_name": "ROKCT Support",
            "last_name": f"({reason})",
            "send_welcome_email": 0,
            "temporary_user_expires_on": frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=24)
        })
        user.set("new_password", temp_password)
        user.insert(ignore_permissions=True)
        user.add_roles("System Manager")

        # Log this significant security event to the brain
        frappe.call(
            "brain.api.record_event",
            message=f"Temporary support access granted to agent '{agent_id}' for reason: {reason}. User account '{support_email}' created.",
            reference_doctype="User",
            reference_name="Administrator"
        )

        frappe.db.commit()
        return {"status": "success", "message": {"email": support_email, "password": temp_password}}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Temporary Support User Creation Failed")
        frappe.throw(f"An error occurred during temporary user creation: {e}")

@frappe.whitelist()
def disable_temporary_support_user(support_user_email):
    """
    Disables a temporary support user account.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    # --- Input Validation ---
    if not support_user_email:
        frappe.throw("Support User Email is required.", title="Missing Information")
    try:
        validate_email_address(support_user_email, throw=True)
    except frappe.exceptions.ValidationError:
        frappe.throw("You must provide a valid email address.", title="Invalid Email")
    # --- End Validation ---

    api_secret = frappe.conf.get("api_secret")
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")

    if not api_secret or not received_secret:
        frappe.throw("Authentication failed: Missing credentials.", frappe.AuthenticationError)

    if received_secret != api_secret:
        frappe.throw("Authentication failed: Invalid credentials.", frappe.AuthenticationError)

    try:
        if not frappe.db.exists("User", support_user_email):
            return {"status": "success", "message": "User already does not exist."}

        user = frappe.get_doc("User", support_user_email)
        user.enabled = 0
        user.save(ignore_permissions=True)

        # Log this significant security event to the brain
        frappe.call(
            "brain.api.record_event",
            message=f"Temporary support access for user account '{support_user_email}' was revoked.",
            reference_doctype="User",
            reference_name="Administrator"
        )

        frappe.db.commit()
        return {"status": "success", "message": f"Support user {support_user_email} has been disabled."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), f"Failed to disable support user {support_user_email}")
        frappe.throw(f"An error occurred while disabling the support user: {e}")

@frappe.whitelist()
def create_sales_invoice(invoice_data, recurring=False, frequency=None, end_date=None):
    """
    Creates a new Sales Invoice and, optionally, sets up a recurring schedule for it.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    # --- Input Validation ---
    if not isinstance(invoice_data, dict) or not invoice_data.get("customer") or not invoice_data.get("items"):
        frappe.throw("`invoice_data` must be a dictionary containing at least 'customer' and 'items'.", title="Invalid Input")

    if recurring:
        if not frequency or not end_date:
            frappe.throw("`frequency` and `end_date` are required for recurring invoices.", title="Missing Information")
        allowed_frequencies = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-yearly", "Yearly"]
        if frequency not in allowed_frequencies:
            frappe.throw(f"Invalid frequency. Must be one of {', '.join(allowed_frequencies)}.", title="Invalid Input")
    # --- End Validation ---

    try:
        invoice_doc = frappe.get_doc(invoice_data)
        invoice_doc.insert(ignore_permissions=False)
        invoice_doc.submit()

        response_data = {"invoice_name": invoice_doc.name}
        if recurring:
            auto_repeat = frappe.get_doc({
                "doctype": "Auto Repeat", "reference_doctype": "Sales Invoice", "reference_document": invoice_doc.name,
                "frequency": frequency, "end_date": end_date
            }).insert(ignore_permissions=False)
            auto_repeat.submit()
            response_data["auto_repeat_name"] = auto_repeat.name
            response_data["message"] = f"Sales Invoice {invoice_doc.name} created and scheduled for recurring generation."
        else:
            response_data["message"] = f"Sales Invoice {invoice_doc.name} created successfully."

        frappe.db.commit()
        return response_data

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Failed to create Sales Invoice")
        frappe.throw(f"An error occurred while creating the Sales Invoice: {e}")

@frappe.whitelist()
def log_frontend_error(error_message, context=None):
    """
    Logs an error from the frontend to the backend, now integrated with the Brain module.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    if not error_message or not isinstance(error_message, str) or not error_message.strip():
        return {"status": "error", "message": "error_message must be a non-empty string."}

    try:
        # Default document to link the error to is the user's profile
        reference_doctype = "User"
        reference_name = frappe.session.user

        # Construct a more descriptive message for the brain
        brain_message = f"Frontend Error: {error_message}"

        if context:
            try:
                context_data = json.loads(context)
                if isinstance(context_data, dict):
                    # If the context provides a more specific document, use it
                    reference_doctype = context_data.get("doctype", reference_doctype)
                    reference_name = context_data.get("name", reference_name)

                    url = context_data.get("url")
                    if url:
                        brain_message += f" at URL: {url}"
            except json.JSONDecodeError:
                # If context is not valid JSON, just append it to the message
                brain_message += f" | Context: {context}"

        # Call the brain's API to record the event
        frappe.call(
            "brain.api.record_event",
            message=brain_message,
            reference_doctype=reference_doctype,
            reference_name=reference_name
        )

        return {"status": "success", "message": "Error logged successfully."}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Failed to log frontend error")
        return {"status": "error", "message": "Failed to log error to backend."}

@frappe.whitelist()
def get_subscription_details():
    """
    A secure proxy API for the frontend to get subscription details.
    Caches the response from the control panel.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    cached_details = frappe.cache().get_value("subscription_details")
    if cached_details:
        return cached_details

    try:
        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            frappe.log_error("Tenant site is not configured to communicate with the control panel.", "Proxy API Error")
            frappe.throw("Platform communication is not configured.", title="Configuration Error")

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.get_subscription_status"

        headers = {"X-Rokct-Secret": api_secret}
        response = requests.post(api_url, headers=headers)
        response.raise_for_status()
        response_json = response.json()

        details = response_json.get("message")
        if details and isinstance(details, dict):
            cache_duration_seconds = details.get("subscription_cache_duration", 86400)
            frappe.cache().set_value("subscription_details", details, expires_in_sec=cache_duration_seconds)

        return details

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Subscription Details Proxy Failed")
        # On failure, it's better to return a clear error than to let the frontend hang
        frappe.throw("An error occurred while fetching subscription details.")


@frappe.whitelist()
def save_email_settings(settings: dict):
    """
    Saves the tenant's custom email settings.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw("You are not authorized to perform this action.", frappe.PermissionError)

@frappe.whitelist()
def set_platform_secret(secret: str):
    """
    Sets the Platform Sync Secret in the site config.
    Called by Next.js upon Tenant Admin login.
    """
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Only System Managers can set the Platform Secret.", frappe.PermissionError)
    
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


    if not isinstance(settings, dict):
        frappe.throw("Settings must be a dictionary.", frappe.ValidationError)

    try:
        doc = frappe.get_doc("Tenant Email Settings")
        doc.update(settings)
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Email settings saved successfully."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Failed to save email settings")
        frappe.throw(f"An error occurred while saving email settings: {e}")


@frappe.whitelist()
def get_welcome_email_details():
    """
    Returns the details needed to send a welcome email to the primary user.
    This is called by the control panel.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    # --- Authentication/Authorization ---
    api_secret = frappe.conf.get("api_secret")
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
    if not api_secret or not received_secret:
        frappe.throw("Authentication failed: Missing credentials.", frappe.AuthenticationError)
    if received_secret != api_secret:
        frappe.throw("Authentication failed: Invalid credentials.", frappe.AuthenticationError)
    # --- End Authentication ---

    try:
        # Find the first user who is a System Manager
        system_managers = frappe.get_all("User", filters={"role_profile_name": "System Manager", "enabled": 1}, fields=["name", "first_name", "email", "email_verification_token"], order_by="creation asc", limit=1)
        if not system_managers:
            frappe.throw("No primary user found to send welcome email to.", title="User Not Found")

        user = system_managers[0]

        return {
            "email": user.email,
            "first_name": user.first_name,
            "email_verification_token": user.email_verification_token
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Failed to get welcome email details")
        frappe.throw(f"An error occurred while getting welcome email details: {e}")

@frappe.whitelist()
def update_verification_token(email, token):
    """
    Updates the verification token for a given user.
    This is called by the control panel before resending a welcome email.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    # --- Authentication/Authorization ---
    api_secret = frappe.conf.get("api_secret")
    received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
    if not api_secret or not received_secret:
        frappe.throw("Authentication failed: Missing credentials.", frappe.AuthenticationError)
    if received_secret != api_secret:
        frappe.throw("Authentication failed: Invalid credentials.", frappe.AuthenticationError)
    # --- End Authentication ---

    try:
        user = frappe.get_doc("User", email)
        user.email_verification_token = token
        user.save(ignore_permissions=True)
        frappe.db.commit()
        return {"status": "success", "message": "Verification token updated."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Update Verification Token Failed")
        frappe.throw(f"An error occurred while updating the verification token: {e}")

@frappe.whitelist()
def update_fiscal_year_if_default(start_date):
    """
    Updates the default fiscal year for the site's company, but only if the
    current fiscal year is the old, incorrect default (starting on Jan 1st).
    This is a protected API meant to be called by the control panel during an update.
    """
    # --- Security Check ---
    # This function is intended to be called via `bench execute` from the control panel.
    # In this context, there are no request headers. The security is implicit because
    # only an admin with shell access to the control panel can trigger the master script.
    if hasattr(frappe.local, "request"):
        api_secret = frappe.conf.get("api_secret")
        received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
        if not received_secret or received_secret != api_secret:
            frappe.throw("Authentication failed.", frappe.AuthenticationError)

    if not start_date:
        frappe.throw("`start_date` is a required parameter.", title="Missing Information")

    try:
        # 1. Get the default company for the site.
        company_name = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company_name:
            return {"status": "skipped", "message": "No default company set for this site."}

        company = frappe.get_doc("Company", company_name)
        current_fiscal_year_name = company.default_fiscal_year

        if not current_fiscal_year_name:
            return {"status": "skipped", "message": f"Company '{company_name}' has no default fiscal year set."}

        # 2. Check the start date of the current fiscal year.
        current_fy_doc = frappe.get_doc("Fiscal Year", current_fiscal_year_name)
        print(f"DEBUG: Current fiscal year is '{current_fiscal_year_name}' with start date {current_fy_doc.year_start_date}")

        # We identify the old, incorrect default by checking if the start date is January 1st.
        if current_fy_doc.year_start_date.month == 1 and current_fy_doc.year_start_date.day == 1:
            print(f"INFO: Current fiscal year starts on January 1st. Proceeding with correction.")
            # 3. Create the new, correct fiscal year.
            new_start_date = getdate(start_date)
            new_year = new_start_date.year
            new_year_name = f"FY {new_year}"
            new_year_end_date = add_days(new_start_date, 364)

            if not frappe.db.exists("Fiscal Year", new_year_name):
                frappe.get_doc({
                    "doctype": "Fiscal Year",
                    "year": new_year_name,
                    "year_start_date": new_start_date,
                    "year_end_date": new_year_end_date,
                }).insert(ignore_permissions=True)
                message = f"Created new fiscal year '{new_year_name}'."
            else:
                message = f"Fiscal year '{new_year_name}' already exists."

            # 4. Set the new fiscal year as the default.
            company.default_fiscal_year = new_year_name
            company.save(ignore_permissions=True)
            frappe.db.commit()

            return {"status": "success", "message": f"{message} Set '{new_year_name}' as default for company '{company_name}'."}
        else:
            # The start date is not Jan 1st, so we assume the tenant has customized it.
            return {"status": "skipped", "message": f"Fiscal year for '{company_name}' was not the default. No changes made."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Fiscal Year Correction Failed")
        raise


@frappe.whitelist()
def complete_onboarding():
    """
    Marks the onboarding process as complete for the user's default company.
    This is intended to be called by the frontend after the initial user setup.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw("This action can only be performed on a tenant site.", title="Action Not Allowed")

    try:
        user = frappe.get_doc("User", frappe.session.user)
        default_company_link = next((d for d in user.user_companies if d.is_default), None)

        if not default_company_link:
            frappe.throw("No default company found for the current user.", title="Not Found")

        company_name = default_company_link.company
        company = frappe.get_doc("Company", company_name)

        if not company.onboarding_complete:
            company.onboarding_complete = 1
            company.save(ignore_permissions=True)
            frappe.db.commit()
            return {"status": "success", "message": f"Onboarding marked as complete for {company_name}."}
        else:
            return {"status": "success", "message": "Onboarding was already complete."}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Complete Onboarding Failed")
        frappe.throw(f"An error occurred while marking onboarding as complete: {e}")


@frappe.whitelist()
def get_weather(location: str):
    """
    Proxy endpoint to get weather data from the control site, with tenant-side caching.
    This follows the same authentication pattern as other tenant-to-control-panel APIs.
    """
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
        frappe.log_error("Tenant site is not configured to communicate with the control panel.", "Weather Proxy Error")
        frappe.throw("Platform communication is not configured.", title="Configuration Error")

    # Construct the secure API call
    scheme = frappe.conf.get("control_plane_scheme", "https")
    api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.get_weather"
    headers = {
        "X-Rokct-Secret": api_secret,
        "Accept": "application/json"
    }

    try:
        # Use frappe.make_get_request which is a wrapper around requests
        # and handles logging and exceptions in a standard way.
        response = frappe.make_get_request(api_url, headers=headers, params={"location": location})

        # Cache the successful response for 10 minutes on the tenant site
        frappe.cache().set_value(cache_key, response, expires_in_sec=600)

        return response

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Weather Proxy API Error")
        frappe.throw(f"An error occurred while fetching weather data from the control plane: {e}")

@frappe.whitelist()
def set_weather_alias(original, corrected):
    """
    Proxy endpoint to teach the Control Plane a weather alias.
    Ensures that learnings are centralized and shared (Global Brain).
    """
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
    headers = {
        "X-Rokct-Secret": api_secret,
        "Accept": "application/json"
    }
    
    # We use POST for state-changing operations
    try:
        response = frappe.make_post_request(api_url, headers=headers, data={"original": original, "corrected": corrected})
        return response
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Weather Alias Proxy Error")
        frappe.throw(f"Failed to sync alias to Global Brain: {e}")
