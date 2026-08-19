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
def get_token_usage() -> Any:
    """
    Returns usage breakdown for Pro and Flash. Tenant context trace.
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
            "seat_limit_exceeded": False,
        }

    try:
        _ensure_custom_fields_exist()
        subscription_details = get_subscription_details()
        monthly_limit = subscription_details.get(
            "monthly_token_limit", 0
        )  # Base/Flash Limit
        monthly_paid_limit = subscription_details.get(
            "monthly_paid_token_limit", 0
        )  # Pro Limit
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
                    base_user_count = (
                        subscription_details.get("base_user_count", 0) or 0
                    )
                    limit = max(user_quantity, base_user_count)

                    used_seats = frappe.db.count(
                        "User", filters={"ai_seat_assigned": 1}
                    )

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

        daily_pro_remaining = (
            daily_pro_limit - daily_pro_usage if daily_pro_limit > 0 else -1
        )
        daily_flash_remaining = (
            daily_flash_limit - daily_flash_usage if daily_flash_limit > 0 else -1
        )

        return {
            "daily_pro_limit": daily_pro_limit,
            "daily_pro_remaining": daily_pro_remaining,
            "daily_flash_limit": daily_flash_limit,
            "daily_flash_remaining": daily_flash_remaining,
            "is_pro_unlimited": monthly_paid_limit == 0,
            "is_flash_unlimited": monthly_limit == 0,
            "seat_limit_exceeded": seat_limit_exceeded,
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Token Usage Failed")
        return {"daily_flash_remaining": 0, "is_flash_unlimited": False}
