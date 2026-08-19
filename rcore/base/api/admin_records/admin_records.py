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
def get_all_orders(limit_start: int=0, limit_page_length: int=20, status: str=None, from_date: str=None, to_date: str=None) -> Any:
    """
    Retrieves a list of all orders on the platform (for admins).
    """
    _require_admin()

    filters = {}
    if status:
        filters["status"] = status
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]

    orders = frappe.get_list(
        "Order",
        filters=filters,
        fields=["name", "user", "shop", "grand_total", "status", "creation"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return orders


@frappe.whitelist()
def get_all_parcel_orders(limit_start: int=0, limit_page_length: int=20, status: str=None, from_date: str=None, to_date: str=None) -> Any:
    """
    Retrieves a list of all parcel orders on the platform (for admins).
    """
    _require_admin()

    filters = {}
    if status:
        filters["status"] = status
    if from_date and to_date:
        filters["creation"] = ["between", [from_date, to_date]]

    parcel_orders = frappe.get_list(
        "Parcel Order",
        filters=filters,
        fields=[
            "name",
            "user",
            "total_price",
            "status",
            "delivery_date",
            "deliveryman",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return parcel_orders


@frappe.whitelist()
def delete_admin_parcel_order(parcel_order_id: Any) -> Any:
    """
    Deletes a parcel order (for admins).
    """
    _require_admin()
    frappe.delete_doc("Parcel Order", parcel_order_id, ignore_permissions=True)
    return {
        "status": "success",
        "message": "Parcel Order deleted successfully.",
    }


@frappe.whitelist()
def assign_deliveryman_to_parcel(parcel_order_id: Any, deliveryman_id: Any) -> Any:
    """
    The assign_deliveryman_to_parcel function assigns a deliveryman to a specific parcel order. This function is restricted to admin users and requires two parameters: parcel_order_id, which is the unique identifier of the parcel order, and deliveryman_id, which is the unique identifier of the deliveryman to be assigned. The function validates the existence of the deliveryman and then updates the parcel order with the assigned deliveryman, returning the updated parcel order details.
    """
    """
    Assigns a deliveryman to a parcel order (for admins).
    """
    _require_admin()
    parcel_order = frappe.get_doc("Parcel Order", parcel_order_id)

    # Validate deliveryman exists and has role?
    # Assuming deliveryman_id is User ID.
    if not frappe.db.exists("User", deliveryman_id):
        frappe.throw(f"User {deliveryman_id} not found.")

    # Optional: Check if user has Deliveryman role.
    # For now, trust admin input.

    parcel_order.deliveryman = deliveryman_id
    parcel_order.save(ignore_permissions=True)

    return parcel_order.as_dict()


@frappe.whitelist()
def get_all_reviews(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all reviews on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Review",
        fields=[
            "name",
            "user",
            "rating",
            "comment",
            "creation",
            "reviewable_type",
            "reviewable_id",
            "published",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def update_admin_review(review_name: Any, review_data: Any) -> Any:
    """
    Updates a review (for admins).
    """
    _require_admin()
    if isinstance(review_data, str):
        review_data = json.loads(review_data)

    review = frappe.get_doc("Review", review_name)
    review.update(review_data)
    review.save(ignore_permissions=True)
    return review.as_dict()


@frappe.whitelist()
def delete_admin_review(review_name: Any) -> Any:
    """
    Deletes a review (for admins).
    """
    _require_admin()
    frappe.delete_doc("Review", review_name, ignore_permissions=True)
    return {"status": "success", "message": "Review deleted successfully."}


@frappe.whitelist()
def get_all_tickets(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all tickets on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Ticket",
        fields=["name", "subject", "status", "creation", "user"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def update_admin_ticket(ticket_name: Any, ticket_data: Any) -> Any:
    """
    Updates a ticket (for admins).
    """
    _require_admin()
    if isinstance(ticket_data, str):
        ticket_data = json.loads(ticket_data)

    ticket = frappe.get_doc("Ticket", ticket_name)
    ticket.update(ticket_data)
    ticket.save(ignore_permissions=True)
    return ticket.as_dict()


@frappe.whitelist()
def get_all_order_refunds(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all order refunds on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Order Refund",
        fields=["name", "order", "status", "cause", "answer"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def update_admin_order_refund(refund_name: Any, status: Any, answer: Any=None) -> Any:
    """
    Updates the status and answer of an order refund (for admins).
    """
    _require_admin()

    refund = frappe.get_doc("Order Refund", refund_name)

    if status not in ["Accepted", "Canceled"]:
        frappe.throw("Invalid status. Must be 'Accepted' or 'Canceled'.")

    refund.status = status
    if answer:
        refund.answer = answer

    refund.save(ignore_permissions=True)
    return refund.as_dict()


@frappe.whitelist()
def get_all_notifications(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all notifications on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Notification Log",
        fields=[
            "name",
            "subject",
            "document_type",
            "document_name",
            "for_user",
            "creation",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def get_all_bookings(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all bookings on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Booking",
        fields=[
            "name",
            "user",
            "shop",
            "booking_date",
            "number_of_guests",
            "status",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="booking_date desc",
    )


@frappe.whitelist()
def create_booking(booking_data: Any) -> Any:
    """
    Creates a new booking (for admins).
    """
    _require_admin()
    if isinstance(booking_data, str):
        booking_data = json.loads(booking_data)

    new_booking = frappe.get_doc({"doctype": "Booking", **booking_data})
    new_booking.insert(ignore_permissions=True)
    return new_booking.as_dict()


@frappe.whitelist()
def update_booking(booking_name: Any, booking_data: Any) -> Any:
    """
    Updates a booking (for admins).
    """
    _require_admin()
    if isinstance(booking_data, str):
        booking_data = json.loads(booking_data)

    booking = frappe.get_doc("Booking", booking_name)
    booking.update(booking_data)
    booking.save(ignore_permissions=True)
    return booking.as_dict()


@frappe.whitelist()
def delete_booking(booking_name: Any) -> Any:
    """
    Deletes a booking (for admins).
    """
    _require_admin()
    frappe.delete_doc("Booking", booking_name, ignore_permissions=True)
    return {"status": "success", "message": "Booking deleted successfully."}


@frappe.whitelist()
def get_all_order_statuses(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all order statuses on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Order Status",
        fields=["name", "status_name", "is_active", "sort_order"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="sort_order",
    )


@frappe.whitelist()
def get_all_request_models(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all request models on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Request Model",
        fields=[
            "name",
            "model_type",
            "model",
            "status",
            "created_by_user",
            "created_at",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
