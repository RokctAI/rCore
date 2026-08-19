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


@frappe.whitelist()
def record_token_usage(tokens_used: int, model_name: str='flash') -> Any:
    """
    Records usage against the User doctype custom fields, split by model type. Tenant context trace.
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
        # Everything else (including "flash", "gemini-2.5-flash",
        # "gemini-1.5-flash") counts as Flash.
        if "pro" in model_name.lower() and "flash" not in model_name.lower():
            user_doc.daily_pro_usage = (user_doc.daily_pro_usage or 0) + tokens_used
        else:
            user_doc.daily_flash_usage = (user_doc.daily_flash_usage or 0) + tokens_used

        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

        # Sync to Control Panel
        frappe.enqueue(
            "rcore.subscriptions.sync_usage_to_control.sync_usage_to_control",
            queue="short",
            tokens_used=tokens_used,
            model_name=model_name,
        )

        return {"status": "success"}

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Token Usage Recording Failed")
        raise
