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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
from functools import wraps
from rcore.subscriptions.get_subscription_details import get_subscription_details


def check_subscription_feature(feature_module):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # If on the control panel or running unit tests, bypass all subscription checks.
            if frappe.conf.get("app_role") == "control" or frappe.flags.in_test:
                return fn(*args, **kwargs)

            # Try to get subscription details from cache first
            cache_key = "subscription_details"
            subscription = frappe.cache().get_value(cache_key)

            if not subscription:
                if frappe.flags.in_test:
                    subscription = {"status": "Active", "modules": ["Memory", "HR", "Lending", "Strategic", "Vision", "Pillar"]}
                else:
                    # If not in cache, fetch from API
                    subscription = get_subscription_details()
                if subscription:
                    # Use the cache duration from the subscription details, or
                    # default to 24 hours
                    cache_duration = subscription.get(
                        "subscription_cache_duration", 86400
                    )
                    frappe.cache().set_value(
                        cache_key, subscription, expires_in_sec=cache_duration
                    )

            if not subscription:
                frappe.throw(
                    "Could not retrieve subscription details.", frappe.PermissionError
                )

            if subscription.get("status") not in ["Active", "Trialing"]:
                frappe.throw("Your subscription is not active.", frappe.PermissionError)

            if feature_module not in subscription.get("modules", []):
                frappe.throw(
                    f"Your plan does not include the '{feature_module}' feature.",
                    frappe.PermissionError,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def get_cached_subscription_details():
    """
    Returns the subscription details, using the cache if available.
    """
    if frappe.flags.in_test:
        return {"status": "Active", "modules": ["Memory", "HR", "Lending", "Strategic", "Vision", "Pillar"]}

    cache_key = "subscription_details"
    subscription = frappe.cache().get_value(cache_key)

    if not subscription:
        subscription = get_subscription_details()
        if subscription:
            cache_duration = subscription.get("subscription_cache_duration", 86400)
            frappe.cache().set_value(
                cache_key, subscription, expires_in_sec=cache_duration
            )

    return subscription or {}
