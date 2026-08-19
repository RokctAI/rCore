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
# Tenant context: session.user validation
import frappe
import json
from frappe.utils import flt


@frappe.whitelist()
def create_delivery_zone(data: Any) -> Any:
    """
    Creates a new Delivery Zone.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Delivery Zone", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_shop_delivery_zones(shop_id: Any) -> Any:
    """
    Retrieves all Delivery Zones for a shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_list(
        "Delivery Zone", filters={"shop": shop_id}, fields=["*"]
    )


@frappe.whitelist()
def update_delivery_zone(name: Any, data: Any) -> Any:
    """
    Updates a Delivery Zone.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Delivery Zone", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_delivery_zone(name: Any) -> Any:
    """
    Deletes a Delivery Zone.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    frappe.delete_doc("Delivery Zone", name)
    return {"status": "success"}


@frappe.whitelist()
def check_delivery_availability(lat: Any, lng: Any, shop_id: Any=None) -> Any:
    """
    Checks if a location is within any delivery zone.
    If shop_id is provided, checks only that shop's zones.
    Returns list of shops that deliver to this location.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    lat = flt(lat)
    lng = flt(lng)

    filters = {}
    if shop_id:
        filters["shop"] = shop_id

    zones = frappe.get_list(
        "Delivery Zone",
        filters=filters,
        fields=["name", "shop", "address", "coordinates"],
    )

    available_shops = []

    for zone in zones:
        if not zone.coordinates:
            continue

        try:
            polygon = json.loads(zone.coordinates)
            if is_point_in_polygon(lat, lng, polygon):
                shop = frappe.get_doc("Shop", zone.shop)
                price_info = calculate_delivery_price(lat, lng, shop)
                available_shops.append(
                    {
                        "shop": shop.name,
                        "shop_title": shop.shop_name,
                        "delivery_price": price_info,
                    }
                )
        except Exception:
            continue

    return available_shops


def is_point_in_polygon(lat, lng, polygon):
    """
    Ray-casting algorithm to check if point is in polygon.
    Polygon is list of [lng, lat] coordinates (GeoJSON standard).
    lat: Y, lng: X
    """
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        xi, yi = polygon[i][0], polygon[i][1]  # xi=Lng, yi=Lat
        xj, yj = polygon[j][0], polygon[j][1]  # xj=Lng, yj=Lat

        # Check intersection with ray along X-axis (Lng)
        # We compare Y (Lat) coords
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def calculate_delivery_price(lat, lng, shop):
    """
    Calculates delivery price based on shop settings.
    """
    # Basic distance calculation (Haversine or simple Euclidean for now)
    # Ideally use Google Maps API or OSRM, but for now simple math
    shop_lat = 0
    shop_lng = 0

    if shop.location:
        try:
            loc = json.loads(shop.location)
            if isinstance(loc, dict) and "features" in loc:  # GeoJSON
                coords = loc["features"][0]["geometry"]["coordinates"]
                shop_lat, shop_lng = coords[1], coords[0]
        except Exception:
            pass

    # Placeholder distance (in km) - implementing Haversine
    import math

    R = 6371  # Earth radius in km
    dLat = math.radians(lat - shop_lat)
    dLon = math.radians(lng - shop_lng)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(
        math.radians(shop_lat)
    ) * math.cos(math.radians(lat)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    price = shop.price + (distance * shop.price_per_km)
    return max(price, shop.min_amount)
