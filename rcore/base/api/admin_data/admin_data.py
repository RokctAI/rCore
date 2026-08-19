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
from ..utils import _require_admin


@frappe.whitelist()
def get_all_units(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all shop units on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Unit",
        fields=["name", "shop", "active"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_tags(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all shop tags on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Tag",
        fields=["name", "shop"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_points(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all points on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Point",
        fields=["name", "user", "points", "reason"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_point(point_data: Any) -> Any:
    """
    Creates a new point record (for admins).
    """
    _require_admin()
    if isinstance(point_data, str):
        point_data = json.loads(point_data)

    new_point = frappe.get_doc({"doctype": "Point", **point_data})
    new_point.insert(ignore_permissions=True)
    return new_point.as_dict()


@frappe.whitelist()
def update_point(point_name: Any, point_data: Any) -> Any:
    """
    Updates a point record (for admins).
    """
    _require_admin()
    if isinstance(point_data, str):
        point_data = json.loads(point_data)

    point = frappe.get_doc("Point", point_name)
    point.update(point_data)
    point.save(ignore_permissions=True)
    return point.as_dict()


@frappe.whitelist()
def delete_point(point_name: Any) -> Any:
    """
    Deletes a point record (for admins).
    """
    _require_admin()
    frappe.delete_doc("Point", point_name, ignore_permissions=True)
    return {
        "status": "success",
        "message": "Point record deleted successfully.",
    }


@frappe.whitelist()
def get_all_translations(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all translations on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Translation",
        fields=["name", "language", "source_text", "translated_text"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_referrals(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all referrals on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Referral",
        fields=["name", "referrer", "referred_user", "referral_code"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_referral(referral_data: Any) -> Any:
    """
    Creates a new referral (for admins).
    """
    _require_admin()
    if isinstance(referral_data, str):
        referral_data = json.loads(referral_data)

    new_referral = frappe.get_doc({"doctype": "Referral", **referral_data})
    new_referral.insert(ignore_permissions=True)
    return new_referral.as_dict()


@frappe.whitelist()
def delete_referral(referral_name: Any) -> Any:
    """
    Deletes a referral (for admins).
    """
    _require_admin()
    frappe.delete_doc("Referral", referral_name, ignore_permissions=True)
    return {"status": "success", "message": "Referral deleted successfully."}


@frappe.whitelist()
def get_all_shop_tags(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all shop tags on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Tag",
        fields=["name", "shop"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_product_extra_groups(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all product extra groups on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Product Extra Group",
        fields=["name", "shop"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_all_product_extra_values(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all product extra values on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Product Extra Value",
        fields=["name", "product_extra_group", "value", "price"],
        offset=limit_start,
        limit=limit_page_length,
    )
