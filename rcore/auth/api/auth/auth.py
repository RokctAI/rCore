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

import frappe
from frappe.utils.password import check_password
from frappe.utils import now_datetime

def validate(request=None):
    """
    Custom authentication hook to support 'Bearer <api_key>:<api_secret>'
    with token expiry check.
    """
    auth_header = frappe.get_request_header("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1].strip()
        if ":" in token:
            try:
                api_key, api_secret = token.split(":")
                user_doc = frappe.db.get_value(
                    "User", {"api_key": api_key}, ["name", "custom_token_expiry"], as_dict=True
                )
                if user_doc:
                    user_name = user_doc.name
                    expiry = user_doc.custom_token_expiry
                    
                    # Check if token has expired
                    if expiry and now_datetime() > expiry:
                        return None # Token expired
                        
                    if check_password(user_name, api_secret):
                        frappe.set_user(user_name)
                        return user_name
            except Exception:
                pass
    return None


@frappe.whitelist(allow_guest=True)
def refresh(refresh_token: str) -> dict:
    """
    Rotates the access token using a valid refresh token.
    """
    from frappe.utils import add_to_date
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

