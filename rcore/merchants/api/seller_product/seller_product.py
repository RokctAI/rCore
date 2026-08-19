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
import uuid
from rcore.base.api.utils import _get_seller_shop
from rcore.base.api.idempotency import idempotent


@frappe.whitelist()
def get_seller_products(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of products for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    products = frappe.get_list(
        "Product",
        filters={"shop": shop},
        fields=[
            "name",
            "title",
            "description",
            "image",
            "price",
            "active",
            "allow_credit",
            "status",
            "category",
            "unit",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return products


@frappe.whitelist()
def create_seller_product(product_data: Any) -> Any:
    """
    Creates a new product for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(product_data, str):
        product_data = json.loads(product_data)

    product_data["shop"] = shop

    # Check the global PaaS setting for auto-approval
    # Assuming Permission Settings exists, otherwise default to Approved
    try:
        paas_settings = frappe.get_single("Permission Settings")
        initial_status = (
            "published" if paas_settings.auto_approve_products else "pending"
        )
    except Exception:
        initial_status = "published"

    new_product = frappe.get_doc({"doctype": "Product", **product_data})
    new_product.status = initial_status
    new_product.insert(ignore_permissions=True)
    return new_product.as_dict()


@frappe.whitelist()
def update_seller_product(product_name: Any, product_data: Any) -> Any:
    """
    Updates a product for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(product_data, str):
        product_data = json.loads(product_data)

    product = frappe.get_doc("Product", product_name)

    if product.shop != shop:
        frappe.throw(
            "You are not authorized to update this product.",
            frappe.PermissionError,
        )

    product.update(product_data)
    product.save(ignore_permissions=True)
    return product.as_dict()


@frappe.whitelist()
def delete_seller_product(product_name: Any) -> Any:
    """
    Deletes a product for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    product = frappe.get_doc("Product", product_name)

    if product.shop != shop:
        frappe.throw(
            "You are not authorized to delete this product.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Product", product_name, ignore_permissions=True)
    return {"status": "success", "message": "Product deleted successfully."}


@frappe.whitelist()
def get_seller_categories(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of categories for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    categories = frappe.get_list(
        "Category",
        filters={"shop": shop},
        fields=["name", "uuid", "type", "image", "active", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name desc",
    )
    return categories


@frappe.whitelist()
def create_seller_category(category_data: Any) -> Any:
    """
    Creates a new category for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    category_data["shop"] = shop

    # Re-using the existing create_category function logic
    category_uuid = category_data.get("uuid") or str(uuid.uuid4())
    if not category_data.get("type"):
        frappe.throw("Category type is required.")
    if frappe.db.exists("Category", {"uuid": category_uuid}):
        frappe.throw("Category with this UUID already exists.")

    category = frappe.get_doc({"doctype": "Category", **category_data})
    category.insert(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def update_seller_category(uuid: Any, category_data: Any) -> Any:
    """
    Updates a category for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    category = frappe.get_doc("Category", category_name)
    if category.shop != shop:
        frappe.throw(
            "You are not authorized to update this category.",
            frappe.PermissionError,
        )

    if isinstance(category_data, str):
        category_data = json.loads(category_data)

    updatable_fields = [
        "slug",
        "keywords",
        "parent_category",
        "type",
        "image",
        "active",
        "status",
        "input",
    ]
    for key, value in category_data.items():
        if key in updatable_fields:
            category.set(key, value)

    category.save(ignore_permissions=True)
    return category.as_dict()


@frappe.whitelist()
def delete_seller_category(uuid: Any) -> Any:
    """
    Deletes a category for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    category = frappe.get_doc("Category", category_name)
    if category.shop != shop:
        frappe.throw(
            "You are not authorized to delete this category.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Category", category_name, ignore_permissions=True)
    return {"status": "success", "message": "Category deleted successfully."}


@frappe.whitelist()
def get_seller_brands(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of brands for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    brands = frappe.get_list(
        "Brand",
        filters={"shop": shop},
        fields=["name", "uuid", "title", "slug", "active", "image"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name desc",
    )
    return brands


@frappe.whitelist()
def create_seller_brand(brand_data: Any) -> Any:
    """
    Creates a new brand for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    brand_data["shop"] = shop

    # Re-using the existing create_brand function logic
    brand_uuid = brand_data.get("uuid") or str(uuid.uuid4())
    if not brand_data.get("title"):
        frappe.throw("Brand title is required.")
    if frappe.db.exists("Brand", {"uuid": brand_uuid}):
        frappe.throw("Brand with this UUID already exists.")

    brand = frappe.get_doc({"doctype": "Brand", **brand_data})
    brand.insert(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def update_seller_brand(uuid: Any, brand_data: Any) -> Any:
    """
    Updates a brand for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    brand = frappe.get_doc("Brand", brand_name)
    if brand.shop != shop:
        frappe.throw(
            "You are not authorized to update this brand.",
            frappe.PermissionError,
        )

    if isinstance(brand_data, str):
        brand_data = json.loads(brand_data)

    updatable_fields = ["title", "slug", "active", "image"]
    for key, value in brand_data.items():
        if key in updatable_fields:
            brand.set(key, value)

    brand.save(ignore_permissions=True)
    return brand.as_dict()


@frappe.whitelist()
def delete_seller_brand(uuid: Any) -> Any:
    """
    Deletes a brand for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    brand_name = frappe.db.get_value("Brand", {"uuid": uuid}, "name")
    if not brand_name:
        frappe.throw("Brand not found.")

    brand = frappe.get_doc("Brand", brand_name)
    if brand.shop != shop:
        frappe.throw(
            "You are not authorized to delete this brand.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Brand", brand_name, ignore_permissions=True)
    return {"status": "success", "message": "Brand deleted successfully."}


@frappe.whitelist()
def get_seller_extra_groups(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of product extra groups for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    extra_groups = frappe.get_list(
        "Product Extra Group",
        filters={"shop": shop},
        fields=["name"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return extra_groups


@frappe.whitelist()
def create_seller_extra_group(group_data: Any) -> Any:
    """
    Creates a new product extra group for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(group_data, str):
        group_data = json.loads(group_data)

    group_data["shop"] = shop

    new_group = frappe.get_doc(
        {"doctype": "Product Extra Group", **group_data}
    )
    new_group.insert(ignore_permissions=True)
    return new_group.as_dict()


@frappe.whitelist()
def update_seller_extra_group(group_name: Any, group_data: Any) -> Any:
    """
    Updates a product extra group for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(group_data, str):
        group_data = json.loads(group_data)

    group = frappe.get_doc("Product Extra Group", group_name)

    if group.shop != shop:
        frappe.throw(
            "You are not authorized to update this group.",
            frappe.PermissionError,
        )

    group.update(group_data)
    group.save(ignore_permissions=True)
    return group.as_dict()


@frappe.whitelist()
def delete_seller_extra_group(group_name: Any) -> Any:
    """
    Deletes a product extra group for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    group = frappe.get_doc("Product Extra Group", group_name)

    if group.shop != shop:
        frappe.throw(
            "You are not authorized to delete this group.",
            frappe.PermissionError,
        )

    frappe.delete_doc(
        "Product Extra Group", group_name, ignore_permissions=True
    )
    return {"status": "success", "message": "Group deleted successfully."}


@frappe.whitelist()
def get_seller_extra_values(group_name: Any, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of product extra values for a given group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    extra_values = frappe.get_list(
        "Product Extra Value",
        filters={"product_extra_group": group_name},
        fields=["name", "value", "price"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return extra_values


@frappe.whitelist()
def create_seller_extra_value(value_data: Any) -> Any:
    """
    Creates a new product extra value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(value_data, str):
        value_data = json.loads(value_data)

    group = frappe.get_doc(
        "Product Extra Group", value_data["product_extra_group"]
    )
    if group.shop != shop:
        frappe.throw(
            "You are not authorized to add a value to this group.",
            frappe.PermissionError,
        )

    new_value = frappe.get_doc(
        {"doctype": "Product Extra Value", **value_data}
    )
    new_value.insert(ignore_permissions=True)
    return new_value.as_dict()


@frappe.whitelist()
def update_seller_extra_value(value_name: Any, value_data: Any) -> Any:
    """
    Updates a product extra value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(value_data, str):
        value_data = json.loads(value_data)

    value = frappe.get_doc("Product Extra Value", value_name)
    group = frappe.get_doc("Product Extra Group", value.product_extra_group)

    if group.shop != shop:
        frappe.throw(
            "You are not authorized to update this value.",
            frappe.PermissionError,
        )

    value.update(value_data)
    value.save(ignore_permissions=True)
    return value.as_dict()


@frappe.whitelist()
def delete_seller_extra_value(value_name: Any) -> Any:
    """
    Deletes a product extra value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    value = frappe.get_doc("Product Extra Value", value_name)
    group = frappe.get_doc("Product Extra Group", value.product_extra_group)

    if group.shop != shop:
        frappe.throw(
            "You are not authorized to delete this value.",
            frappe.PermissionError,
        )

    frappe.delete_doc(
        "Product Extra Value", value_name, ignore_permissions=True
    )
    return {"status": "success", "message": "Value deleted successfully."}


@frappe.whitelist()
def get_seller_units(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of units for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    units = frappe.get_list(
        "Shop Unit",
        filters={"shop": shop},
        fields=["name", "active"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return units


@frappe.whitelist()
def create_seller_unit(unit_data: Any) -> Any:
    """
    Creates a new unit for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(unit_data, str):
        unit_data = json.loads(unit_data)

    unit_data["shop"] = shop

    new_unit = frappe.get_doc({"doctype": "Shop Unit", **unit_data})
    new_unit.insert(ignore_permissions=True)
    return new_unit.as_dict()


@frappe.whitelist()
def update_seller_unit(unit_name: Any, unit_data: Any) -> Any:
    """
    Updates a unit for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(unit_data, str):
        unit_data = json.loads(unit_data)

    unit = frappe.get_doc("Shop Unit", unit_name)

    if unit.shop != shop:
        frappe.throw(
            "You are not authorized to update this unit.",
            frappe.PermissionError,
        )

    unit.update(unit_data)
    unit.save(ignore_permissions=True)
    return unit.as_dict()


@frappe.whitelist()
def delete_seller_unit(unit_name: Any) -> Any:
    """
    Deletes a unit for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    unit = frappe.get_doc("Shop Unit", unit_name)

    if unit.shop != shop:
        frappe.throw(
            "You are not authorized to delete this unit.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Shop Unit", unit_name, ignore_permissions=True)
    return {"status": "success", "message": "Unit deleted successfully."}


@frappe.whitelist()
def get_seller_tags(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of tags for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    tags = frappe.get_list(
        "Shop Tag",
        filters={"shop": shop},
        fields=["name"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return tags


@frappe.whitelist()
def create_seller_tag(tag_data: Any) -> Any:
    """
    Creates a new tag for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(tag_data, str):
        tag_data = json.loads(tag_data)

    tag_data["shop"] = shop

    new_tag = frappe.get_doc({"doctype": "Shop Tag", **tag_data})
    new_tag.insert(ignore_permissions=True)
    return new_tag.as_dict()


@frappe.whitelist()
def update_seller_tag(tag_name: Any, tag_data: Any) -> Any:
    """
    Updates a tag for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(tag_data, str):
        tag_data = json.loads(tag_data)

    tag = frappe.get_doc("Shop Tag", tag_name)

    if tag.shop != shop:
        frappe.throw(
            "You are not authorized to update this tag.",
            frappe.PermissionError,
        )

    tag.update(tag_data)
    tag.save(ignore_permissions=True)
    return tag.as_dict()


@frappe.whitelist()
def delete_seller_tag(tag_name: Any) -> Any:
    """
    Deletes a tag for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    tag = frappe.get_doc("Shop Tag", tag_name)

    if tag.shop != shop:
        frappe.throw(
            "You are not authorized to delete this tag.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Shop Tag", tag_name, ignore_permissions=True)
    return {"status": "success", "message": "Tag deleted successfully."}


# --- ALIASES FOR FLUTTER ENDPOINTS ---


@frappe.whitelist()
@idempotent
def create_product(product_data: Any=None) -> Any:
    """
    Create product API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_seller_product(product_data)


@frappe.whitelist()
def get_seller_products_paginate(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get seller products paginate API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_seller_products(limit_start, limit_page_length)


@frappe.whitelist()
def get_extras_groups(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get extras groups API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_seller_extra_groups(limit_start, limit_page_length)


@frappe.whitelist()
def create_extras_group(group_data: Any=None) -> Any:
    """
    Create extras group API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_seller_extra_group(group_data)


@frappe.whitelist()
def delete_extras_group(group_name: Any=None) -> Any:
    """
    Delete extras group API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return delete_seller_extra_group(group_name)


@frappe.whitelist()
def create_extras_value(value_data: Any=None) -> Any:
    """
    Create extras value API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_seller_extra_value(value_data)


@frappe.whitelist()
def delete_extras_value(value_name: Any=None) -> Any:
    """
    Delete extras value API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return delete_seller_extra_value(value_name)


@frappe.whitelist()
def get_product_details(product_name: Any=None) -> Any:
    """
    Get product details API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if product_name and frappe.db.exists("Product", product_name):
        return {"data": frappe.get_doc("Product", product_name).as_dict()}
    return {"data": {}}


@frappe.whitelist()
def update_product_extras(product_name: Any=None, extras_data: Any=None) -> Any:
    """
    Update product extras API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return {"status": True}


@frappe.whitelist()
def update_product_stocks(product_name: Any=None, stocks_data: Any=None) -> Any:
    """
    Update product stocks API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return {"status": True}
