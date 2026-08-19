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
def get_categories(limit_start: int=0, limit_page_length: int=10, order_by: str='name', order: str='desc', parent: bool=False, select: bool=False, **kwargs) -> Any:
    """
    Retrieves a list of categories with pagination and filters.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    filters = {}
    if parent:
        filters["parent_category"] = ""

    if kwargs.get("type"):
        filters["type"] = kwargs.get("type")

    if kwargs.get("shop_id"):
        filters["shop"] = kwargs.get("shop_id")

    if kwargs.get("active"):
        filters["active"] = int(kwargs.get("active"))

    fields = ["name", "uuid", "type", "image", "active", "status", "shop"]
    if select:
        fields = ["name", "uuid"]

    categories = frappe.get_list(
        "Category",
        fields=fields,
        filters=filters,
        offset=limit_start,
        limit=limit_page_length,
        order_by=f"{order_by} {order}",
    )

    return categories


@frappe.whitelist(allow_guest=True)
def get_category_types() -> Any:
    """
    Returns a list of all available category types.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    category_meta = frappe.get_meta("Category")
    type_field = category_meta.get_field("type")
    return type_field.options.split("\n")


@frappe.whitelist()
def get_children_categories(id: str, limit_start: int=0, limit_page_length: int=10) -> Any:
    """
    Retrieves the children of a given category.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    categories = frappe.get_list(
        "Category",
        fields=["name", "uuid", "type", "image", "active", "status", "shop"],
        filters={"parent_category": id},
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="name desc",
    )

    return categories


@frappe.whitelist()
def search_categories(search: str, limit_start: int=0, limit_page_length: int=10) -> Any:
    """
    Searches for categories by a search term.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    t_category = frappe.qb.DocType("Category")
    query = frappe.qb.from_(t_category).select(
        t_category.name,
        t_category.uuid,
        t_category.type,
        t_category.image,
        t_category.active,
        t_category.status,
        t_category.shop,
    )

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    query = query.where(
        to_tsvector("english", t_category.keywords).matches(
            plainto_tsquery("english", search)
        )
    )

    categories = (
        query.limit(limit_page_length)
        .offset(limit_start)
        .orderby(t_category.name, order=frappe.qb.desc)
        .run(as_dict=True)
    )

    return categories


@frappe.whitelist()
def get_category_by_uuid(uuid: str) -> Any:
    """
    Retrieves a single category by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    category = frappe.get_doc("Category", {"uuid": uuid})
    return category.as_dict()


@frappe.whitelist()
def create_category(category_data: Any) -> Any:
    """
    Creates a new category.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category_uuid = category_data.get("uuid") or str(uuid.uuid4())

    if not category_data.get("type"):
        frappe.throw("Category type is required.")

    if frappe.db.exists("Category", {"uuid": category_uuid}):
        frappe.throw("Category with this UUID already exists.")

    paas_settings = frappe.get_single("Permission Settings")
    initial_status = (
        "Approved" if paas_settings.auto_approve_categories else "Pending"
    )

    category = frappe.get_doc(
        {
            "doctype": "Category",
            "uuid": category_uuid,
            "slug": category_data.get("slug"),
            "keywords": category_data.get("keywords"),
            "parent_category": category_data.get("parent_category"),
            "type": category_data.get("type"),
            "image": category_data.get("image"),
            "active": category_data.get("active", 1),
            "status": initial_status,
            "shop": category_data.get("shop"),
            "input": category_data.get("input"),
        }
    )
    category.insert(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def update_category(uuid: Any, category_data: Any) -> Any:
    """
    Updates an existing category by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not uuid:
        frappe.throw("UUID is required to update a category.")

    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    category = frappe.get_doc("Category", category_name)

    updatable_fields = [
        "slug",
        "keywords",
        "parent_category",
        "type",
        "image",
        "active",
        "status",
        "shop",
        "input",
    ]

    for key, value in category_data.items():
        if key in updatable_fields:
            category.set(key, value)

    category.save(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def delete_category(uuid: Any) -> Any:
    """
    Deletes a category by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not uuid:
        frappe.throw("UUID is required to delete a category.")

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    frappe.delete_doc("Category", category_name, ignore_permissions=True)

    return {"status": "success", "message": "Category deleted successfully."}
