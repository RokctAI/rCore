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
def get_seller_delivery_zones(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of delivery zones for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    delivery_zones = frappe.get_list(
        "Delivery Zone",
        filters={"shop": shop},
        fields=["name"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return delivery_zones


@frappe.whitelist()
def get_seller_delivery_zone(zone_name: Any) -> Any:
    """
    Retrieves a single delivery zone with its coordinates for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    zone = frappe.get_doc("Delivery Zone", zone_name)

    if zone.shop != shop:
        frappe.throw(
            "You are not authorized to view this delivery zone.",
            frappe.PermissionError,
        )

    return zone.as_dict()


@frappe.whitelist()
def create_seller_delivery_zone(zone_data: Any) -> Any:
    """
    Creates a new delivery zone for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(zone_data, str):
        zone_data = json.loads(zone_data)

    zone_data["shop"] = shop

    new_zone = frappe.get_doc({"doctype": "Delivery Zone", **zone_data})
    new_zone.insert(ignore_permissions=True)
    return new_zone.as_dict()


@frappe.whitelist()
def update_seller_delivery_zone(zone_name: Any, zone_data: Any) -> Any:
    """
    Updates a delivery zone for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(zone_data, str):
        zone_data = json.loads(zone_data)

    zone = frappe.get_doc("Delivery Zone", zone_name)

    if zone.shop != shop:
        frappe.throw(
            "You are not authorized to update this delivery zone.",
            frappe.PermissionError,
        )

    zone.update(zone_data)
    zone.save(ignore_permissions=True)
    return zone.as_dict()


@frappe.whitelist()
def delete_seller_delivery_zone(zone_name: Any) -> Any:
    """
    Deletes a delivery zone for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    zone = frappe.get_doc("Delivery Zone", zone_name)

    if zone.shop != shop:
        frappe.throw(
            "You are not authorized to delete this delivery zone.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Delivery Zone", zone_name, ignore_permissions=True)
    return {
        "status": "success",
        "message": "Delivery zone deleted successfully.",
    }


@frappe.whitelist()
def check_delivery_fee(lat: Any, lng: Any) -> Any:
    """
    Checks if a location is within any of the seller's delivery zones and returns the fee.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    # Get all zones for the shop
    zones = frappe.get_list(
        "Delivery Zone",
        filters={"shop": shop},
        fields=["name", "delivery_fee", "coordinates"],
    )

    point = {"lat": float(lat), "lng": float(lng)}

    for zone in zones:
        if not zone.coordinates:
            continue

        try:
            polygon = (
                json.loads(zone.coordinates)
                if isinstance(zone.coordinates, str)
                else zone.coordinates
            )
            if is_point_in_polygon(point, polygon):
                return {"fee": zone.delivery_fee, "zone": zone.name}
        except Exception as e:
            frappe.log_error(f"Error checking zone {zone.name}: {str(e)}")
            continue

    return {
        "fee": None,
        "message": "Location not covered by any delivery zone.",
    }


def is_point_in_polygon(point, polygon):
    """
    Ray-casting algorithm to check if point is in polygon.
    Polygon is expected to be a list of dicts with 'lat' and 'lng' or list of lists.
    """
    x = point["lng"]
    y = point["lat"]
    inside = False

    n = len(polygon)
    p1x, p1y = _get_lat_lng(polygon[0])

    for i in range(n + 1):
        p2x, p2y = _get_lat_lng(polygon[i % n])

        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def _get_lat_lng(point_data):
    # Handle different formats: dict or list/tuple
    if isinstance(point_data, dict):
        return point_data.get("lng"), point_data.get("lat")
    elif isinstance(point_data, (list, tuple)):
        # Standardize on [lat, lng] format for list inputs
        return point_data[1], point_data[0]
    return 0, 0
