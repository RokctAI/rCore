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
from rcore.base.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_request_models(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of request models for the current seller.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your request models.",
            frappe.AuthenticationError,
        )

    request_models = frappe.get_list(
        "Request Model",
        filters={"created_by_user": user},
        fields=["name", "model_type", "model", "status", "created_at"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return request_models


@frappe.whitelist()
def get_seller_customer_addresses(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of customer addresses for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    t_order = frappe.qb.DocType("Order")
    customer_ids = (
        frappe.qb.from_(t_order)
        .select(frappe.qb.fn.Distinct(t_order.user))
        .where(t_order.shop == shop)
    ).run(pluck=True)

    if not customer_ids:
        return []

    addresses = frappe.get_all(
        "User Address",
        filters={"user": ["in", customer_ids]},
        fields=["name", "user", "title", "address", "location", "active"],
        offset=limit_start,
        limit=limit_page_length,
    )
    return addresses
