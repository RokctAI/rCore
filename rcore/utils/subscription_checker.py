# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
from functools import wraps
from rcore.tenant.api import get_subscription_details


def check_subscription_feature(feature_module):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # If on the control panel, bypass all subscription checks.
            if frappe.conf.get("app_role") == "control":
                return fn(*args, **kwargs)

            # Try to get subscription details from cache first
            cache_key = "subscription_details"
            subscription = frappe.cache().get_value(cache_key)

            if not subscription:
                # If not in cache, fetch from API
                subscription = get_subscription_details()
                if subscription:
                    # Use the cache duration from the subscription details, or
                    # default to 24 hours
                    cache_duration = subscription.get(
                        "subscription_cache_duration", 86400)
                    frappe.cache().set_value(cache_key, subscription, expires_in_sec=cache_duration)

            if not subscription:
                frappe.throw(
                    "Could not retrieve subscription details.",
                    frappe.PermissionError)

            if subscription.get("status") not in ["Active", "Trialing"]:
                frappe.throw(
                    "Your subscription is not active.",
                    frappe.PermissionError)

            if feature_module not in subscription.get("modules", []):
                frappe.throw(
                    f"Your plan does not include the '{feature_module}' feature.",
                    frappe.PermissionError)

            return fn(*args, **kwargs)
        return wrapper
    return decorator
