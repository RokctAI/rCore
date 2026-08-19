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


@frappe.whitelist(allow_guest=True)
def get_parcel_options() -> Any:
    """
    Retrieves a list of all active Parcel Options.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        options = frappe.get_list(
            "Parcel Option",
            filters={"active": 1},
            fields=["name", "title", "description", "price"],
            order_by="price asc",
        )
        return options
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_parcel_options Error")
        frappe.throw(f"An error occurred while fetching parcel options: {
            str(e)}")


@frappe.whitelist()
def create_parcel_option(option_data: Any) -> Any:
    """
    Creates a new Parcel Option.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        if isinstance(option_data, str):
            option_data = frappe.parse_json(option_data)

        doc = frappe.get_doc({"doctype": "Parcel Option", **option_data})
        doc.insert()
        return doc.as_dict()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_parcel_option Error")
        frappe.throw(f"An error occurred while creating parcel option: {
            str(e)}")


@frappe.whitelist()
def update_parcel_option(name: Any, option_data: Any) -> Any:
    """
    Updates an existing Parcel Option.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        if isinstance(option_data, str):
            option_data = frappe.parse_json(option_data)

        doc = frappe.get_doc("Parcel Option", name)
        doc.update(option_data)
        doc.save()
        return doc.as_dict()
    except frappe.DoesNotExistError:
        frappe.throw("Parcel Option not found", frappe.DoesNotExistError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_parcel_option Error")
        frappe.throw(f"An error occurred while updating parcel option: {
            str(e)}")


@frappe.whitelist()
def delete_parcel_option(name: Any) -> Any:
    """
    Deletes a Parcel Option.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        frappe.delete_doc("Parcel Option", name)
        return {
            "status": "success",
            "message": "Parcel Option deleted successfully",
        }
    except frappe.DoesNotExistError:
        frappe.throw("Parcel Option not found", frappe.DoesNotExistError)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "delete_parcel_option Error")
        frappe.throw(f"An error occurred while deleting parcel option: {
            str(e)}")
