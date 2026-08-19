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
import json
from rcore.base.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_orders(limit_start: int=0, limit_page_length: int=20, status: str=None, from_date: str=None, to_date: str=None) -> Any:
    """
    Retrieves a list of orders for the current seller's shop, with optional filters.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    filters = {"shop": shop}
    if status:
        filters["status"] = status
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]

    orders = frappe.get_list(
        "Order",
        filters=filters,
        fields=["name", "user", "grand_total", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_seller_order_details(order_id: Any) -> Any:
    """
    Retrieves full details of a specific order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    order = frappe.get_doc("Order", order_id)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to view this order.",
            frappe.PermissionError,
        )

    return order.as_dict()


@frappe.whitelist()
def update_seller_order_status(order_id: Any, status: Any) -> Any:
    """
    Updates the status of an order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    order = frappe.get_doc("Order", order_id)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to update this order.",
            frappe.PermissionError,
        )

    valid_statuses = [
        "New",
        "Accepted",
        "Shipped",
        "Delivered",
        "Cancelled",
        "Paid",
        "Failed",
    ]
    if status not in valid_statuses:
        frappe.throw(f"Invalid status. Must be one of: {
            ', '.join(valid_statuses)}")

    order.status = status
    order.save(ignore_permissions=True)
    return order.as_dict()


@frappe.whitelist()
def get_seller_order_refunds(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of order refunds for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    refunds = frappe.get_list(
        "Order Refund",
        filters={"order": ["in", orders]},
        fields=["name", "order", "status", "cause", "answer"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return refunds


@frappe.whitelist()
def update_seller_order_refund(refund_name: Any, status: Any, answer: Any=None) -> Any:
    """
    Updates the status and answer of an order refund.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    refund = frappe.get_doc("Order Refund", refund_name)
    order = frappe.get_doc("Order", refund.order)

    if order.shop != shop:
        frappe.throw(
            "You are not authorized to update this refund request.",
            frappe.PermissionError,
        )

    if status not in ["Accepted", "Canceled"]:
        frappe.throw("Invalid status. Must be 'Accepted' or 'Canceled'.")

    refund.status = status
    if answer:
        refund.answer = answer

    refund.save(ignore_permissions=True)
    return refund.as_dict()


@frappe.whitelist()
def get_seller_reviews(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of reviews for products in the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    products = frappe.get_all("Item", filters={"shop": shop}, pluck="name")

    if not products:
        return []

    reviews = frappe.get_list(
        "Review",
        filters={"reviewable_id": ["in", products], "reviewable_type": "Item"},
        fields=[
            "name",
            "user",
            "rating",
            "comment",
            "creation",
            "reviewable_id",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return reviews
