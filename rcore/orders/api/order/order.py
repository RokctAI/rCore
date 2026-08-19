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
from frappe.model.document import Document
from rcore.base.api.utils import api_response
from rcore.base.api.idempotency import idempotent


@frappe.whitelist(allow_guest=True)
@idempotent
def create_order(order_data: Any) -> Any:
    """
    Creates a new order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(order_data, str):
        order_data = json.loads(order_data)

    # 1. Idempotency Check (Offline UUID)
    offline_uuid = order_data.get("offline_uuid")
    if offline_uuid:
        existing_order = frappe.db.exists(
            "Order", {"offline_uuid": offline_uuid}
        )
        if existing_order:
            return api_response(
                data=frappe.get_doc("Order", existing_order).as_dict(),
                message="Duplicate order detected. Returning existing order.",
            )

    # Check for hierarchical auto-approval
    paas_settings = frappe.get_single("Permission Settings")

    # Validate phone number if required by admin settings
    if paas_settings.require_phone_for_order and not order_data.get("phone"):
        frappe.throw(
            "A phone number is required to create this order.",
            frappe.ValidationError,
        )

    shop = frappe.get_doc("Shop", order_data.get("shop"))

    initial_status = "New"
    if paas_settings.auto_approve_orders and shop.auto_approve_orders:
        initial_status = "Accepted"

    # If cart_id is provided and order_items is missing, load items from cart
    if order_data.get("cart_id") and not order_data.get("order_items"):
        cart = frappe.get_doc("Cart", order_data.get("cart_id"))
        order_items = []
        for item in cart.items:
            product_doc = frappe.get_doc("Product", item.item)
            order_items.append(
                {
                    "product": item.item,
                    "quantity": item.quantity,
                    "price": item.price or product_doc.price,
                    "alternative_product": item.alternative_product,
                }
            )
        order_data["order_items"] = order_items

    order = frappe.get_doc(
        {
            "doctype": "Order",
            "user": order_data.get("user"),
            "shop": order_data.get("shop"),
            "status": initial_status,
            "delivery_type": order_data.get("delivery_type"),
            "currency": order_data.get("currency"),
            "rate": order_data.get("rate"),
            "delivery_fee": order_data.get("delivery_fee"),
            "waiter_fee": order_data.get("waiter_fee"),
            "tax": order_data.get("tax"),
            "commission_fee": order_data.get("commission_fee"),
            "service_fee": order_data.get("service_fee"),
            "total_discount": order_data.get("total_discount"),
            "coupon_code": order_data.get("coupon_code"),
            "location": order_data.get("location"),
            "address": order_data.get("address"),
            "phone": order_data.get("phone"),
            "username": order_data.get("username"),
            "delivery_date": order_data.get("delivery_date"),
            "delivery_time": order_data.get("delivery_time"),
            "note": order_data.get("note"),
            "offline_uuid": offline_uuid,
        }
    )

    for item in order_data.get("order_items", []):
        product_id = item.get("product")
        quantity = item.get("quantity")
        alt_product_id = item.get("alternative_product")

        # Real-time Stock Check & Auto-Substitution
        is_substituted = 0
        original_product = None

        # Check stock for primary product
        stock_qty = (
            frappe.db.get_value(
                "Stock",
                {"shop": order_data.get("shop"), "product": product_id},
                "quantity",
            )
            or 0
        )

        if stock_qty <= 0 and alt_product_id:
            # Check stock for alternative product
            alt_stock_qty = (
                frappe.db.get_value(
                    "Stock",
                    {
                        "shop": order_data.get("shop"),
                        "product": alt_product_id,
                    },
                    "quantity",
                )
                or 0
            )
            if alt_stock_qty > 0:
                original_product = product_id
                product_id = alt_product_id
                is_substituted = 1

        # Fetch current price for the chosen product (primary or substituted)
        current_price = (
            frappe.db.get_value("Product", product_id, "price") or 0
        )
        cost_price = frappe.db.get_value("Product", product_id, "cost") or 0

        order.append(
            "order_items",
            {
                "product": product_id,
                "quantity": quantity,
                "price": current_price,
                "cost_price": cost_price,
                "alternative_product": alt_product_id,
                "is_substituted": is_substituted,
                "original_product": original_product,
            },
        )

    # Store the quoted total from frontend for refund calculation
    order.quoted_total = order_data.get("quoted_total") or 0

    order.insert(ignore_permissions=True)

    # Surplus Refund Logic (Pay-Max Strategy)
    # If the user authorized/paid more than the final actual total, refund to
    # wallet.
    if order.quoted_total > order.total_price:
        refund_amount = order.quoted_total - order.total_price
        deposit_to_wallet(
            user=order.user,
            amount=refund_amount,
            note=f"Substitution refund for Order {order.name}",
        )

    # Calculate cashback
    if order.total_price:
        # Composed path per merchants/frappe/manifest.json:
        # rcore.api.shop.check_cashback ->
        # rcore.merchants.api.shop.check_cashback (the old double
        # "shop.shop" segment path pointed at a module that never exists).
        cashback_amount = frappe.call(
            "paas.merchants.api.shop.check_cashback",
            shop_id=order_data.get("shop"),
            amount=order.total_price,
        )
        order.db_set("cashback_amount", cashback_amount.get("cashback_amount"))

    if order_data.get("coupon_code"):
        coupon = frappe.get_doc(
            "Coupon", {"code": order_data.get("coupon_code")}
        )
        frappe.get_doc(
            {
                "doctype": "Coupon Usage",
                "coupon": coupon.name,
                "user": order.user,
                "order": order.name,
            }
        ).insert(ignore_permissions=True)

    return api_response(
        data=order.as_dict(), message="Order created successfully."
    )


def deposit_to_wallet(user, amount, note):
    """
    Helper to add balance to user's wallet and log the transaction.
    """
    if not amount or amount <= 0:
        return

    # 1. Fetch or Create Wallet
    wallet_name = frappe.db.get_value("Wallet", {"user": user}, "name")
    if not wallet_name:
        wallet = frappe.get_doc(
            {"doctype": "Wallet", "user": user, "balance": 0}
        ).insert(ignore_permissions=True)
    else:
        wallet = frappe.get_doc("Wallet", wallet_name)

    # 2. Update Balance
    wallet.balance += amount
    wallet.save(ignore_permissions=True)

    # 3. Create Transaction Audit Record
    frappe.get_doc(
        {
            "doctype": "Transaction",
            "user": user,
            "amount": amount,
            "status": "Paid",
            "type": "Refund",
            "note": note,
            "performed_at": frappe.utils.now_datetime(),
        }
    ).insert(ignore_permissions=True)

    frappe.db.commit()


@frappe.whitelist()
def list_orders(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of orders for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your orders.")

    orders = frappe.get_list(
        "Order",
        filters={"user": user},
        fields=["name", "shop", "total_price", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
        ignore_permissions=True,
    )
    return api_response(data=orders)


@frappe.whitelist()
def get_order_details(order_id: str) -> Any:
    """
    Retrieves the details of a specific order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your orders.")

    # Bypass permission check for retrieval
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        order = frappe.get_doc("Order", order_id)
    finally:
        frappe.set_user(original_user)
    if order.user != user:
        frappe.throw(
            "You are not authorized to view this order.",
            frappe.PermissionError,
        )
    return api_response(data=order.as_dict())


@frappe.whitelist()
def update_order_status(order_id: str, status: str) -> Any:
    """
    Updates the status of a specific order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to update an order.")

    # Bypass permission check for retrieval
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        order = frappe.get_doc("Order", order_id)
    finally:
        frappe.set_user(original_user)

    if order.user != user and "System Manager" not in frappe.get_roles(user):
        frappe.throw(
            "You are not authorized to update this order.",
            frappe.PermissionError,
        )

    valid_statuses = (
        frappe.get_meta("Order").get_field("status").options.split("\n")
    )
    if status not in valid_statuses:
        frappe.throw(f"Invalid status. Must be one of {
            ', '.join(valid_statuses)}")

    previous_status = order.status
    order.status = status
    order.save(ignore_permissions=True)

    # Subtract stock when order is Accepted (and wasn't already)
    if status == "Accepted" and previous_status != "Accepted":
        for item in order.order_items:
            # Check if product tracks stock
            product_doc = frappe.get_doc("Product", item.product)
            if product_doc.track_stock:
                # Find the Stock record for this shop and product
                stock_name = frappe.db.get_value(
                    "Stock",
                    {"shop": order.shop, "product": item.product},
                    "name",
                )
                if stock_name:
                    stock_doc = frappe.get_doc("Stock", stock_name)
                    stock_doc.quantity -= item.quantity
                    stock_doc.save(ignore_permissions=True)
                else:
                    # Optional: Create stock record if missing? checking with user pref "stocks belong to sellers"
                    # For now, let's log or create if not exists
                    frappe.get_doc(
                        {
                            "doctype": "Stock",
                            "shop": order.shop,
                            "product": item.product,
                            "quantity": -item.quantity,  # Allow negative logic if started from 0
                            "price": item.price,  # Init price
                        }
                    ).insert(ignore_permissions=True)

    # Restore stock if order is Cancelled/Rejected from a status that deducted
    # stock
    if status in ["Cancelled", "Rejected"] and previous_status in [
        "Accepted",
        "Prepared",
        "Delivered",
    ]:  # Assuming these are downstream of Accepted
        for item in order.order_items:
            product_doc = frappe.get_doc("Product", item.product)
            if product_doc.track_stock:
                stock_name = frappe.db.get_value(
                    "Stock",
                    {"shop": order.shop, "product": item.product},
                    "name",
                )
                if stock_name:
                    stock_doc = frappe.get_doc("Stock", stock_name)
                    stock_doc.quantity += item.quantity
                    stock_doc.save(ignore_permissions=True)

    return api_response(
        data=order.as_dict(), message="Order status updated successfully."
    )


@frappe.whitelist()
def add_order_review(order_id: str, rating: float, comment: str=None) -> Any:
    """
    Adds a review for a specific order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to leave a review.")

    # Bypass permission check for retrieval
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        order = frappe.get_doc("Order", order_id)
    finally:
        frappe.set_user(original_user)

    if order.user != user:
        frappe.throw(
            "You can only review your own orders.", frappe.PermissionError
        )

    if order.status != "Delivered":
        frappe.throw("You can only review delivered orders.")

    if frappe.db.exists(
        "Review",
        {"reviewable_type": "Order", "reviewable_id": order_id, "user": user},
    ):
        frappe.throw("You have already reviewed this order.")

    review = frappe.get_doc(
        {
            "doctype": "Review",
            "reviewable_type": "Order",
            "reviewable_id": order_id,
            "user": user,
            "rating": rating,
            "comment": comment,
            "published": 1,
        }
    )
    review.insert(ignore_permissions=True)
    return api_response(
        data=review.as_dict(), message="Review added successfully."
    )


@frappe.whitelist()
def cancel_order(order_id: str) -> Any:
    """
    Cancels a specific order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to cancel an order.")

    # Bypass permission check for retrieval
    original_user = frappe.session.user
    frappe.set_user("Administrator")
    try:
        order = frappe.get_doc("Order", order_id)
    finally:
        frappe.set_user(original_user)

    if order.user != user and "System Manager" not in frappe.get_roles(user):
        frappe.throw(
            "You are not authorized to cancel this order.",
            frappe.PermissionError,
        )

    if order.status != "New":
        frappe.throw(
            "You can only cancel orders that have not been accepted yet."
        )

    order.status = "Cancelled"
    # No stock restoration needed for "New" orders as stock wasn't deducted
    # yet.

    order.save(ignore_permissions=True)
    return api_response(
        data=order.as_dict(), message="Order cancelled successfully."
    )


@frappe.whitelist(allow_guest=True)
def get_order_statuses() -> Any:
    """
    Retrieves a list of active order statuses, formatted for frontend compatibility.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    statuses = frappe.get_list(
        "Order Status",
        filters={"is_active": 1},
        fields=["name", "status_name", "sort_order"],
        order_by="sort_order asc",
    )

    formatted_statuses = []
    for status in statuses:
        formatted_statuses.append(
            {
                "id": status.name,
                "name": status.status_name,
                "active": True,
                "sort": status.sort_order,
            }
        )

    return api_response(data=formatted_statuses)


@frappe.whitelist()
def get_calculate(cart_id: Any, address: Any=None, coupon_code: Any=None, tips: Any=0, delivery_type: Any='Delivery') -> Any:
    """
    The get_calculate function calculates the total cost of a shopping cart, taking into account various factors such as product prices, taxes, discounts, delivery fees, and service fees. 
    
    It accepts the following parameters: 
    - cart_id: the unique identifier of the shopping cart
    - address: the delivery address, which can be a string or a dictionary containing latitude and longitude coordinates
    - coupon_code: a discount coupon code to apply to the order
    - tips: the amount of tips to add to the order, defaulting to 0
    - delivery_type: the type of delivery, defaulting to 'Delivery'
    
    The function returns a dictionary containing the calculated totals, including the total tax, product price, shop tax, total price, discount, delivery fee, service fee, tips, and coupon price. 
    
    This function is used to provide an accurate estimate of the total cost of an order, considering various factors that may affect the final price.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(address, str) and address:
        try:
            address = json.loads(address)
        except Exception:
            address = None

    cart = frappe.get_doc("Cart", cart_id)
    shop = frappe.get_doc("Shop", cart.shop)

    # 1. Calculate Product Totals
    product_tax = 0
    product_total = 0
    subtotal_buffer = 0  # To track price protection for alternatives
    discount = 0
    calculated_products = []

    for item in cart.items:
        # Using 'Product' instead of 'Item' as per project conventions
        product_doc = frappe.get_doc("Product", item.item)

        item_price = product_doc.price or 0

        # Pay-Max Logic: Use alternative price if higher
        effective_price = item_price
        if item.alternative_product:
            alt_price = (
                frappe.db.get_value(
                    "Product", item.alternative_product, "price"
                )
                or 0
            )
            if alt_price > item_price:
                effective_price = alt_price
                subtotal_buffer += (alt_price - item_price) * (
                    item.quantity or 0
                )

        item_qty = item.quantity or 0
        item_tax = (effective_price * (product_doc.tax or 0) / 100) * item_qty
        item_discount = (
            effective_price * (item.discount_percentage or 0) / 100
        ) * item_qty

        item_total = (effective_price * item_qty) - item_discount + item_tax

        product_total += effective_price * item_qty
        product_tax += item_tax
        discount += item_discount

        calculated_products.append(
            {
                "id": product_doc.name,
                "price": effective_price,
                "original_price": item_price,
                "qty": item_qty,
                "tax": item_tax,
                "shop_tax": 0,  # Placeholder or specific shop tax per item
                "discount": item_discount,
                "price_without_tax": effective_price,
                "total_price": item_total,
                "is_buffered": effective_price > item_price,
            }
        )

    # 2. Calculate Delivery Fee
    delivery_fee = 0
    if delivery_type == "Delivery" and address:
        from math import radians, sin, cos, sqrt, atan2

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Radius of Earth in kilometers
            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            lat1 = radians(lat1)
            lat2 = radians(lat2)
            a = sin(dLat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dLon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            return R * c

        # Shop coordinates live in the location JSON field; the Shop
        # doctype has no latitude/longitude columns.
        from rcore.merchants.api.shop.shop import get_shop_coords

        shop_lat, shop_lon = get_shop_coords(shop)

        # The address arrives client-supplied (JSON string or dict) and
        # may carry string coordinates; coerce defensively — an
        # unparseable address means no distance fee, not a 500.
        addr_lat = addr_lon = None
        try:
            addr_lat = float(address.get("latitude"))
            addr_lon = float(address.get("longitude"))
        except (TypeError, ValueError, AttributeError):
            addr_lat = addr_lon = None

        if (
            shop_lat is not None
            and shop_lon is not None
            and addr_lat
            and addr_lon
        ):
            distance = haversine(
                shop_lat,
                shop_lon,
                addr_lat,
                addr_lon,
            )
            delivery_fee = (
                distance * shop.price_per_km if shop.price_per_km else 0
            )

    # 3. Calculate Shop Tax
    # Total tax on the whole order from the shop's tax setting
    shop_tax = (product_total - discount) * (shop.tax / 100) if shop.tax else 0

    # 4. Get Service Fee from Permission Settings
    paas_settings = frappe.get_single("Permission Settings")
    service_fee = paas_settings.service_fee or 0

    # 5. Apply Coupon
    coupon_price = 0
    if coupon_code:
        try:
            # Check for coupon linked to this shop or global
            coupon_doc = frappe.db.get_value(
                "Coupon",
                {"coupon_code": coupon_code, "shop": cart.shop},
                [
                    "name",
                    "coupon_type",
                    "discount_percentage",
                    "discount_amount",
                ],
                as_dict=True,
            )
            if coupon_doc:
                if coupon_doc.coupon_type == "Percentage":
                    coupon_price = (product_total - discount) * (
                        coupon_doc.discount_percentage / 100
                    )
                else:  # Fixed Amount
                    coupon_price = coupon_doc.discount_amount
        except Exception:
            pass

    # 6. Calculate Final Total
    order_total = (
        (product_total - discount)
        + delivery_fee
        + shop_tax
        + service_fee
        - coupon_price
        + float(tips)
    )

    # Return in the format expected by GetCalculateModel
    return api_response(
        data={
            "total_tax": product_tax,
            "price": product_total,
            "total_shop_tax": shop_tax,
            "total_price": max(order_total, 0),
            "total_discount": discount + coupon_price,
            "delivery_fee": delivery_fee,
            "service_fee": service_fee,
            "tips": float(tips),
            "coupon_price": coupon_price,
            "subtotal_buffer": subtotal_buffer,
        }
    )
