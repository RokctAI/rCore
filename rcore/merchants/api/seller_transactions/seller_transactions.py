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
def get_seller_transactions(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Retrieves a list of transactions for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    transactions = frappe.get_all(
        "Transaction",
        filters={"reference_name": ["in", orders]},
        fields=[
            "name",
            "transaction_date",
            "reference_doctype",
            "reference_name",
            "debit",
            "credit",
            "currency",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return transactions


@frappe.whitelist()
def get_seller_shop_payments(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of shop payments for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    orders = frappe.get_all("Order", filters={"shop": shop}, pluck="name")

    if not orders:
        return []

    payments = frappe.get_all(
        "Transaction",
        filters={"reference_name": ["in", orders], "credit": [">", 0]},
        fields=[
            "name",
            "transaction_date",
            "reference_doctype",
            "reference_name",
            "credit",
            "currency",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return payments


@frappe.whitelist()
def get_seller_payment_to_partners(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of payments to partners for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    payouts = frappe.get_list(
        "Payout",
        filters={"shop": shop},
        fields=["name", "deliveryman", "amount", "payment_date", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="payment_date desc",
    )
    return payouts
