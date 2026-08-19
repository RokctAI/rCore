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
from rcore.delivery.api.delivery_man.delivery_man import (
    get_deliveryman_statistics as _get_deliveryman_statistics,
)


@frappe.whitelist()
def get_driver_statistics() -> Any:
    """
    Get driver statistics API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return _get_deliveryman_statistics()


@frappe.whitelist()
def update_location(
    lat: Any=None, lng: Any=None, latitude: Any=None, longitude: Any=None
) -> Any:
    """
    Update location API endpoint.

    Accepts either lat/lng (legacy callers) or latitude/longitude (the
    driver app's background tracker).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if lat is None:
        lat = latitude
    if lng is None:
        lng = longitude
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    if not frappe.db.exists("Deliveryman Profile", {"user": user}):
        doc = frappe.new_doc("Deliveryman Profile")
        doc.user = user
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Deliveryman Profile", {"user": user})

    if hasattr(doc, "latitude") and hasattr(doc, "longitude"):
        doc.latitude = lat
        doc.longitude = lng
        doc.save(ignore_permissions=True)
    return {"status": True, "message": "Location updated"}


@frappe.whitelist()
def set_online_status() -> Any:
    """
    Set online status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized")

    if frappe.db.exists("Deliveryman Profile", {"user": user}):
        doc = frappe.get_doc("Deliveryman Profile", {"user": user})
        doc.online = 1 if not doc.online else 0
        doc.save(ignore_permissions=True)
        return {"status": True, "online": doc.online}
    return {"status": False}


@frappe.whitelist()
def get_car_requests() -> Any:
    """
    Get car requests API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return []


@frappe.whitelist()
def update_car_info(car_model: Any=None, car_number: Any=None, color: Any=None) -> Any:
    """
    Update car info API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if frappe.db.exists("Deliveryman Profile", {"user": user}):
        doc = frappe.get_doc("Deliveryman Profile", {"user": user})
        if hasattr(doc, "car_model"):
            doc.car_model = car_model
            doc.car_number = car_number
            doc.color = color
            doc.save(ignore_permissions=True)
            return doc.as_dict()
    return {}
