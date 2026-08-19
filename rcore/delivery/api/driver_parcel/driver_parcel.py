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
from rcore.delivery.api.delivery_man.delivery_man import (
    get_deliveryman_parcel_orders as _get_parcel_orders,
)

# The legacy driver app posts lowercase Laravel-era statuses; the
# Parcel Order doctype's Select options are New / Accepted / Ready /
# "On a way" / Delivered / Canceled. Mapping (case-insensitive):
#   "delivered" -> "Delivered"
#   "canceled" / "cancelled" -> "Canceled"  (Parcel Order spells it with one L)
#   "on_a_way" / "on a way" -> "On a way"
#   "new"/"accepted"/"ready" -> their canonical casing
PARCEL_STATUS_MAP = {
    "new": "New",
    "accepted": "Accepted",
    "ready": "Ready",
    "on_a_way": "On a way",
    "on a way": "On a way",
    "delivered": "Delivered",
    "canceled": "Canceled",
    "cancelled": "Canceled",
}


def normalize_parcel_status(status):
    """Map an incoming (possibly legacy lowercase) status to a valid
    Parcel Order Select option. Returns None for unknown statuses."""
    if status is None:
        return None
    return PARCEL_STATUS_MAP.get(str(status).strip().lower())


def parse_cod_amount(value):
    """Parse an incoming COD amount into a non-negative float.

    Raises ValueError for non-numeric or negative input.
    """
    try:
        amount = float(value)
    except (TypeError, ValueError):
        raise ValueError("amount_received must be a number")
    if amount != amount or amount in (float("inf"), float("-inf")):
        raise ValueError("amount_received must be a finite number")
    if amount < 0:
        raise ValueError("amount_received cannot be negative")
    return amount


def _get_or_create_wallet(user):
    """Fetch or lazily create a user's Wallet ledger doc.

    Same pattern as commerce's deposit_to_wallet: the Wallet doctype
    (uuid/user/balance) is created on first use. Reimplemented locally on
    purpose — modules must not import across module packages.
    """
    wallet_name = frappe.db.get_value("Wallet", {"user": user}, "name")
    if not wallet_name:
        return frappe.get_doc(
            {"doctype": "Wallet", "user": user, "balance": 0}
        ).insert(ignore_permissions=True)
    return frappe.get_doc("Wallet", wallet_name)


@frappe.whitelist()
def get_driver_parcel_orders_paginate(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get driver parcel orders paginate API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return _get_parcel_orders(limit_start, limit_page_length)


@frappe.whitelist()
def add_parcel_order_review(order_id: Any, rating: Any, comment: Any=None) -> Any:
    """
    Add parcel order review API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.new_doc("Review")
        doc.reference_doctype = "Parcel Order"
        doc.reference_name = order_id
        doc.rating = rating
        doc.comment = comment
        doc.user = frappe.session.user
        doc.insert(ignore_permissions=True)
        return {"status": True}
    return {"status": False}


@frappe.whitelist()
def attach_parcel_order_to_me(order_id: Any) -> Any:
    """
    Attach parcel order to me API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if not doc.deliveryman:
            doc.deliveryman = user
            doc.status = "Accepted"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def set_current_parcel_order(order_id: Any) -> Any:
    """
    Set current parcel order API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if doc.deliveryman == user:
            doc.status = "On a Way"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def update_driver_parcel_order_status(order_id: Any, status: Any) -> Any:
    """
    Update driver parcel order status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    normalized = normalize_parcel_status(status)
    if not normalized:
        frappe.throw(
            "Unknown parcel status '{0}'. Allowed: {1}.".format(
                status, ", ".join(sorted(set(PARCEL_STATUS_MAP.values())))
            )
        )
    if frappe.db.exists("Parcel Order", order_id):
        doc = frappe.get_doc("Parcel Order", order_id)
        if doc.deliveryman == frappe.session.user:
            doc.status = normalized
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def confirm_parcel_cod_collection(parcel_id: Any, amount_received: Any) -> Any:
    """
    Records the cash a deliveryman collected from a parcel recipient
    (sender-declared cod_amount, an off-platform sale) and settles it
    between wallets: the collected amount is debited from the
    deliveryman's Wallet (he holds the physical cash, so his ledger may go
    negative) and credited to the sender's Wallet. Two Wallet History rows
    document the movement ("COD Collection" for the driver leg, "COD
    Settlement" for the sender leg). The cod_settled flag makes the whole
    operation strictly once-only.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    if not frappe.db.exists("Parcel Order", parcel_id):
        frappe.throw("Parcel Order {0} not found.".format(parcel_id))

    doc = frappe.get_doc("Parcel Order", parcel_id)
    if doc.deliveryman != user:
        frappe.throw(
            "You are not the deliveryman assigned to this parcel order.",
            frappe.PermissionError,
        )

    cod_amount = float(doc.get("cod_amount") or 0)
    if cod_amount <= 0:
        frappe.throw(
            "Parcel Order {0} has no cash amount to collect.".format(doc.name)
        )

    # THE idempotency guard: without it a retried request would move the
    # wallet balances twice.
    if int(doc.get("cod_settled") or 0):
        frappe.throw(
            "Cash collection for parcel order {0} has already been "
            "settled.".format(doc.name)
        )

    try:
        amount = parse_cod_amount(amount_received)
    except ValueError as e:
        frappe.throw(str(e))

    sender = doc.get("user")
    if not sender:
        frappe.throw(
            "Parcel Order {0} has no sender to settle the collected "
            "cash to.".format(doc.name)
        )
    if sender == user:
        frappe.throw(
            "Sender and deliveryman are the same user; there is nothing "
            "to settle."
        )

    doc.cod_collected_amount = amount
    doc.cod_settled = 1
    doc.save(ignore_permissions=True)

    deliveryman_wallet = _get_or_create_wallet(user)
    sender_wallet = _get_or_create_wallet(sender)

    # Debit the deliveryman (he keeps the physical cash; negative balances
    # are allowed), credit the sender. Everything below runs inside the
    # request's DB transaction: any throw rolls back the doc save and both
    # balance writes together. No explicit frappe.db.commit on purpose.
    if amount > 0:
        deliveryman_wallet.balance = (
            float(deliveryman_wallet.balance or 0) - amount
        )
        deliveryman_wallet.save(ignore_permissions=True)

        sender_wallet.balance = float(sender_wallet.balance or 0) + amount
        sender_wallet.save(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Wallet History",
                "wallet": deliveryman_wallet.name,
                "transaction_type": "COD Collection",
                "amount": -amount,
                "status": "Paid",
                "description": (
                    "Cash collected from recipient of Parcel Order "
                    "{0}".format(doc.name)
                ),
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Wallet History",
                "wallet": sender_wallet.name,
                "transaction_type": "COD Settlement",
                "amount": amount,
                "status": "Paid",
                "description": (
                    "Cash collection settled for Parcel Order "
                    "{0}".format(doc.name)
                ),
            }
        ).insert(ignore_permissions=True)

    return {
        "parcel_id": doc.name,
        "amount": amount,
        "deliveryman_balance": float(deliveryman_wallet.balance or 0),
        "sender_balance": float(sender_wallet.balance or 0),
    }
