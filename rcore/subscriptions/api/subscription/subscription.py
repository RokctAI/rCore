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
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Admin Subscription Management


@frappe.whitelist()
def create_subscription(data: Any) -> Any:
    """Create a new subscription."""
    if not frappe.has_permission("Subscription", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_subscription(name: Any) -> Any:
    """Get a subscription by name."""
    if not frappe.has_permission("Subscription", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.get_doc("Subscription", name)


@frappe.whitelist()
def list_subscriptions() -> Any:
    """List all subscriptions."""
    if not frappe.has_permission("Subscription", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.get_list("Subscription", fields=["*"])


@frappe.whitelist()
def update_subscription(name: Any, data: Any) -> Any:
    """Update a subscription."""
    if not frappe.has_permission("Subscription", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Subscription", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_subscription(name: Any) -> Any:
    """Delete a subscription."""
    if not frappe.has_permission("Subscription", "delete"):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.delete_doc("Subscription", name)
    return {
        "status": "success",
        "message": "Subscription deleted successfully"}

# Admin Shop Subscription Management


@frappe.whitelist()
def assign_subscription_to_shop(shop: Any, subscription: Any, expired_at: Any) -> Any:
    """Assign a subscription to a shop."""
    if not frappe.has_permission("Shop Subscription", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)

    sub = frappe.get_doc("Subscription", subscription)

    doc = frappe.get_doc({
        "doctype": "Shop Subscription",
        "shop": shop,
        "subscription": subscription,
        "expired_at": expired_at,
        "price": sub.price,
        "type": sub.type,
        "active": 1,
        "allowed_subjects": sub.get("allowed_subjects")
    })
    doc.insert()
    return doc


@frappe.whitelist()
def get_shop_subscriptions(shop: Any) -> Any:
    """Get all subscriptions for a shop."""
    if not frappe.has_permission("Shop Subscription", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)
    return frappe.get_list(
        "Shop Subscription", filters={
            "shop": shop}, fields=["*"])


@frappe.whitelist()
def update_shop_subscription(name: Any, data: Any) -> Any:
    """Update a shop subscription."""
    if not frappe.has_permission("Shop Subscription", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Shop Subscription", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def cancel_shop_subscription(name: Any) -> Any:
    """Cancel a shop's subscription."""
    if not frappe.has_permission("Shop Subscription", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Shop Subscription", name)
    doc.active = 0
    doc.save()
    return doc

# Seller Subscription Management


def get_seller_shop():
    """Get the shop associated with the current seller."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to manage subscriptions.",
            frappe.PermissionError)

    shop = frappe.db.get_value("Shop", {"user": user}, "name")
    if not shop:
        frappe.throw(
            "You do not have a shop associated with your account.",
            frappe.PermissionError)

    return shop


@frappe.whitelist()
def get_my_shop_subscription() -> Any:
    """Get the current seller's shop subscription."""
    shop = get_seller_shop()
    return frappe.get_list(
        "Shop Subscription",
        filters={
            "shop": shop,
            "active": 1},
        fields=["*"])


@frappe.whitelist()
def subscribe_my_shop(subscription_id: Any) -> Any:
    """Subscribe the seller's shop to a new plan."""
    shop = get_seller_shop()

    # Cancel any existing active subscriptions for the shop
    existing_subscriptions = frappe.get_all(
        "Shop Subscription", filters={
            "shop": shop, "active": 1})
    for sub in existing_subscriptions:
        doc = frappe.get_doc("Shop Subscription", sub.name)
        doc.active = 0
        doc.save()

    # Create the new subscription
    subscription = frappe.get_doc("Subscription", subscription_id)

    from frappe.utils import add_months, nowdate
    expired_at = add_months(nowdate(), subscription.month)

    new_shop_sub = frappe.get_doc({
        "doctype": "Shop Subscription",
        "shop": shop,
        "subscription": subscription_id,
        "expired_at": expired_at,
        "price": subscription.price,
        "type": subscription.type,
        "active": 1,
        "allowed_subjects": subscription.get("allowed_subjects")
    })
    new_shop_sub.insert(ignore_permissions=True)
    return new_shop_sub
