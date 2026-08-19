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
import json
import frappe
from rcore.delivery.api.delivery_man.delivery_man import (
    get_deliveryman_orders as _get_orders,
)

# Tolerance when comparing a collected cash amount against the order total
# (Currency fields are 2dp; this only absorbs float noise).
COD_AMOUNT_EPSILON = 1e-6

# The legacy driver app posts lowercase Laravel-era statuses; the Order
# doctype's Select options are New / Accepted / Shipped / Delivered /
# Cancelled / Paid / Failed. Mapping (case-insensitive):
#   "delivered" -> "Delivered"
#   "canceled" / "cancelled" -> "Cancelled"
#   "on_a_way" / "on a way" -> "Shipped"  (Order has no "On a Way" option;
#       Shipped is the in-transit state)
#   "new"/"accepted"/"shipped"/"paid"/"failed" -> their canonical casing
ORDER_STATUS_MAP = {
    "new": "New",
    "accepted": "Accepted",
    "ready": "Shipped",
    "on_a_way": "Shipped",
    "on a way": "Shipped",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "canceled": "Cancelled",
    "cancelled": "Cancelled",
    "paid": "Paid",
    "failed": "Failed",
}


def normalize_order_status(status):
    """Map an incoming (possibly legacy lowercase) status to a valid
    Order Select option. Returns None for unknown statuses."""
    if status is None:
        return None
    return ORDER_STATUS_MAP.get(str(status).strip().lower())


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


def _split_order_transactions(order_id):
    """Return (cash_transactions, non_cash_transactions) linked to an Order.

    A transaction is "cash" when its PaaS Payment Gateway's
    gateway_controller is "Cash" (case-insensitive).
    """
    rows = frappe.get_all(
        "Transaction",
        filters={"payable_type": "Order", "payable_id": order_id},
        fields=["name", "payment_gateway", "status"],
    )
    cash, non_cash = [], []
    for row in rows:
        controller = None
        if row.get("payment_gateway"):
            controller = frappe.db.get_value(
                "PaaS Payment Gateway", row.get("payment_gateway"),
                "gateway_controller",
            )
        if controller and str(controller).strip().lower() == "cash":
            cash.append(row)
        else:
            non_cash.append(row)
    return cash, non_cash


def _assert_cash_order(doc):
    """Throw unless the order is payable in cash.

    Returns the list of linked cash Transactions (may be empty: WhatsApp
    COD orders are created without any Transaction — checkout.py builds the
    order payload with payment_status "Unpaid" and no Transaction row — so
    a transactionless order still counts as cash-eligible while its
    payment_status is a pending/unpaid state).
    """
    cash_tx, non_cash_tx = _split_order_transactions(doc.name)
    if cash_tx:
        return cash_tx
    if non_cash_tx:
        frappe.throw(
            "Order {0} is not a cash order (a non-cash payment "
            "transaction exists).".format(doc.name)
        )
    if (doc.payment_status or "Pending") not in ("Pending", "Unpaid"):
        frappe.throw(
            "Order {0} cannot be treated as a cash order "
            "(payment status is {1}).".format(doc.name, doc.payment_status)
        )
    return []


@frappe.whitelist()
def get_driver_orders_paginate(
    limit_start: Any=0, limit_page_length: Any=20, statuses: Any=None
) -> Any:
    """
    Get driver orders paginate API endpoint.

    Returns {"data": [...], "meta": {"total": n}} — the shape the driver
    app's OrderPaginateResponse expects — with rows enriched by
    get_deliveryman_orders (coordinates, shop, payment tag). `statuses`
    optionally filters (legacy lowercase or canonical values).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    rows = _get_orders(limit_start, limit_page_length, statuses)

    total = len(rows) if isinstance(rows, list) else 0
    try:
        # Lazy: the composed delivery_man module provides the normalizer
        # (the module-level import above predates it; keeping this lazy
        # also keeps older stubs working).
        from rcore.delivery.api.delivery_man.delivery_man import normalize_statuses
    except ImportError:
        normalize_statuses = None
    if normalize_statuses is not None:
        filters = {"deliveryman": frappe.session.user}
        normalized = normalize_statuses(statuses)
        if normalized:
            filters["status"] = ["in", normalized]
        counted = frappe.db.count("Order", filters)
        if isinstance(counted, int):
            total = counted
    return {"data": rows, "meta": {"total": total}}


@frappe.whitelist()
def fetch_current_order() -> Any:
    """
    Fetch current order API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    order = frappe.get_list(
        "Order",
        filters={
            "deliveryman": user,
            "status": ["in", ["On a Way", "Accepted"]],
        },
        fields=["name", "shop", "total_price", "status", "creation"],
        limit=1,
    )
    if order:
        doc = frappe.get_doc("Order", order[0].name)
        return {"data": doc.as_dict()}
    return {"data": {}}


@frappe.whitelist()
def set_current_order(order_id: Any) -> Any:
    """
    Set current order API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if doc.deliveryman == user:
            doc.status = "On a Way"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def attach_order_to_me(order_id: Any) -> Any:
    """
    Attach order to me API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if not doc.deliveryman:
            doc.deliveryman = user
            doc.status = "Accepted"
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def update_driver_order_status(order_id: Any, status: Any) -> Any:
    """
    Update driver order status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    normalized = normalize_order_status(status)
    if not normalized:
        frappe.throw(
            "Unknown order status '{0}'. Allowed: {1}.".format(
                status, ", ".join(sorted(set(ORDER_STATUS_MAP.values())))
            )
        )
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if doc.deliveryman == frappe.session.user:
            doc.status = normalized
            doc.save(ignore_permissions=True)
            return {"status": True, "data": doc.as_dict()}
    return {"status": False}


@frappe.whitelist()
def confirm_cod_collection(order_id: Any, amount_received: Any) -> Any:
    """
    Records how much cash the deliveryman actually collected on a
    cash-on-delivery order. The server (Order.total_price) is the sole
    authority on the expected amount; the driver only confirms what he
    physically received. Full collection marks the order (and its cash
    Transaction, when one exists) as Paid; partial collection is recorded
    without changing payment_status.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    if not frappe.db.exists("Order", order_id):
        frappe.throw("Order {0} not found.".format(order_id))

    doc = frappe.get_doc("Order", order_id)
    if doc.deliveryman != user:
        frappe.throw(
            "You are not the deliveryman assigned to this order.",
            frappe.PermissionError,
        )

    cash_tx = _assert_cash_order(doc)

    try:
        amount = parse_cod_amount(amount_received)
    except ValueError as e:
        frappe.throw(str(e))

    # Idempotency: never double-record a collection.
    already = doc.get("cod_collected_amount") or 0
    if float(already) > 0:
        frappe.throw(
            "Cash collection for order {0} is already recorded "
            "({1}).".format(doc.name, already)
        )

    expected_total = float(doc.total_price or 0)

    doc.cod_collected_amount = amount
    if amount + COD_AMOUNT_EPSILON >= expected_total:
        doc.payment_status = "Paid"
        for tx in cash_tx:
            frappe.db.set_value(
                "Transaction", tx.get("name"), "status", "Paid"
            )
    doc.save(ignore_permissions=True)

    return {
        "order_id": doc.name,
        "cod_collected_amount": amount,
        "payment_status": doc.payment_status,
        "expected_total": expected_total,
    }


@frappe.whitelist()
def convert_cod_to_credit(order_id: Any) -> Any:
    """
    Flips an (uncollected) cash order to payment_status "Credit": the goods
    were left with the customer and the customer now owes the shop. Requires
    BOTH opt-ins: the deliveryman's Deliveryman Profile must have the
    can_convert_cod_to_credit capability enabled, AND the order's Shop must
    have chosen to offer credit (Shop.enable_credit). A missing shop link or
    an unset enable_credit field counts as the shop NOT offering credit.

    Shops that offer credit additionally choose a Shop.credit_mode:
    "All Orders" (default) makes every order eligible, while
    "Selected Products" restricts credit to orders containing at least one
    item whose Product has allow_credit checked — one qualifying item makes
    the WHOLE order eligible. A missing/unset/unknown credit_mode is
    treated as "All Orders" (back-compat with shops saved before the field
    existed).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    if not frappe.db.exists("Order", order_id):
        frappe.throw("Order {0} not found.".format(order_id))

    doc = frappe.get_doc("Order", order_id)
    if doc.deliveryman != user:
        frappe.throw(
            "You are not the deliveryman assigned to this order.",
            frappe.PermissionError,
        )

    allowed = frappe.db.get_value(
        "Deliveryman Profile", {"user": user}, "can_convert_cod_to_credit"
    )
    if not allowed:
        frappe.throw(
            "You are not allowed to convert cash orders to credit. "
            "Ask an administrator to enable this on your profile.",
            frappe.PermissionError,
        )

    # Shop-level opt-in: the order's shop (Order.shop -> Shop) must have
    # enable_credit checked. No shop, or an unset/0 field, means the shop
    # does not offer credit.
    shop = doc.get("shop")
    shop_credit = (
        frappe.db.get_value("Shop", shop, ["enable_credit", "credit_mode"])
        if shop
        else None
    )
    shop_offers_credit, credit_mode = shop_credit or (0, None)
    if not shop_offers_credit:
        frappe.throw(
            "This shop does not offer credit.",
            frappe.PermissionError,
        )

    # Credit mode: "Selected Products" restricts credit to orders that
    # contain at least one item whose Product has allow_credit checked
    # (one qualifying item makes the whole order eligible). Any other or
    # unset value means "All Orders" — no per-product check.
    if credit_mode == "Selected Products":
        products = list(
            {
                item.get("product")
                for item in (doc.get("order_items") or [])
                if item.get("product")
            }
        )
        qualifying = (
            frappe.get_all(
                "Product",
                filters={"name": ["in", products], "allow_credit": 1},
                limit=1,
            )
            if products
            else []
        )
        if not qualifying:
            frappe.throw(
                "No product in this order is allowed on credit.",
                frappe.PermissionError,
            )

    _assert_cash_order(doc)

    if doc.payment_status == "Paid":
        frappe.throw(
            "Order {0} is already paid and cannot be converted to "
            "credit.".format(doc.name)
        )
    if float(doc.get("cod_collected_amount") or 0) > 0:
        frappe.throw(
            "Cash has already been collected for order {0}; it cannot "
            "be converted to credit.".format(doc.name)
        )

    doc.payment_status = "Credit"
    doc.save(ignore_permissions=True)

    return {"order_id": doc.name, "payment_status": doc.payment_status}


# Order statuses that still need driving: not yet Delivered / Cancelled /
# Failed (Paid is a payment outcome recorded on delivered flows).
ACTIVE_ORDER_STATUSES = ("New", "Accepted", "Shipped")
# Parcel Order statuses that still need driving.
ACTIVE_PARCEL_STATUSES = ("New", "Accepted", "Ready", "On a way")


def _address_text(value):
    """Human label from an address payload: the "address" key of a JSON
    dict, else the raw text itself. Never raises."""
    data = value
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return text
    if isinstance(data, dict):
        label = data.get("address")
        return str(label) if label else None
    return None


def _order_payment_tag(order_id):
    """Payment-system tag for an order ("cash" when its transactions are
    COD), reusing the COD helpers' gateway split."""
    cash, non_cash = _split_order_transactions(order_id)
    if cash:
        return "cash"
    for row in non_cash:
        gateway = row.get("payment_gateway")
        if not gateway:
            continue
        controller = frappe.db.get_value(
            "PaaS Payment Gateway", gateway, "gateway_controller"
        )
        if controller:
            return str(controller).strip().lower()
    return None


@frappe.whitelist()
def get_driver_route(latitude: Any=None, longitude: Any=None) -> Any:
    """
    The session driver's merged, server-ordered stop list: active Orders
    (shop pickup + customer drop-off from Order.location JSON), active
    Parcel Orders (address_from/address_to JSON — tolerant of the plain
    "Customer: <name>" text, which simply yields a coordinate-less stop
    at the tail), plus the pending stops of an active Dispatch Route.

    Ordering is greedy nearest-next from the given latitude/longitude,
    falling back to the driver's last reported Deliveryman Profile
    position, else the first stop as-is. A pickup always precedes its own
    drop-off. Stops without usable coordinates go last, flagged
    missing_coordinates. The returned `sequence` is the drive order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    # Lazy imports: composed as paas.api.*; lazy so this module still
    # imports under older/partial test stubs.
    from rcore.delivery.api.route.route_utils import order_stops, parse_location

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    shop_location_cache = {}

    def shop_coords(shop_name):
        if not shop_name:
            return None
        if shop_name not in shop_location_cache:
            shop_location_cache[shop_name] = parse_location(
                frappe.db.get_value("Shop", shop_name, "location")
            )
        return shop_location_cache[shop_name]

    stops = []

    orders = frappe.get_all(
        "Order",
        filters={
            "deliveryman": user,
            "status": ["in", list(ACTIVE_ORDER_STATUSES)],
        },
        fields=[
            "name", "shop", "total_price", "status", "location",
            "address",
        ],
        order_by="creation asc",
    )
    for order in orders:
        meta = {
            "total_price": order.get("total_price"),
            "status": order.get("status"),
            "payment_tag": _order_payment_tag(order.get("name")),
        }
        # Shipped = already picked up; only the drop-off remains.
        if order.get("status") != "Shipped" and order.get("shop"):
            coords = shop_coords(order.get("shop"))
            stops.append(
                {
                    "stop_type": "pickup",
                    "ref_doctype": "Order",
                    "ref_name": order.get("name"),
                    "pair_key": "Order:{0}".format(order.get("name")),
                    "label": order.get("shop"),
                    "latitude": coords[0] if coords else None,
                    "longitude": coords[1] if coords else None,
                    "quantity": None,
                    "unit": None,
                    "meta": meta,
                }
            )
        drop = parse_location(order.get("location"))
        stops.append(
            {
                "stop_type": "dropoff",
                "ref_doctype": "Order",
                "ref_name": order.get("name"),
                "pair_key": "Order:{0}".format(order.get("name")),
                "label": (
                    _address_text(order.get("address"))
                    or order.get("name")
                ),
                "latitude": drop[0] if drop else None,
                "longitude": drop[1] if drop else None,
                "quantity": None,
                "unit": None,
                "meta": meta,
            }
        )

    parcels = frappe.get_all(
        "Parcel Order",
        filters={
            "deliveryman": user,
            "status": ["in", list(ACTIVE_PARCEL_STATUSES)],
        },
        fields=[
            "name", "status", "total_price", "address_from", "address_to",
            "username_from", "username_to", "cod_amount",
        ],
        order_by="creation asc",
    )
    for parcel in parcels:
        meta = {
            "total_price": parcel.get("total_price"),
            "status": parcel.get("status"),
            "cod_amount": parcel.get("cod_amount"),
            "payment_tag": "cash" if parcel.get("cod_amount") else None,
        }
        # "On a way" = parcel already collected; only the drop-off is left.
        if parcel.get("status") != "On a way":
            pickup = parse_location(parcel.get("address_from"))
            stops.append(
                {
                    "stop_type": "pickup",
                    "ref_doctype": "Parcel Order",
                    "ref_name": parcel.get("name"),
                    "pair_key": "Parcel Order:{0}".format(
                        parcel.get("name")
                    ),
                    "label": (
                        parcel.get("username_from")
                        or _address_text(parcel.get("address_from"))
                        or parcel.get("name")
                    ),
                    "latitude": pickup[0] if pickup else None,
                    "longitude": pickup[1] if pickup else None,
                    "quantity": None,
                    "unit": None,
                    "meta": meta,
                }
            )
        drop = parse_location(parcel.get("address_to"))
        stops.append(
            {
                "stop_type": "dropoff",
                "ref_doctype": "Parcel Order",
                "ref_name": parcel.get("name"),
                "pair_key": "Parcel Order:{0}".format(parcel.get("name")),
                "label": (
                    parcel.get("username_to")
                    or _address_text(parcel.get("address_to"))
                    or parcel.get("name")
                ),
                "latitude": drop[0] if drop else None,
                "longitude": drop[1] if drop else None,
                "quantity": None,
                "unit": None,
                "meta": meta,
            }
        )

    try:
        from rcore.delivery.api.dispatch_route.dispatch_route import (
            get_active_dispatch_stops,
        )
    except ImportError:
        get_active_dispatch_stops = None
    if get_active_dispatch_stops is not None:
        _route, dispatch_stops = get_active_dispatch_stops(user)
        stops.extend(dispatch_stops or [])

    start = None
    try:
        if latitude is not None and longitude is not None:
            start = (float(latitude), float(longitude))
            if start == (0.0, 0.0):
                start = None
    except (TypeError, ValueError):
        start = None
    if start is None:
        profile = frappe.db.get_value(
            "Deliveryman Profile",
            {"user": user},
            ["latitude", "longitude"],
            as_dict=True,
        )
        if profile:
            try:
                candidate = (
                    float(profile.get("latitude")),
                    float(profile.get("longitude")),
                )
                if candidate != (0.0, 0.0):
                    start = candidate
            except (TypeError, ValueError):
                start = None

    return order_stops(start, stops)


@frappe.whitelist()
def upload_order_image(order_id: Any, image_url: Any=None) -> Any:
    """
    Upload order image API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not image_url:
        return {"status": False}
    if frappe.db.exists("Order", order_id):
        doc = frappe.get_doc("Order", order_id)
        if hasattr(doc, "delivery_photo"):
            doc.delivery_photo = image_url
            doc.save(ignore_permissions=True)
            return {"status": True}
    return {"status": True}
