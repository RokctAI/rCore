import frappe
from frappe.utils import now_datetime, add_to_date

@frappe.whitelist(allow_guest=True)
def refresh(refresh_token: str) -> dict:
    """
    Rotates the access token using a valid refresh token.
    """
    try:
        # Find user with this refresh token
        user_name = frappe.db.get_value("User", {"custom_refresh_token": refresh_token}, "name")
        
        if not user_name:
            return {"status": False, "message": "Invalid refresh token"}

        # Generate new access tokens
        new_api_secret = frappe.generate_hash(length=15)
        new_api_key = frappe.generate_hash(length=15)
        new_refresh_token = frappe.generate_hash(length=32)
        new_expiry_date = add_to_date(now_datetime(), hours=24)

        # Update User
        frappe.db.set_value(
            "User",
            user_name,
            {
                "api_key": new_api_key,
                "api_secret": new_api_secret,
                "custom_refresh_token": new_refresh_token,
                "custom_token_expiry": new_expiry_date
            },
            update_modified=False,
        )

        return {
            "status": True,
            "message": "Token rotated successfully",
            "data": {
                "access_token": f"{new_api_key}:{new_api_secret}",
                "refresh_token": new_refresh_token,
                "expires_at": new_expiry_date,
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Token Refresh Error")
        return {"status": False, "message": f"Refresh failed: {str(e)}"}
