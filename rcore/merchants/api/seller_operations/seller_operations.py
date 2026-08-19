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


@frappe.whitelist()
def get_seller_kitchens(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of kitchens for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    kitchens = frappe.get_list(
        "Kitchen",
        filters={"shop": shop},
        fields=["name", "active"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return kitchens


@frappe.whitelist()
def create_seller_kitchen(kitchen_data: Any) -> Any:
    """
    Creates a new kitchen for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(kitchen_data, str):
        kitchen_data = json.loads(kitchen_data)

    kitchen_data["shop"] = shop

    new_kitchen = frappe.get_doc({"doctype": "Kitchen", **kitchen_data})
    new_kitchen.insert(ignore_permissions=True)
    return new_kitchen.as_dict()


@frappe.whitelist()
def update_seller_kitchen(kitchen_name: Any, kitchen_data: Any) -> Any:
    """
    Updates a kitchen for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(kitchen_data, str):
        kitchen_data = json.loads(kitchen_data)

    kitchen = frappe.get_doc("Kitchen", kitchen_name)

    if kitchen.shop != shop:
        frappe.throw(
            "You are not authorized to update this kitchen.",
            frappe.PermissionError,
        )

    kitchen.update(kitchen_data)
    kitchen.save(ignore_permissions=True)
    return kitchen.as_dict()


@frappe.whitelist()
def delete_seller_kitchen(kitchen_name: Any) -> Any:
    """
    Deletes a kitchen for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    kitchen = frappe.get_doc("Kitchen", kitchen_name)

    if kitchen.shop != shop:
        frappe.throw(
            "You are not authorized to delete this kitchen.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Kitchen", kitchen_name, ignore_permissions=True)
    return {"status": "success", "message": "Kitchen deleted successfully."}


@frappe.whitelist()
def get_seller_inventory_items(limit_start: int=0, limit_page_length: int=20, item_code: str=None) -> Any:
    """
    Retrieves inventory items (Bin entries) for the current seller's shop.
    Can be filtered by a specific item.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    item_filters = {"shop": shop}
    if item_code:
        item_filters["name"] = item_code

    items = frappe.get_all("Item", filters=item_filters, pluck="name")

    if not items:
        return []

    inventory_items = frappe.get_list(
        "Bin",
        filters={"item_code": ["in", items]},
        fields=["item_code", "warehouse", "actual_qty"],
        limit_start=limit_start,
        limit=limit_page_length,
    )
    return inventory_items


@frappe.whitelist()
def adjust_seller_inventory(item_code: str, warehouse: str, new_qty: int) -> Any:
    """
    Adjusts the inventory for a specific item in a warehouse for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    item = frappe.get_doc("Item", item_code)
    if item.shop != shop:
        frappe.throw(
            "You are not authorized to adjust inventory for this item.",
            frappe.PermissionError,
        )

    # Get current quantity
    current_qty = (
        frappe.db.get_value(
            "Bin",
            {"item_code": item_code, "warehouse": warehouse},
            "actual_qty",
        )
        or 0
    )

    # Create a stock reconciliation entry
    stock_entry = frappe.get_doc(
        {
            "doctype": "Stock Entry",
            "purpose": "Stock Reconciliation",
            "company": shop,
            "items": [
                {
                    "item_code": item_code,
                    "warehouse": warehouse,
                    "qty": new_qty,
                    "basic_rate": item.standard_rate,
                    "t_warehouse": warehouse,
                    "s_warehouse": warehouse,
                    "diff_qty": new_qty - current_qty,
                }
            ],
        }
    )
    stock_entry.submit()

    return {
        "status": "success",
        "message": f"Inventory for {item_code} adjusted to {new_qty}.",
    }


@frappe.whitelist()
def get_seller_menus(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of menus for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    menus = frappe.get_list(
        "Menu",
        filters={"shop": shop},
        fields=["name"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return menus


@frappe.whitelist()
def get_seller_menu(menu_name: Any) -> Any:
    """
    Retrieves a single menu with its items for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    menu = frappe.get_doc("Menu", menu_name)

    if menu.shop != shop:
        frappe.throw(
            "You are not authorized to view this menu.", frappe.PermissionError
        )

    return menu.as_dict()


@frappe.whitelist()
def create_seller_menu(menu_data: Any) -> Any:
    """
    Creates a new menu for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(menu_data, str):
        menu_data = json.loads(menu_data)

    menu_data["shop"] = shop

    new_menu = frappe.get_doc({"doctype": "Menu", **menu_data})
    new_menu.insert(ignore_permissions=True)
    return new_menu.as_dict()


@frappe.whitelist()
def update_seller_menu(menu_name: Any, menu_data: Any) -> Any:
    """
    Updates a menu for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(menu_data, str):
        menu_data = json.loads(menu_data)

    menu = frappe.get_doc("Menu", menu_name)

    if menu.shop != shop:
        frappe.throw(
            "You are not authorized to update this menu.",
            frappe.PermissionError,
        )

    menu.update(menu_data)
    menu.save(ignore_permissions=True)
    return menu.as_dict()


@frappe.whitelist()
def delete_seller_menu(menu_name: Any) -> Any:
    """
    Deletes a menu for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    menu = frappe.get_doc("Menu", menu_name)

    if menu.shop != shop:
        frappe.throw(
            "You are not authorized to delete this menu.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Menu", menu_name, ignore_permissions=True)
    return {"status": "success", "message": "Menu deleted successfully."}


@frappe.whitelist()
def get_seller_receipts(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of receipts for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    receipts = frappe.get_list(
        "Receipt",
        filters={"shop": shop},
        fields=["name", "title"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return receipts


@frappe.whitelist()
def create_seller_receipt(receipt_data: Any) -> Any:
    """
    Creates a new receipt for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(receipt_data, str):
        receipt_data = json.loads(receipt_data)

    receipt_data["shop"] = shop

    new_receipt = frappe.get_doc({"doctype": "Receipt", **receipt_data})
    new_receipt.insert(ignore_permissions=True)
    return new_receipt.as_dict()


@frappe.whitelist()
def update_seller_receipt(receipt_name: Any, receipt_data: Any) -> Any:
    """
    Updates a receipt for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(receipt_data, str):
        receipt_data = json.loads(receipt_data)

    receipt = frappe.get_doc("Receipt", receipt_name)

    if receipt.shop != shop:
        frappe.throw(
            "You are not authorized to update this receipt.",
            frappe.PermissionError,
        )

    receipt.update(receipt_data)
    receipt.save(ignore_permissions=True)
    return receipt.as_dict()


@frappe.whitelist()
def delete_seller_receipt(receipt_name: Any) -> Any:
    """
    Deletes a receipt for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    receipt = frappe.get_doc("Receipt", receipt_name)

    if receipt.shop != shop:
        frappe.throw(
            "You are not authorized to delete this receipt.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Receipt", receipt_name, ignore_permissions=True)
    return {"status": "success", "message": "Receipt deleted successfully."}


@frappe.whitelist()
def get_seller_combos(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of combos for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    combos = frappe.get_list(
        "Combo",
        filters={"shop": shop},
        fields=["name", "price"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return combos


@frappe.whitelist()
def get_seller_combo(combo_name: Any) -> Any:
    """
    Retrieves a single combo with its items for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    combo = frappe.get_doc("Combo", combo_name)

    if combo.shop != shop:
        frappe.throw(
            "You are not authorized to view this combo.",
            frappe.PermissionError,
        )

    return combo.as_dict()


@frappe.whitelist()
def create_seller_combo(combo_data: Any) -> Any:
    """
    Creates a new combo for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(combo_data, str):
        combo_data = json.loads(combo_data)

    combo_data["shop"] = shop

    new_combo = frappe.get_doc({"doctype": "Combo", **combo_data})
    new_combo.insert(ignore_permissions=True)
    return new_combo.as_dict()


@frappe.whitelist()
def update_seller_combo(combo_name: Any, combo_data: Any) -> Any:
    """
    Updates a combo for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(combo_data, str):
        combo_data = json.loads(combo_data)

    combo = frappe.get_doc("Combo", combo_name)

    if combo.shop != shop:
        frappe.throw(
            "You are not authorized to update this combo.",
            frappe.PermissionError,
        )

    combo.update(combo_data)
    combo.save(ignore_permissions=True)
    return combo.as_dict()


@frappe.whitelist()
def delete_seller_combo(combo_name: Any) -> Any:
    """
    Deletes a combo for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    combo = frappe.get_doc("Combo", combo_name)

    if combo.shop != shop:
        frappe.throw(
            "You are not authorized to delete this combo.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Combo", combo_name, ignore_permissions=True)
    return {"status": "success", "message": "Combo deleted successfully."}


# --- MISSING RESTAURANT BOOKING & TABLE ENDPOINTS ---


@frappe.whitelist()
def get_seller_sections(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get seller sections API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)
    if frappe.db.exists("DocType", "Shop Section"):
        return frappe.get_all(
            "Shop Section", filters={"shop": shop}, fields=["name", "title"]
        )
    return []


@frappe.whitelist()
def create_seller_section(section_data: Any=None) -> Any:
    """
    Create seller section API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return {"status": True}


@frappe.whitelist()
def get_seller_tables(limit_start: Any=0, limit_page_length: Any=20) -> Any:
    """
    Get seller tables API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)
    if frappe.db.exists("DocType", "Shop Table"):
        return frappe.get_all(
            "Shop Table",
            filters={"shop": shop},
            fields=["name", "table_number", "capacity"],
        )
    return []


@frappe.whitelist()
def delete_seller_tables(table_id: Any=None) -> Any:
    """
    Delete seller tables API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if table_id and frappe.db.exists("Shop Table", table_id):
        frappe.delete_doc("Shop Table", table_id, ignore_permissions=True)
    return {"status": True}


@frappe.whitelist()
def get_table_disable_dates() -> Any:
    """
    Get table disable dates API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return []


@frappe.whitelist()
def get_booking_working_days() -> Any:
    """
    Get booking working days API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)
    if frappe.db.exists("DocType", "Shop Working Day"):
        return frappe.get_all(
            "Shop Working Day", filters={"shop": shop}, fields=["*"]
        )
    return []


@frappe.whitelist()
def create_seller_booking(booking_data: Any=None) -> Any:
    """
    Create seller booking API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return {"status": True}


@frappe.whitelist()
def update_booking_status(booking_id: Any=None, status: Any=None) -> Any:
    """
    Update booking status API endpoint.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if booking_id and status and frappe.db.exists("Shop Booking", booking_id):
        doc = frappe.get_doc("Shop Booking", booking_id)
        doc.status = status
        doc.save(ignore_permissions=True)
    return {"status": True}
