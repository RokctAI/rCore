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
def get_seller_shop_galleries(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of shop gallery images for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    galleries = frappe.get_list(
        "Shop Gallery",
        filters={"shop": shop},
        fields=["name", "image"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return galleries


@frappe.whitelist()
def create_seller_shop_gallery(gallery_data: Any) -> Any:
    """
    Creates a new shop gallery image for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(gallery_data, str):
        gallery_data = json.loads(gallery_data)

    gallery_data["shop"] = shop

    new_gallery = frappe.get_doc({"doctype": "Shop Gallery", **gallery_data})
    new_gallery.insert(ignore_permissions=True)
    return new_gallery.as_dict()


@frappe.whitelist()
def delete_seller_shop_gallery(gallery_name: Any) -> Any:
    """
    Deletes a shop gallery image for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    gallery = frappe.get_doc("Shop Gallery", gallery_name)

    if gallery.shop != shop:
        frappe.throw(
            "You are not authorized to delete this gallery image.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Shop Gallery", gallery_name, ignore_permissions=True)
    return {
        "status": "success",
        "message": "Gallery image deleted successfully.",
    }
