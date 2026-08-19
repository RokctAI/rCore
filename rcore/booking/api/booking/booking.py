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
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

# Helper Functions


def check_shop_permission(shop_id, role):
    """Check if the current user has permission for a given shop."""
    user = frappe.session.user
    if frappe.has_role("System Manager"):
        return

    # Assuming Shop User logic exists or will be implemented.
    # If Shop User doctype doesn't exist yet, this might fail.
    # For now, we'll keep the check but be aware.
    if not frappe.db.exists(
            "Shop User", {
            "user": user, "shop": shop_id, "role": role}):
        frappe.throw(
            f"You are not authorized to manage this shop's "
            f"{role.lower()} bookings.",
            frappe.PermissionError)


def check_availability(
        shop_id,
        table_id,
        start_date,
        end_date,
        exclude_reservation_id=None):
    """
    Check if a table is available for the given time range.
    Returns True if available, False otherwise.
    """
    filters = {
        "table": table_id,
        "status": ["in", ["New", "Accepted"]],
        "start_date": ["<", end_date],
        "end_date": [">", start_date]
    }

    if exclude_reservation_id:
        filters["name"] = ["!=", exclude_reservation_id]

    overlapping_reservations = frappe.get_all("User Booking", filters=filters)

    return len(overlapping_reservations) == 0

# Admin/Seller Booking Slot Management (The 'Booking' DocType)


@frappe.whitelist()
def create_booking_slot(data: Any) -> Any:
    """Create a new booking slot (shift)."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    # Permission check: Admin or Seller of the shop
    data = frappe._dict(data)
    if not frappe.has_permission("Booking", "create"):
        # Fallback to shop permission check if not system admin
        if data.get("shop"):
            check_shop_permission(data.get("shop"), "Seller")
        else:
            frappe.throw("Not permitted", frappe.PermissionError)

    data["doctype"] = "Booking"
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_booking_slots(shop_id: Any) -> Any:
    """Get all booking slots for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    # Publicly accessible? Or restricted? Assuming public for now so users can
    # see slots.
    return frappe.get_list(
        "Booking",
        filters={
            "shop": shop_id,
            "active": 1},
        fields=["*"])


@frappe.whitelist()
def update_booking_slot(name: Any, data: Any) -> Any:
    """Update a booking slot."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Booking", "write"):
        doc = frappe.get_doc("Booking", name)
        check_shop_permission(doc.shop, "Seller")

    doc = frappe.get_doc("Booking", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_booking_slot(name: Any) -> Any:
    """Delete a booking slot."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Booking", "delete"):
        doc = frappe.get_doc("Booking", name)
        check_shop_permission(doc.shop, "Seller")

    frappe.delete_doc("Booking", name)
    return {
        "status": "success",
        "message": "Booking slot deleted successfully"}

# Reservation Management (The 'User Booking' DocType)


@frappe.whitelist()
def create_reservation(data: Any) -> Any:
    """Create a new user reservation."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to create a booking.",
            frappe.PermissionError)

    booking_data = frappe._dict(data)

    # Validation
    if not booking_data.get("table"):
        frappe.throw("Table is required.")
    if not booking_data.get("start_date") or not booking_data.get("end_date"):
        frappe.throw("Start and End dates are required.")

    start_date = get_datetime(booking_data.get("start_date"))
    end_date = get_datetime(booking_data.get("end_date"))

    if start_date >= end_date:
        frappe.throw("End date must be after start date.")

    # Check Availability
    # We need to know the shop_id. It can be fetched from the Booking Slot or
    # Table.
    table = frappe.get_doc("Table", booking_data.get("table"))
    shop_section = frappe.get_doc("Shop Section", table.shop_section)
    shop_id = shop_section.shop

    if not check_availability(
            shop_id,
            booking_data.get("table"),
            start_date,
            end_date):
        frappe.throw(
            "The selected table is not available for the chosen time.")

    booking_data.user = user
    booking_data.doctype = "User Booking"
    booking_data.status = "New"

    doc = frappe.get_doc(booking_data)
    doc.insert(ignore_permissions=True)
    return doc


@frappe.whitelist()
def get_my_reservations() -> Any:
    """Get the current user's reservations."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(
            "You must be logged in to view your bookings.",
            frappe.PermissionError)

    return frappe.get_list(
        "User Booking",
        filters={
            "user": user},
        fields=["*"],
        order_by="start_date desc")


@frappe.whitelist()
def get_shop_reservations(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """Get all reservations for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    _filters = {"booking.shop": shop_id}
    # Wait, UserBooking links to Booking (Slot). Booking (Slot) has Shop.
    # So we can filter by booking.shop if standard queries support it, or we filter manually.
    # Frappe get_list supports child table filtering but this is a Link.
    # We might need to query User Booking where booking in (select name from
    # Booking where shop=shop_id)

    # Alternative: User Booking -> Table -> Shop Section -> Shop.
    # Let's use Table -> Shop Section -> Shop as it's more direct for the
    # physical location.

    # Fetch tables for the shop
    shop_sections = frappe.get_all(
        "Shop Section", filters={
            "shop": shop_id}, pluck="name")
    tables = frappe.get_all(
        "Table",
        filters={
            "shop_section": [
                "in",
                shop_sections]},
        pluck="name")

    if not tables:
        return []

    res_filters = {"table": ["in", tables]}
    if status:
        res_filters["status"] = status
    if date_from:
        res_filters["start_date"] = [">=", date_from]
    if date_to:
        res_filters["end_date"] = ["<=", date_to]

    return frappe.get_list(
        "User Booking",
        filters=res_filters,
        fields=["*"],
        order_by="start_date desc")


@frappe.whitelist()
def update_reservation_status(name: Any, status: Any) -> Any:
    """Update the status of a reservation."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    doc = frappe.get_doc("User Booking", name)

    # Permission check: User can cancel their own. Seller can accept/reject.
    user = frappe.session.user

    if user == doc.user:
        if status == "Cancelled":
            doc.status = "Cancelled"
            doc.save(ignore_permissions=True)
            return doc
        else:
            frappe.throw(
                "You can only cancel your own booking.",
                frappe.PermissionError)

    # Check if user is seller for this shop
    # Need to traverse to Shop ID
    table = frappe.get_doc("Table", doc.table)
    shop_section = frappe.get_doc("Shop Section", table.shop_section)
    check_shop_permission(shop_section.shop, "Seller")

    doc.status = status
    doc.save(ignore_permissions=True)
    return doc

# Admin Shop Section & Table Management (Kept mostly same)


@frappe.whitelist()
def create_shop_section(data: Any) -> Any:
    """
    The create_shop_section function is used to create a new shop section in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create a shop section. The function first checks if the current user has permission to create a shop section, throwing a PermissionError if they do not. If permission is granted, it creates a new document based on the provided data and inserts it into the system, returning the newly created document.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_shop_section(name: Any) -> Any:
    """
    The get_shop_section function retrieves a specific shop section document from the database. It takes one parameter, name, which is the name of the shop section to be retrieved. This function utilizes the frappe framework to fetch the document, allowing for easy access to the shop section's details.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_doc("Shop Section", name)


@frappe.whitelist()
def update_shop_section(name: Any, data: Any) -> Any:
    """
    The update_shop_section function updates an existing shop section document with new data. It takes two parameters: name, which is the name of the shop section to be updated, and data, which is a dictionary containing the new data to be applied to the shop section. The function first checks if the user has write permission for the shop section, throwing a permission error if not. If permission is granted, it retrieves the shop section document, updates it with the provided data, saves the changes, and returns the updated document.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Shop Section", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_shop_section(name: Any) -> Any:
    """
    The delete_shop_section function is used to delete a specific shop section from the system. It takes one parameter, name, which represents the name of the shop section to be deleted. The function first checks if the user has the necessary permission to delete a shop section, and if not, it throws a permission error. If the user has permission, it proceeds to delete the shop section with the specified name and returns a success status along with a confirmation message.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Shop Section", "delete"):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.delete_doc("Shop Section", name)
    return {
        "status": "success",
        "message": "Shop Section deleted successfully"}


@frappe.whitelist()
def create_table(data: Any) -> Any:
    """
    The create_table function is used to create a new table in the system. It takes one parameter, data, which is expected to be a dictionary containing the necessary information to create the table. The function first checks if the user has the necessary permission to create a table, throwing a PermissionError if they do not. If permission is granted, it retrieves the document using the provided data, inserts it into the system, and returns the newly created document.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Table", "create"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc(data)
    doc.insert()
    return doc


@frappe.whitelist()
def get_table(name: Any) -> Any:
    """
    The get_table function retrieves a specific table document from the database. It takes one parameter, name, which represents the name of the table to be retrieved. The function utilizes the frappe framework to fetch the table document, returning the result as a document object.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_doc("Table", name)


@frappe.whitelist()
def update_table(name: Any, data: Any) -> Any:
    """
    The update_table function updates an existing table document in the database. It takes two parameters: name, which specifies the name of the table to be updated, and data, which contains the new data to be applied to the table. The function first checks if the user has write permission for the table, throwing a permission error if not. If permitted, it retrieves the table document, applies the updates, saves the changes, and returns the updated document.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Table", "write"):
        frappe.throw("Not permitted", frappe.PermissionError)
    doc = frappe.get_doc("Table", name)
    doc.update(data)
    doc.save()
    return doc


@frappe.whitelist()
def delete_table(name: Any) -> Any:
    """
    The delete_table function is used to delete a table from the database. It takes one parameter, name, which specifies the name of the table to be deleted. The function first checks if the user has permission to delete tables, and if not, it throws a permission error. If the user has permission, it deletes the table with the specified name and returns a success message.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not frappe.has_permission("Table", "delete"):
        frappe.throw("Not permitted", frappe.PermissionError)
    frappe.delete_doc("Table", name)
    return {"status": "success", "message": "Table deleted successfully"}


@frappe.whitelist()
def get_shop_sections_for_booking(shop_id: Any) -> Any:
    """Get all shop sections for a specific shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_list(
        "Shop Section", filters={
            "shop": shop_id}, fields=["*"])


@frappe.whitelist()
def get_tables_for_section(shop_section_id: Any) -> Any:
    """Get all tables for a specific shop section."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_list(
        "Table",
        filters={
            "shop_section": shop_section_id,
            "active": 1},
        fields=["*"])

# Shop Settings (Working Days / Closed Dates)


@frappe.whitelist()
def manage_shop_booking_working_days(shop_id: Any, working_days: Any) -> Any:
    """Manage the booking working days for a shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    shop = frappe.get_doc("Shop", shop_id)
    # Assuming Shop has a child table 'booking_working_days'
    # If not, this needs to be adapted to whatever schema exists.
    # The previous code assumed 'booking_working_days' field.
    # We should verify Shop doctype but for now we keep the logic.
    shop.booking_working_days = []
    for day in working_days:
        shop.append("booking_working_days", day)
    shop.save()
    return shop


@frappe.whitelist()
def manage_shop_booking_closed_dates(shop_id: Any, closed_dates: Any) -> Any:
    """Manage the booking closed dates for a shop."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    check_shop_permission(shop_id, "Seller")

    shop = frappe.get_doc("Shop", shop_id)
    shop.booking_closed_dates = []
    for date in closed_dates:
        shop.append("booking_closed_dates", date)
    shop.save()
    return shop

# --- Aliases for Backward Compatibility ---


@frappe.whitelist()
def create_booking(data: Any) -> Any:
    """
    The **create_booking** function serves as a simple wrapper that initiates the creation of a new booking. It accepts a single argument, **data**, which should contain all the necessary information required to define the booking (the exact structure of this data is determined by the underlying implementation of the booking system). Inside the function, the provided **data** is passed directly to **create_booking_slot**, which performs the actual booking‑slot creation and returns its result. In summary, **create_booking** offers a concise, high‑level interface for creating bookings by delegating the work to **create_booking_slot**.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_booking_slot(data)


@frappe.whitelist()
def get_booking(name: Any) -> Any:
    """
    The get_booking function retrieves a specific booking document from the database. It takes one parameter, name, which is the unique identifier of the booking to be retrieved. The function uses the frappe framework to fetch the booking document with the specified name and returns it as a document object.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_doc("Booking", name)


@frappe.whitelist()
def update_booking(name: Any, data: Any) -> Any:
    """
    The update_booking function is used to modify an existing booking. It takes two parameters: name and data. The name parameter represents the identifier of the booking to be updated, while the data parameter contains the new information to be applied to the booking. This function serves as a wrapper around the update_booking_slot function, which performs the actual update operation.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return update_booking_slot(name, data)


@frappe.whitelist()
def delete_booking(name: Any) -> Any:
    """
    The delete_booking function is used to cancel a booking by removing the associated booking slot. It takes one parameter, name, which represents the name of the booking to be deleted. This function serves as a wrapper around the delete_booking_slot function, providing a simplified interface for deleting bookings.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return delete_booking_slot(name)


@frappe.whitelist()
def create_user_booking(data: Any) -> Any:
    """
    The create_user_booking function is used to generate a new user booking by creating a reservation. It takes one parameter, data, which is expected to contain all necessary information required to create the booking, such as user details and reservation specifics. This function essentially serves as a wrapper around the create_reservation function, passing the provided data to it to complete the booking process.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return create_reservation(data)


@frappe.whitelist()
def get_user_bookings() -> Any:
    """
    The get_user_bookings function retrieves a list of bookings associated with the current user. It takes no parameters, relying on internal state to determine the user's identity. The function serves as a wrapper around the get_my_reservations function, providing a simplified interface for accessing user-specific booking data.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_my_reservations()


@frappe.whitelist()
def update_user_booking_status(name: Any, status: Any) -> Any:
    """
    The update_user_booking_status function updates the status of a user's booking in the system. It takes two parameters: name, which represents the name of the user whose booking status is to be updated, and status, which represents the new status to be assigned to the user's booking. This function serves as a wrapper around the update_reservation_status function, providing a more specific and user-centric interface for managing booking statuses.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return update_reservation_status(name, status)


@frappe.whitelist()
def get_shop_bookings(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """
    The get_shop_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their current status, while date_from and date_to allow for filtering by a specific date range. If these optional parameters are not provided, the function will return all bookings for the specified shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_shop_reservations(shop_id, status, date_from, date_to)


@frappe.whitelist()
def get_shop_user_bookings(shop_id: Any, status: Any=None, date_from: Any=None, date_to: Any=None) -> Any:
    """
    The get_shop_user_bookings function retrieves a list of bookings for a specific shop. It takes four parameters: shop_id, which is a required identifier for the shop, and three optional parameters: status, date_from, and date_to. The status parameter filters bookings by their status, while date_from and date_to filter bookings by a specific date range. The function leverages the get_shop_reservations function to fetch the relevant data, providing a simplified interface for accessing shop user bookings.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_shop_reservations(shop_id, status, date_from, date_to)


@frappe.whitelist()
def update_shop_user_booking_status(name: Any, status: Any) -> Any:
    """
    The update_shop_user_booking_status function updates the status of a user's booking at a shop. It takes two parameters: name, which represents the name of the user or booking to be updated, and status, which represents the new status to be applied to the booking. This function serves as a wrapper around the update_reservation_status function, providing a shop-specific interface for managing user bookings.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return update_reservation_status(name, status)


@frappe.whitelist()
def get_my_bookings() -> Any:
    """
    The get_my_bookings function retrieves a list of bookings associated with the current user. This function takes no parameters and returns the result of the get_my_reservations function, effectively serving as an alias for retrieving user-specific reservation data.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_my_reservations()


@frappe.whitelist()
def cancel_my_booking(name: Any) -> Any:
    """
    The cancel_my_booking function is used to cancel an existing booking by updating its reservation status. It takes one parameter, name, which represents the name associated with the booking to be cancelled. This function internally calls the update_reservation_status function, passing the provided name and the status "Cancelled" to effect the cancellation.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return update_reservation_status(name, "Cancelled")
