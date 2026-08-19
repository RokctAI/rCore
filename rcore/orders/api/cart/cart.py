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
from rcore.base.api.idempotency import idempotent


@frappe.whitelist()
def get_cart(shop_id: str) -> Any:
    """
    Retrieves the active cart for the current user and a given shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your cart.")

    cart_name = frappe.db.get_value(
        "Cart", {"owner": user, "shop": shop_id, "status": "Active"}, "name"
    )
    if not cart_name:
        return None  # No active cart

    return frappe.get_doc("Cart", cart_name).as_dict()


@frappe.whitelist()
@idempotent
def add_to_cart(qty: int, shop_id: str, item_code: str=None, stock_id: int=None, addons: str=None, alternative_product: str=None) -> Any:
    """
    Adds an item to the user's cart. Support multi-cart by shop_id.
    accepts item_code (ProductId) or stock_id (Variant).
    addons: JSON string of addons list.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    import json

    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to add items to your cart.")

    if not item_code and not stock_id:
        frappe.throw("Product or Stock ID required")

    # If item_code not provided, try to find from stock (assuming Stock doctype exists, optional logic)
    # For now, we rely on item_code being passed.

    # Find or create the Cart document
    cart_name = frappe.db.get_value(
        "Cart", {"owner": user, "shop": shop_id, "status": "Active"}, "name"
    )
    if not cart_name:
        cart = frappe.get_doc(
            {
                "doctype": "Cart",
                "owner": user,
                "shop": shop_id,
                "status": "Active",
            }
        ).insert(ignore_permissions=True)
    else:
        cart = frappe.get_doc("Cart", cart_name)

    # Decode addons if present
    addons_data = []
    if addons:
        try:
            addons_data = (
                json.loads(addons) if isinstance(addons, str) else addons
            )
        except Exception:
            addons_data = []

    # Check if item already exists in cart (matching stock_id and addons)
    existing_item = None

    # helper for addons comparison
    def compare_addons(a1, a2):
        # simplified check: sort by stock_id and compare
        # a1, a2 are lists of dicts
        if not a1 and not a2:
            return True
        if not a1 or not a2:
            return False
        if len(a1) != len(a2):
            return False
        # Deep compare implementation needed or just assume new row if complex
        # For MVP, we will just add a new row if addons are present to avoid
        # merging complexity
        return False

    # If no addons, we can try to merge
    should_merge = len(addons_data) == 0

    if should_merge:
        for detail in cart.items:
            # Check match: item_code and stock_id
            # If stock_id is provided, match it. If not, match item_code only?
            match = False
            if stock_id:
                if detail.stock_id == int(stock_id):
                    match = True
            elif item_code:
                if detail.item == item_code and (not detail.stock_id):
                    match = True

            if match:
                # Check if existing item has addons. If yes, don't merge (since
                # we have no addons)
                existing_addons = (
                    json.loads(detail.addons) if detail.addons else []
                )
                if not existing_addons:
                    existing_item = detail
                    break

    if existing_item:
        existing_item.quantity += int(qty)
    else:
        # Get Price
        price = 0
        if item_code:
            price = (
                frappe.db.get_value("Product", item_code, "price") or 0
            )  # field name might be diff
        # If stock_id, might want to fetch specific price

        cart.append(
            "items",
            {
                "item": item_code,  # Ensure item_code is provided by Caller
                "quantity": qty,
                "price": price,
                "stock_id": stock_id,
                "addons": json.dumps(addons_data) if addons_data else None,
                "bonus": 0,
                "alternative_product": alternative_product,
            },
        )

    cart.save(ignore_permissions=True)

    # Recalculate totals
    calculate_cart_totals(cart.name)

    return cart.as_dict()


@frappe.whitelist()
def remove_from_cart(cart_detail_name: str) -> Any:
    """
    Removes an item from the cart.
    `cart_detail_name` is the name of the Cart Detail row.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to modify your cart.")

    cart_detail = frappe.get_doc("Cart Detail", cart_detail_name)
    cart = frappe.get_doc("Cart", cart_detail.parent)

    if cart.owner != user:
        frappe.throw(
            "You are not authorized to remove this item.",
            frappe.PermissionError,
        )

    # Remove the item
    cart.remove(cart_detail)
    cart.save(ignore_permissions=True)

    # Recalculate totals
    calculate_cart_totals(cart.name)
    return {"status": "success", "message": "Item removed from cart."}


@frappe.whitelist()
@idempotent
def remove_product_cart(cart_detail_id: str) -> Any:
    """
    Alias for remove_from_cart, used by Flutter app.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return remove_from_cart(cart_detail_name=cart_detail_id)


def calculate_cart_totals(cart_name: str):
    """
    Helper function to recalculate the total price of a cart.
    """
    cart = frappe.get_doc("Cart", cart_name)
    total_price = 0
    for detail in cart.items:
        total_price += detail.price * detail.quantity

    cart.total_price = total_price
    cart.save(ignore_permissions=True)


@frappe.whitelist()
def create_cart(cart: dict, lang: str='en') -> Any:
    """
    Creates a new cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    cart_doc = frappe.get_doc(
        {
            "doctype": "Cart",
            "user": frappe.session.user,
            "shop": cart.get("shop_id"),
        }
    )
    for item in cart.get("items", []):
        cart_doc.append(
            "items",
            {
                "item": item.get("item_code"),
                "quantity": item.get("quantity"),
                "alternative_product": item.get("alternative_product"),
            },
        )
    cart_doc.insert(ignore_permissions=True)
    return cart_doc.as_dict()


@frappe.whitelist()
def insert_cart(cart: dict, lang: str='en') -> Any:
    """
    Inserts items into an existing cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    cart_doc = frappe.get_doc("Cart", cart.get("cart_id"))
    for item in cart.get("items", []):
        cart_doc.append(
            "items",
            {
                "item": item.get("item_code"),
                "quantity": item.get("quantity"),
                "alternative_product": item.get("alternative_product"),
            },
        )
    cart_doc.save(ignore_permissions=True)
    return cart_doc.as_dict()


@frappe.whitelist()
def insert_cart_with_group(cart: dict, lang: str='en') -> Any:
    """
    Inserts items into an existing group cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    cart_doc = frappe.get_doc("Cart", cart.get("cart_id"))
    for item in cart.get("items", []):
        cart_doc.append(
            "items",
            {
                "item": item.get("item_code"),
                "quantity": item.get("quantity"),
                "alternative_product": item.get("alternative_product"),
            },
        )
    cart_doc.save(ignore_permissions=True)
    return cart_doc.as_dict()


@frappe.whitelist()
def create_and_cart(cart: dict, lang: str='en') -> Any:
    """
    Creates a new cart and adds items to it.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_cart(cart, lang)


@frappe.whitelist()
def get_cart_in_group(cart_id: str, shop_id: str, cart_uuid: str, lang: str='en') -> Any:
    """
    Retrieves a group cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_doc("Cart", cart_id)


@frappe.whitelist()
def delete_cart(cart_id: int, lang: str='en') -> Any:
    """
    Deletes a cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    frappe.delete_doc("Cart", cart_id, ignore_permissions=True)
    return {"status": "success"}


@frappe.whitelist()
def change_status(user_uuid: str, cart_id: str, lang: str='en') -> Any:
    """
    Changes the status of a user in a group cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    # This is a placeholder for the actual implementation.
    return {"status": "success"}


@frappe.whitelist()
def delete_user(cart_id: int, user_id: str, lang: str='en') -> Any:
    """
    Deletes a user from a group cart.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    cart_doc = frappe.get_doc("Cart", cart_id)
    cart_doc.remove("group_order_users", {"user": user_id})
    cart_doc.save(ignore_permissions=True)
    return cart_doc.as_dict()

    cart_doc.save(ignore_permissions=True)
    return cart_doc.as_dict()


@frappe.whitelist()
def join_order(cart_id: str, user_name: str, lang: str='en') -> Any:
    """
    Allows a user to join a group order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    # Placeholder logic
    return {"status": "success", "message": "Joined order."}
