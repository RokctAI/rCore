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
def get_parcel_order_settings() -> Any:
    """
    Retrieves a list of all active Parcel Order Settings.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        settings = frappe.get_list(
            "Parcel Order Setting",
            fields=[
                "name",
                "type",
                "img",
                "min_width",
                "max_width",
                "min_height",
                "max_height",
                "min_length",
                "max_length",
                "max_range",
                "min_g",
                "max_g",
                "price",
                "price_per_km",
                "special",
                "special_price",
                "special_price_per_km",
            ],
            order_by="price asc",
        )
        return settings
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "get_parcel_order_settings Error"
        )
        frappe.throw(
            f"An error occurred while fetching parcel order settings: {
                str(e)}"
        )


@frappe.whitelist()
def create_parcel_order_setting(setting_data: Any) -> Any:
    """
    Creates a new Parcel Order Setting.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        if isinstance(setting_data, str):
            setting_data = frappe.parse_json(setting_data)

        doc = frappe.get_doc(
            {"doctype": "Parcel Order Setting", **setting_data}
        )
        doc.insert()
        return doc.as_dict()
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "create_parcel_order_setting Error"
        )
        frappe.throw(f"An error occurred while creating parcel order setting: {
            str(e)}")


@frappe.whitelist()
def update_parcel_order_setting(name: Any, setting_data: Any) -> Any:
    """
    Updates an existing Parcel Order Setting.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        if isinstance(setting_data, str):
            setting_data = frappe.parse_json(setting_data)

        doc = frappe.get_doc("Parcel Order Setting", name)
        doc.update(setting_data)
        doc.save()
        return doc.as_dict()
    except frappe.DoesNotExistError:
        frappe.throw(
            "Parcel Order Setting not found", frappe.DoesNotExistError
        )
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "update_parcel_order_setting Error"
        )
        frappe.throw(f"An error occurred while updating parcel order setting: {
            str(e)}")


@frappe.whitelist()
def delete_parcel_order_setting(name: Any) -> Any:
    """
    Deletes a Parcel Order Setting.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        frappe.delete_doc("Parcel Order Setting", name)
        return {
            "status": "success",
            "message": "Parcel Order Setting deleted successfully",
        }
    except frappe.DoesNotExistError:
        frappe.throw(
            "Parcel Order Setting not found", frappe.DoesNotExistError
        )
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(), "delete_parcel_order_setting Error"
        )
        frappe.throw(f"An error occurred while deleting parcel order setting: {
            str(e)}")
