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
import math

# Legacy lowercase driver-app statuses -> Order Select options ("ready" /
# "on_a_way" have no Order option of their own; Shipped is the in-transit
# state — same mapping as the map module's driver_order.py).
_ORDER_STATUS_MAP = {
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


def _parse_location_dict(value):
    """Parse a location JSON string/dict into {"latitude", "longitude"}
    floats, or None when malformed (never raises — Order.location and
    Shop.location are free-text Data/Geolocation fields)."""
    data = value
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict):
        return None
    lat = data.get("latitude", data.get("lat"))
    lon = data.get("longitude", data.get("long", data.get("lng")))
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        # json.loads accepts NaN/Infinity literals; a NaN here would
        # serialize as invalid JSON for the app's decoder.
        return None
    return {"latitude": lat, "longitude": lon}


def normalize_statuses(statuses):
    """Normalize an incoming statuses filter (JSON string or list, legacy
    lowercase or canonical) into a list of Order Select options. Unknown
    entries are dropped; returns None when nothing usable remains."""
    if not statuses:
        return None
    if isinstance(statuses, str):
        try:
            statuses = json.loads(statuses)
        except (ValueError, TypeError):
            statuses = [statuses]
    if not isinstance(statuses, (list, tuple)):
        statuses = [statuses]
    normalized = []
    for status in statuses:
        canonical = _ORDER_STATUS_MAP.get(str(status).strip().lower())
        if canonical and canonical not in normalized:
            normalized.append(canonical)
    return normalized or None


def _order_payment_tag(order_name):
    """The payment-system tag for an order's transaction ("cash" for the
    COD gateway), from the linked Transaction's PaaS Payment Gateway
    gateway_controller. None when no transaction/gateway exists."""
    rows = frappe.get_all(
        "Transaction",
        filters={"payable_type": "Order", "payable_id": order_name},
        fields=["name", "payment_gateway", "status"],
        order_by="creation desc",
    )
    for row in rows:
        gateway = row.get("payment_gateway")
        if not gateway:
            continue
        controller = frappe.db.get_value(
            "PaaS Payment Gateway", gateway, "gateway_controller"
        )
        if controller:
            return str(controller).strip().lower()
    return None


def serialize_deliveryman_order(order, shop_cache=None):
    """Shape one Order row for the driver app's OrderDetailData model:
    total_price, location {latitude, longitude}, nested shop with coords,
    transaction.payment_system.tag, plus the Frappe name."""
    name = order.get("name")
    row = {
        "name": name,
        # OrderDetailData.id is an int on the Dart side; only emit it
        # when the Frappe name is numeric.
        "id": int(name) if str(name).isdigit() else None,
        "total_price": order.get("total_price"),
        "delivery_fee": order.get("delivery_fee"),
        "status": order.get("status"),
        "creation": str(order.get("creation") or "") or None,
        "location": _parse_location_dict(order.get("location")),
        "address": None,
        "shop": None,
        "transaction": None,
    }

    address = order.get("address")
    if address:
        parsed = None
        if isinstance(address, str):
            try:
                parsed = json.loads(address)
            except (ValueError, TypeError):
                parsed = None
        elif isinstance(address, dict):
            parsed = address
        if isinstance(parsed, dict):
            row["address"] = parsed
        else:
            row["address"] = {"address": address}

    shop_name = order.get("shop")
    if shop_name:
        if shop_cache is not None and shop_name in shop_cache:
            shop_row = shop_cache[shop_name]
        else:
            shop_value = frappe.db.get_value(
                "Shop", shop_name, ["location", "logo"], as_dict=True
            )
            shop_value = shop_value or {}
            shop_row = {
                # Shop names are shop_name strings (autoname
                # field:shop_name); the Dart Shop.id is an int, so the
                # name travels in uuid/translation instead.
                "uuid": shop_name,
                "translation": {"title": shop_name},
                "logo_img": shop_value.get("logo"),
                "location": _parse_location_dict(
                    shop_value.get("location")
                ),
            }
            if shop_cache is not None:
                shop_cache[shop_name] = shop_row
        row["shop"] = shop_row

    tag = _order_payment_tag(name)
    if tag:
        row["transaction"] = {"payment_system": {"tag": tag}}
    return row


@frappe.whitelist()
def get_deliveryman_orders(
    limit_start: int=0, limit_page_length: int=20, statuses: Any=None
) -> Any:
    """
    Retrieves a list of orders assigned to the current deliveryman.

    Each row carries the parsed drop-off coordinates (Order.location
    JSON), the shop's coordinates (Shop.location JSON) and the payment
    tag, shaped for the driver app's OrderDetailData model. An optional
    `statuses` filter accepts canonical or legacy-lowercase statuses.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your orders.",
            frappe.AuthenticationError,
        )

    filters = {"deliveryman": user}
    normalized = normalize_statuses(statuses)
    if normalized:
        filters["status"] = ["in", normalized]

    orders = frappe.get_list(
        "Order",
        filters=filters,
        fields=[
            "name", "shop", "total_price", "delivery_fee", "status",
            "creation", "location", "address",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    shop_cache = {}
    return [
        serialize_deliveryman_order(order, shop_cache=shop_cache)
        for order in orders
    ]


@frappe.whitelist()
def get_deliveryman_parcel_orders(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of parcel orders assigned to the current deliveryman.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your parcel orders.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_list(
        "Parcel Order",
        filters={"deliveryman": user},
        fields=["name", "status", "total_price", "delivery_date"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_deliveryman_settings() -> Any:
    """
    Retrieves the settings for the current deliveryman.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your settings.",
            frappe.AuthenticationError,
        )

    # Per-driver settings live on the "Deliveryman Profile" doctype (the
    # legacy "DeliveryMan Settings" Single only holds the global
    # default_commission_rate and is not per-user).
    if not frappe.db.exists("Deliveryman Profile", {"user": user}):
        return {"can_convert_cod_to_credit": 0}

    settings = frappe.get_doc("Deliveryman Profile", {"user": user}).as_dict()
    settings.setdefault("can_convert_cod_to_credit", 0)
    return settings


@frappe.whitelist()
def update_deliveryman_settings(settings_data: Any) -> Any:
    """
    Updates the settings for the current deliveryman.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update your settings.",
            frappe.AuthenticationError,
        )

    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    # can_convert_cod_to_credit is an admin-granted capability; a driver
    # must not be able to grant it to himself through this endpoint.
    if isinstance(settings_data, dict):
        settings_data.pop("can_convert_cod_to_credit", None)

    if not frappe.db.exists("Deliveryman Profile", {"user": user}):
        settings = frappe.new_doc("Deliveryman Profile")
        settings.user = user
    else:
        settings = frappe.get_doc("Deliveryman Profile", {"user": user})

    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


@frappe.whitelist()
def get_deliveryman_statistics() -> Any:
    """
    Retrieves statistics for the current deliveryman.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your statistics.",
            frappe.AuthenticationError,
        )

    # Total completed orders
    completed_orders_count = frappe.db.count(
        "Order", filters={"deliveryman": user, "status": "Delivered"}
    )

    # Total completed parcel orders
    completed_parcel_orders_count = frappe.db.count(
        "Parcel Order", filters={"deliveryman": user, "status": "Delivered"}
    )

    # Total earnings from regular orders
    t_order = frappe.qb.DocType("Order")
    total_order_earnings = (
        frappe.qb.from_(t_order)
        .select(frappe.qb.fn.Sum(t_order.delivery_fee))
        .where(t_order.deliveryman == user)
        .where(t_order.status == "Delivered")
    ).run()[0][0] or 0

    # Total earnings from parcel orders
    t_parcel_order = frappe.qb.DocType("Parcel Order")
    total_parcel_earnings = (
        frappe.qb.from_(t_parcel_order)
        .select(frappe.qb.fn.Sum(t_parcel_order.delivery_fee))
        .where(t_parcel_order.deliveryman == user)
        .where(t_parcel_order.status == "Delivered")
    ).run()[0][0] or 0

    total_earnings = total_order_earnings + total_parcel_earnings

    return {
        "completed_orders": completed_orders_count,
        "completed_parcel_orders": completed_parcel_orders_count,
        "total_orders": completed_orders_count + completed_parcel_orders_count,
        "total_earnings": total_earnings,
    }


@frappe.whitelist()
def get_banned_shops() -> Any:
    """
    Retrieves a list of shops from which the current deliveryman is banned.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your banned shops.",
            frappe.AuthenticationError,
        )

    banned_shops = frappe.get_all(
        "Shop Ban", filters={"deliveryman": user}, fields=["shop"]
    )
    return [d.shop for d in banned_shops]


@frappe.whitelist()
def get_payment_to_partners(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of payments to partners (deliverymen) for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your payments.",
            frappe.AuthenticationError,
        )

    payouts = frappe.get_list(
        "Payout",
        filters={"deliveryman": user},
        fields=["name", "amount", "payment_date", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="payment_date desc",
    )
    return payouts


@frappe.whitelist()
def get_deliveryman_order_report(from_date: str, to_date: str) -> Any:
    """
    Retrieves a report of orders and parcel orders for the current deliveryman within a date range.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your order report.",
            frappe.AuthenticationError,
        )

    orders = frappe.get_all(
        "Order",
        filters={
            "deliveryman": user,
            "status": "Delivered",
            "creation": ["between", [from_date, to_date]],
        },
        fields=["name", "shop", "total_price", "status", "creation"],
        order_by="creation desc",
    )

    parcel_orders = frappe.get_all(
        "Parcel Order",
        filters={
            "deliveryman": user,
            "status": "Delivered",
            "creation": ["between", [from_date, to_date]],
        },
        fields=["name", "status", "total_price", "delivery_date"],
        order_by="creation desc",
    )

    return {"orders": orders, "parcel_orders": parcel_orders}


@frappe.whitelist()
def get_deliveryman_delivery_zones() -> Any:
    """
    Retrieves a list of delivery zones assigned to the current deliveryman.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your delivery zones.",
            frappe.AuthenticationError,
        )

    delivery_zones = frappe.get_all(
        "Deliveryman Delivery Zone",
        filters={"deliveryman": user},
        fields=["delivery_zone"],
    )
    return [d.delivery_zone for d in delivery_zones]
