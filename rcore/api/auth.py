# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe
from frappe.auth import LoginManager


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    """
    Standard Login endpoint that returns API Keys.
    Can be used on both Control Panel and Tenant sites.
    """
    try:
        login_manager = LoginManager()

        # Smart Auth: Resolve Email to Username (for Administrator)
        if "@" in usr:
            user_name = frappe.db.get_value("User", {"email": usr}, "name")
            if user_name:
                usr = user_name

        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()

        user = frappe.get_doc("User", usr)

        # Generate API keys if missing
        api_secret = None
        if not user.api_key:
            api_secret = frappe.generate_hash(length=15)
            user.api_key = frappe.generate_hash(length=15)
            user.api_secret = api_secret
            user.save(ignore_permissions=True)
        else:
            # If keys exist, we cannot retrieve the secret.
            # We must regenerate them to provide a valid token.
            # WARNING: This invalidates previous sessions using the old key.
            api_secret = frappe.generate_hash(length=15)
            user.api_key = frappe.generate_hash(length=15)
            user.api_secret = api_secret
            user.save(ignore_permissions=True)

        # Self-Healing: Ensure System Users have System Manager role
        user_roles = frappe.get_roles(user.name)
        if user.user_type == "System User" and "System Manager" not in user_roles:
            user.add_roles("System Manager")
            user_roles = frappe.get_roles(user.name)  # Refresh roles

        # Determine Primary Role for Frontend Logic
        primary_role = "user"
        if "Administrator" in user_roles:
            primary_role = "Administrator"
        elif "System Manager" in user_roles:
            primary_role = "System Manager"
        elif user.user_type == "System User":
            primary_role = "System Manager"

        token = f"{user.api_key}:{api_secret}"

        return {
            "status": True,
            "message": "Logged In",
            "data": {
                "access_token": token,
                "token_type": "Bearer",
                "user": {
                    "id": user.name,
                    "email": user.email,
                    "firstname": user.first_name,
                    "lastname": user.last_name,
                    "phone": getattr(
                        user,
                        "phone",
                        None) or getattr(
                        user,
                        "mobile_no",
                        None),
                    "role": primary_role,
                    "active": 1,
                    "img": getattr(
                        user,
                        "user_image",
                        None),
                    "home_page": getattr(
                        user,
                        "home_page",
                        None) or "/app"}}}

    except frappe.AuthenticationError:
        frappe.log_error(
            "Authentication Failure for user: " +
            str(usr),
            "Login API Auth Error")
        return {"status": False, "message": "Invalid credentials"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Login API System Error")
        return {"status": False, "message": f"Login Error: {str(e)}"}
