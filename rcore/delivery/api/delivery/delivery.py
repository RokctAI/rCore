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


def is_point_in_polygon(point, polygon):
    """
    Checks if a point is inside a polygon using the Ray-Casting algorithm.
    `point` should be a dict with 'latitude' and 'longitude'.
    `polygon` should be a list of dicts, each with 'latitude' and 'longitude'.
    """
    x, y = point["latitude"], point["longitude"]
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]["latitude"], polygon[0]["longitude"]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]["latitude"], polygon[i % n]["longitude"]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


@frappe.whitelist(allow_guest=True)
def get_delivery_zone_by_shop(shop_id: str) -> Any:
    """
    The get_delivery_zone_by_shop function retrieves the delivery zone associated with a specific shop. It takes one parameter, shop_id, which is a string representing the unique identifier of the shop. The function first checks if the provided shop_id exists in the database, throwing an error if it does not. If the shop exists, it retrieves the corresponding delivery zone document and returns it as a dictionary.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Retrieves the delivery zone for a given shop.
    trace context
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    delivery_zone = frappe.get_doc("Delivery Zone", {"shop": shop_id})
    return delivery_zone.as_dict()


@frappe.whitelist(allow_guest=True)
def check_delivery_zone(shop_id: str, latitude: float, longitude: float) -> Any:
    """
    The check_delivery_zone function determines whether a specific geographic location falls within the designated delivery area of a particular shop. It takes three parameters: shop_id, which is a unique string identifier for the shop, and latitude and longitude, which are floating-point values representing the coordinates of the location to be checked. The function returns a dictionary containing a status indicator and a corresponding message, indicating whether the location is within the delivery zone of the specified shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Checks if a given coordinate is within the delivery zone of a shop.
    trace context
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    delivery_zone = frappe.get_doc("Delivery Zone", {"shop": shop_id})
    polygon = delivery_zone.get("coordinates")
    point = {"latitude": latitude, "longitude": longitude}

    if is_point_in_polygon(point, polygon):
        return {
            "status": "success",
            "message": "Address is within the delivery zone.",
        }
    else:
        return {
            "status": "error",
            "message": "Address is outside the delivery zone.",
        }


@frappe.whitelist(allow_guest=True)
def get_delivery_points() -> Any:
    """
    Retrieves a list of all active delivery points.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    delivery_points = frappe.get_list(
        "Delivery Point",
        filters={"active": 1},
        fields=["name", "price", "address", "location", "img"],
    )
    return delivery_points


@frappe.whitelist(allow_guest=True)
def get_delivery_point(name: Any) -> Any:
    """
    Retrieves a single delivery point by its name.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_doc("Delivery Point", name).as_dict()


@frappe.whitelist(allow_guest=True)
def get_driver_location(driver_id: str) -> Any:
    """
    Retrieves the current location of a driver.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    location = frappe.db.get_value(
        "Driver Location",
        {"driver": driver_id},
        ["latitude", "longitude"],
        order_by="creation desc",
        as_dict=True,
    )

    if not location:
        return {"latitude": 0.0, "longitude": 0.0}

    return location


@frappe.whitelist()
def update_driver_location(latitude: Any, longitude: Any, order_id: Any=None, parcel_order_id: Any=None) -> Any:
    """
    Endpoint for the Driver App to send real-time coordinates.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Authentication required to update location.")

    frappe.get_doc(
        {
            "doctype": "Driver Location",
            "driver": user,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "order": order_id,
            "parcel_order": parcel_order_id,
        }
    ).insert(ignore_permissions=True)

    # Optional: Log to database commit
    frappe.db.commit()

    return {"status": "success", "message": "Location updated."}
