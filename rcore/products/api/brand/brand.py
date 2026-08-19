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
import uuid


@frappe.whitelist()
def get_brands(limit_start: int=0, limit_page_length: int=10) -> Any:
    """
    Retrieves a list of brands.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    brands = frappe.get_list(
        "Brand",
        fields=["name", "uuid", "title", "slug", "active", "image", "shop"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name desc",
    )
    return brands


@frappe.whitelist()
def get_brand_by_uuid(uuid: str) -> Any:
    """
    Retrieves a single brand by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    brand = frappe.get_doc("Brand", {"uuid": uuid})
    return brand.as_dict()


@frappe.whitelist()
def create_brand(brand_data: Any) -> Any:
    """
    Creates a new brand.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    brand_uuid = brand_data.get("uuid") or str(uuid.uuid4())

    if not brand_data.get("title"):
        frappe.throw("Brand title is required.")

    if frappe.db.exists("Brand", {"uuid": brand_uuid}):
        frappe.throw("Brand with this UUID already exists.")

    brand = frappe.get_doc(
        {
            "doctype": "Brand",
            "uuid": brand_uuid,
            "title": brand_data.get("title"),
            "slug": brand_data.get("slug"),
            "active": brand_data.get("active", 1),
            "image": brand_data.get("image"),
            "shop": brand_data.get("shop"),
        }
    )
    brand.insert(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def update_brand(uuid: Any, brand_data: Any) -> Any:
    """
    Updates an existing brand by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not uuid:
        frappe.throw("UUID is required to update a brand.")

    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    brand = frappe.get_doc("Brand", brand_name)

    updatable_fields = ["title", "slug", "active", "image", "shop"]

    for key, value in brand_data.items():
        if key in updatable_fields:
            brand.set(key, value)

    brand.save(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def delete_brand(uuid: Any) -> Any:
    """
    Deletes a brand by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not uuid:
        frappe.throw("UUID is required to delete a brand.")

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    frappe.delete_doc("Brand", brand_name, ignore_permissions=True)

    return {"status": "success", "message": "Brand deleted successfully."}
