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
def get_shop() -> Any:
    """
    Retrieves the current seller's shop details.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop_id = _get_seller_shop(user)

    shop = frappe.get_doc("Shop", shop_id)

    return {
        "id": shop.name,
        "uuid": shop.uuid,
        "slug": shop.slug,
        "user_id": shop.user,
        "tax": shop.tax,
        "service_fee": shop.service_fee,
        "percentage": shop.percentage,
        "phone": shop.phone,
        "open": bool(shop.open),
        "visibility": bool(shop.visibility),
        "verify": bool(shop.verify),
        "logo_img": shop.logo,
        "background_img": shop.cover_photo,
        "min_amount": shop.min_amount,
        "status": shop.status,
        "delivery_time": {
            "type": shop.delivery_time_type,
            "from": shop.delivery_time_from,
            "to": shop.delivery_time_to,
        },
        "location": shop.location,
        "title": shop.name,
        "address": shop.address,
        "description": shop.description,
    }


@frappe.whitelist()
def update_shop(shop_data: Any) -> Any:
    """
    Updates the current seller's shop details.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop_id = _get_seller_shop(user)

    if isinstance(shop_data, str):
        shop_data = json.loads(shop_data)

    shop = frappe.get_doc("Shop", shop_id)

    # Update allowed fields
    allowed_fields = [
        "phone",
        "address",
        "location",
        "min_amount",
        "tax",
        "delivery_time_type",
        "delivery_time_from",
        "delivery_time_to",
        "open",
        "logo",
        "cover_photo",
        "description",
    ]

    for field in allowed_fields:
        if field in shop_data:
            shop.set(field, shop_data[field])

    # Handle specific mapping if needed (e.g. logo_img -> logo)
    if "logo_img" in shop_data:
        shop.logo = shop_data["logo_img"]
    if "background_img" in shop_data:
        shop.cover_photo = shop_data["background_img"]
    if "title" in shop_data:
        shop.shop_name = shop_data["title"]  # Assuming shop_name is the field

    shop.save(ignore_permissions=True)
    return shop.as_dict()


@frappe.whitelist()
def set_working_status(status: Any) -> Any:
    """
    Updates the shop's open status.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop_id = _get_seller_shop(user)

    shop = frappe.get_doc("Shop", shop_id)

    # status can be boolean or string "true"/"false" or 0/1
    if isinstance(status, str):
        if status.lower() == "true":
            status = 1
        elif status.lower() == "false":
            status = 0
        else:
            status = int(status)

    shop.open = 1 if status else 0
    shop.save(ignore_permissions=True)

    return shop.open


# --- ALIASES FOR FLUTTER ENDPOINTS ---


@frappe.whitelist()
def set_shop_working_status(status: Any=None) -> Any:
    """
    Set shop working status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return set_working_status(status)
