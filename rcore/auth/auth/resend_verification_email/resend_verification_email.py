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
from rcore.core.helpers import *


def resend_verification_email(email: str) -> Any:
    """
    Resends the verification email for a given user. Tenant context trace.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    # Security: Ensure the logged-in user is the one requesting the resend, or
    # is an admin.
    if frappe.session.user != email and "System Manager" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to perform this action for another user.",
            frappe.PermissionError,
        )

    try:
        user = frappe.get_doc("User", email)
        if user.email_verified_at:
            return {"status": "success", "message": "Email is already verified."}

        # Generate and store a new verification token
        token = frappe.generate_hash(length=48)
        user.email_verification_token = token
        user.save(ignore_permissions=True)

        # Get company name for email context
        default_company_link = next(
            (d for d in user.user_companies if d.is_default), None
        )
        company_name = (
            default_company_link.company if default_company_link else "Your Company"
        )

        # Prepare context and send the email
        verification_url = get_url(
            f"/api/method/rcore.auth.verify_my_email.verify_my_email?token={token}"
        )
        email_context = {
            "first_name": user.first_name,
            "company_name": company_name,
            "verification_url": verification_url,
        }
        send_tenant_email(
            recipients=[user.email],
            template="Resend Verification",
            args=email_context,
            now=True,
        )
        frappe.db.commit()
        return {"status": "success", "message": "Verification email sent."}
    except frappe.DoesNotExistError:
        return {"status": "error", "message": "User not found."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Resend Verification Email Failed")
        frappe.throw(f"An error occurred while resending the verification email: {e}")
