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
from rcore.base.api.utils import api_response


@frappe.whitelist()
def create_parcel_order(order_data: Any) -> Any:
    """
    The create_parcel_order function creates a new parcel order from a flexible payload. It takes one parameter, order_data, which is a JSON string or dictionary containing parcel details. The function checks for idempotency, handles different destination types, and links orders and parcel options if provided. It returns the newly created parcel order document. The order_data parameter should include relevant information such as total price, currency, parcel type, and destination details. If the user is not logged in, the function throws an authentication error.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Creates a new parcel order from a flexible payload.
    'order_data' is a JSON string or dict with parcel details.
    """
    if isinstance(order_data, str):
        order_data = json.loads(order_data)

    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a parcel order.",
            frappe.AuthenticationError,
        )

    # 1. Idempotency Check (Offline UUID)
    offline_uuid = order_data.get("offline_uuid")
    if offline_uuid:
        existing_order = frappe.db.exists(
            "Parcel Order", {"offline_uuid": offline_uuid}
        )
        if existing_order:
            return api_response(
                data=frappe.get_doc("Parcel Order", existing_order).as_dict(),
                message="Duplicate order detected. Returning existing order.",
            )

    # Get Permission Settings for auto-approval
    paas_settings = frappe.get_single("Permission Settings")
    initial_status = (
        "Accepted" if paas_settings.auto_approve_parcel_orders else "New"
    )

    # Start building the new parcel document
    new_parcel_doc = {
        "doctype": "Parcel Order",
        "user": user,
        "status": initial_status,
        "total_price": order_data.get("total_price"),
        "currency": order_data.get("currency"),
        # Mapped from 'type' to 'parcel_type'
        "parcel_type": order_data.get("type"),
        "note": order_data.get("note"),
        "tax": order_data.get("tax"),
        "phone_from": order_data.get("phone_from"),
        "username_from": order_data.get("username_from"),
        "phone_to": order_data.get("phone_to"),
        "username_to": order_data.get("username_to"),
        "delivery_fee": order_data.get("delivery_fee"),
        "delivery_date": order_data.get("delivery_date"),
        "delivery_time": order_data.get("delivery_time"),
        # Default address values, can be overwritten by destination logic
        "address_from": json.dumps(order_data.get("address_from")),
        "address_to": json.dumps(order_data.get("address_to")),
        "offline_uuid": offline_uuid,
        # Intercity provider fields (default last_mile keeps existing flow)
        "fulfilment_mode": order_data.get("fulfilment_mode") or "last_mile",
        "declared_value": order_data.get("declared_value"),
        "cod_amount": order_data.get("cod_amount"),
    }

    # Handle different destination types
    destination_type = order_data.get("destination_type")

    if destination_type == "customer" and order_data.get("customer_id"):
        customer = frappe.get_doc("User", order_data.get("customer_id"))
        new_parcel_doc["username_to"] = customer.get("full_name")
        new_parcel_doc["phone_to"] = customer.get("phone")
        new_parcel_doc["address_to"] = f"Customer: {customer.get('full_name')}"

    elif destination_type == "delivery_point" and order_data.get(
        "delivery_point_id"
    ):
        delivery_point = frappe.get_doc(
            "Delivery Point", order_data.get("delivery_point_id")
        )
        new_parcel_doc["delivery_point"] = delivery_point.name
        new_parcel_doc["address_to"] = delivery_point.address
        new_parcel_doc["username_to"] = f"Pickup Point: {delivery_point.name}"

    elif destination_type == "custom_location" and order_data.get(
        "address_to"
    ):
        new_parcel_doc["address_to"] = json.dumps(order_data.get("address_to"))

    # Link Order if provided
    if order_data.get("sales_order_id"):
        new_parcel_doc["order"] = order_data.get("sales_order_id")
    elif order_data.get("order_id"):
        new_parcel_doc["order"] = order_data.get("order_id")

    # Link Parcel Option if provided
    if order_data.get("parcel_option_id"):
        new_parcel_doc["parcel_option"] = order_data.get("parcel_option_id")

    # Create the parcel order document
    parcel_order = frappe.get_doc(new_parcel_doc)

    # Handle Items Child Table
    items = order_data.get("items")
    if items and isinstance(items, list):
        for item in items:
            parcel_order.append(
                "items",
                {
                    "item": item.get("item_code") or item.get("item"),
                    "quantity": item.get("quantity", 1),
                    "item_name": item.get("item_name"),
                },
            )

    # Insert the document and return it
    parcel_order.insert(ignore_permissions=True)

    # Intercity parcels are booked with the configured logistics provider.
    # Inert by default: while intercity is disabled or unconfigured this
    # throws, rolling back the insert -- no provider call is ever made.
    if parcel_order.get("fulfilment_mode") == "intercity":
        from rcore.delivery.api.intercity.intercity import book_intercity_parcel

        book_intercity_parcel(parcel_order)

    return api_response(
        data=parcel_order.as_dict(), message="Parcel Order Created"
    )


@frappe.whitelist()
def get_parcel_orders(limit: Any=20, offset: Any=0, status: Any=None) -> Any:
    """
    Retrieves a paginated list of parcel orders for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view parcel orders.",
            frappe.AuthenticationError,
        )

    filters = {"user": user}
    if status:
        if isinstance(status, str) and "[" in status:
            import json

            try:
                filters["status"] = ["in", json.loads(status)]
            except Exception:
                filters["status"] = status
        elif isinstance(status, list):
            filters["status"] = ["in", status]
        else:
            filters["status"] = status

    parcel_orders = frappe.get_list(
        "Parcel Order",
        filters=filters,
        fields=[
            "name",
            "status",
            "delivery_date",
            "total_price",
            "address_to",
            "delivery_point",
            "order",
        ],
        limit=limit,
        offset=offset,
        order_by="modified desc",
    )

    return api_response(data=parcel_orders)


@frappe.whitelist()
def get_user_parcel_order(name: Any) -> Any:
    """
    Retrieves a single parcel order for the current user.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view a parcel order.",
            frappe.AuthenticationError,
        )

    try:
        parcel_order = frappe.get_doc("Parcel Order", name)
        if parcel_order.user != user:
            frappe.throw(
                "You are not authorized to view this parcel order.",
                frappe.PermissionError,
            )
        return api_response(data=parcel_order.as_dict())
    except frappe.DoesNotExistError:
        frappe.throw(
            f"Parcel Order {name} not found.", frappe.DoesNotExistError
        )


@frappe.whitelist()
def update_parcel_status(parcel_order_id: Any, status: Any) -> Any:
    """
    Updates the status of a specific parcel order with state machine validation and role checks.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to update a parcel order.",
            frappe.AuthenticationError,
        )

    try:
        parcel_order = frappe.get_doc("Parcel Order", parcel_order_id)
        current_status = parcel_order.status

        # Define allowed transitions
        allowed_transitions = {
            "New": ["Accepted", "Canceled"],
            "Accepted": ["Ready", "Canceled"],
            "Ready": ["On a way"],
            "On a way": ["Delivered"],
            "Delivered": [],
            "Canceled": [],
        }

        # Check if transition is valid (skip check for Admins to allow manual
        # overrides)
        if (
            "System Manager" not in frappe.get_roles()
            and "Administrator" not in frappe.get_roles()
        ):
            if status not in allowed_transitions.get(current_status, []):
                frappe.throw(
                    f"Invalid status transition from {current_status} to {status}.")

        # Role-Based Authorization
        if (
            "System Manager" in frappe.get_roles()
            or "Administrator" in frappe.get_roles()
        ):
            pass  # Admins can do anything

        elif "Deliveryman" in frappe.get_roles():
            if current_status == "Ready" and status == "On a way":
                pass
            elif current_status == "On a way" and status == "Delivered":
                pass
            else:
                frappe.throw(
                    "Deliveryman is not authorized for this status change.",
                    frappe.PermissionError,
                )

        elif parcel_order.user == user:
            if current_status == "New" and status == "Canceled":
                pass
            else:
                frappe.throw(
                    "Users can only cancel New orders.", frappe.PermissionError
                )

        else:
            frappe.throw(
                "You are not authorized to update this parcel order.",
                frappe.PermissionError,
            )

        parcel_order.status = status
        parcel_order.save(ignore_permissions=True)

        return api_response(
            data=parcel_order.as_dict(), message="Status Updated"
        )
    except frappe.DoesNotExistError:
        frappe.throw(
            f"Parcel Order {parcel_order_id} not found.",
            frappe.DoesNotExistError,
        )
    except Exception as e:
        frappe.throw(f"An error occurred: {str(e)}")


@frappe.whitelist(allow_guest=True)
def get_types() -> Any:
    """
    Retrieves all available Parcel Types (Parcel Order Settings).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    types = frappe.get_all(
        "Parcel Order Setting",
        fields=["name", "type", "img", "price", "price_per_km"],
        order_by="name asc",
    )
    return api_response(data=types)


def haversine(lat1, lon1, lat2, lon2):
    from rcore.base.api.utils import haversine as _haversine

    return _haversine(lat1, lon1, lat2, lon2)


@frappe.whitelist(allow_guest=True)
def calculate_price(type_id: Any, address_from: Any, address_to: Any) -> Any:
    """
    Calculates the delivery price based on distance and parcel type settings.
    address_from/to: JSON strings or dicts with latitude/longitude.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(address_from, str):
        address_from = json.loads(address_from)
    if isinstance(address_to, str):
        address_to = json.loads(address_to)

    try:
        lat1 = float(address_from.get("latitude") or address_from.get("lat"))
        lon1 = float(address_from.get("longitude") or address_from.get("long"))
        lat2 = float(address_to.get("latitude") or address_to.get("lat"))
        lon2 = float(address_to.get("longitude") or address_to.get("long"))
    except (ValueError, TypeError, AttributeError):
        # Fallback if coordinates missing or invalid
        return api_response(
            data={
                "price": 0,
                "km": 0,
                "status": "error",
                "message": "Invalid coordinates",
            }
        )

    km = haversine(lat1, lon1, lat2, lon2)

    # Fetch rates from Parcel Order Setting
    setting = frappe.get_doc("Parcel Order Setting", type_id)
    base_price = float(setting.price or 0)
    per_km = float(setting.price_per_km or 0)

    total_price = base_price + (km * per_km)

    return api_response(
        data={
            "price": round(total_price, 2),
            "delivery_fee": round(km * per_km, 2),
            "km": round(km, 2),
            "time": f"{max(15, int(km * 3))}-{max(20, int(km * 4))} min",
        }
    )


@frappe.whitelist()
def add_parcel_review(parcel_id: str, rating: int, review: str=None) -> Any:
    """
    Adds a review to a completed parcel order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    parcel = frappe.get_doc("Parcel Order", parcel_id)
    if parcel.status != "Delivered":
        frappe.throw("Cannot review an undelivered parcel.")

    parcel.rating = rating
    if review:
        parcel.review = review
    parcel.save(ignore_permissions=True)
    return {"status": "success"}


# Aliases for backward compatibility or hook mapping
get_parcel_categories = get_types
get_parcel_calculate = calculate_price
# Assuming flow or placeholder needed
initiate_parcel_payment = create_parcel_order
