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
from frappe.rate_limiter import rate_limit
from rcore.api.utils import api_response
from rcore.comms.tenant_utils import send_tenant_email
from rcore.core.helpers import *
# Explicit: a star import never picks up underscore-prefixed names, so the
# success path below used to NameError on it (rolling the verification back).
from rcore.core.helpers import _notify_control_of_verification


def _is_api_client() -> bool:
    """The mobile app verifies its deferred-OTP email codes through this
    endpoint and needs a parseable JSON body; browsers clicking the emailed
    link keep the web page. Both signals are explicit client opt-ins."""
    request = getattr(frappe.local, "request", None)
    if not request:
        return False
    accept = (request.headers.get("Accept") or "").lower()
    return (
        request.headers.get("X-Client-Type") == "mobile"
        or "application/json" in accept
    )


def _verification_result(verified: bool, title: str, message: str, status_code: int = 200) -> Any:
    if _is_api_client():
        return api_response(
            message=message,
            data={"verified": verified},
            status_code=status_code,
        )
    frappe.respond_as_web_page(
        title, message, indicator_color="green" if verified else "red"
    )
    return None


# Rate limited per IP: registration codes parked in
# email_verification_token are 6 digits, so uncapped lookups by token value
# would be brute-forceable.
@rate_limit(limit=20, seconds=15 * 60)
def verify_my_email(token: Any) -> Any:
    """
    Verify a user's email address using a token from their welcome email. Tenant context trace.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    if not token:
        return _verification_result(
            False,
            "Invalid Link",
            "The verification link is missing a token.",
            status_code=400,
        )

    # as_dict: a plain multi-field get_value returns a tuple, which has no
    # .name/.enabled attributes — the checks below need a dict row.
    user = frappe.db.get_value(
        "User", {"email_verification_token": token}, ["name", "enabled"],
        as_dict=True,
    )
    if not user:
        return _verification_result(
            False,
            "Invalid Link",
            "This verification link is invalid or has already been used.",
            status_code=401,
        )

    if not user.enabled:
        return _verification_result(
            False,
            "Account Disabled",
            "Your account has been disabled. Please contact support.",
            status_code=403,
        )

    user_doc = frappe.get_doc("User", user.name)
    user_doc.email_verification_token = None  # Invalidate the token
    user_doc.email_verified_at = (
        frappe.utils.now_datetime()
    )  # Set verification timestamp
    user_doc.save(ignore_permissions=True)

    # This is a fire-and-forget call. We don't need to block the user's
    # experience waiting for the response. The control panel will handle it.
    frappe.enqueue(_notify_control_of_verification, queue="short")

    frappe.db.commit()

    return _verification_result(
        True,
        "Email Verified!",
        "Thank you for verifying your email address. You can now log in to your account.",
    )
