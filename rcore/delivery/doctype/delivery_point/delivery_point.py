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
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeliveryPoint(Document):
    pass


@frappe.whitelist()
def get_nearest_delivery_points(latitude: Any, longitude: Any, radius: Any=20) -> Any:
    """
    Get nearest delivery points based on latitude and longitude.
    :param latitude: User's latitude
    :param longitude: User's longitude
    :param radius: Search radius in kilometers (default: 20)
    :return: List of nearest delivery points
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not latitude or not longitude:
        frappe.throw("Latitude and Longitude are required.")

    try:
        latitude = float(latitude)
        longitude = float(longitude)
        radius = float(radius)
    except ValueError:
        frappe.throw("Invalid coordinates or radius.")

    t_dp = frappe.qb.DocType("Delivery Point")

    # Haversine formula using frappe.qb functions

    # We can use CustomFunction for the math parts
    from frappe.query_builder.functions import CustomFunction
    radians = CustomFunction("RADIANS", ["x"])
    sin = CustomFunction("SIN", ["x"])
    cos = CustomFunction("COS", ["x"])
    acos = CustomFunction("ACOS", ["x"])
    sqrt = CustomFunction("SQRT", ["x"])
    power = CustomFunction("POWER", ["x", "y"])
    asin = CustomFunction("ASIN", ["x"])

    # The formula:
    # 6371 * 2 * ASIN(SQRT(POWER(SIN(RADIANS(lat2 - lat1) / 2), 2) + COS(RADIANS(lat1)) * COS(RADIANS(lat2)) * POWER(SIN(RADIANS(lon2 - lon1) / 2), 2)))

    d_lat = radians(t_dp.latitude - latitude)
    d_lon = radians(t_dp.longitude - longitude)

    a = power(sin(d_lat / 2), 2) + cos(radians(latitude)) * \
        cos(radians(t_dp.latitude)) * power(sin(d_lon / 2), 2)
    c = 2 * asin(sqrt(a))
    distance = 6371 * c

    query = (
        frappe.qb.from_(t_dp)
        .select(
            t_dp.name, t_dp.address, t_dp.latitude, t_dp.longitude, t_dp.img,
            distance.as_("distance")
        )
        .where(t_dp.active == 1)
        .where(distance < radius)
        .orderby(distance)
        .limit(20)
    )

    delivery_points = query.run(as_dict=True)

    return delivery_points
