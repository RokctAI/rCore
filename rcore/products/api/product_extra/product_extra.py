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

# --- Product Extra Group APIs ---


@frappe.whitelist()
def create_extra_group(data: Any) -> Any:
    """
    Creates a new Product Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Group", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_groups(shop_id: Any=None) -> Any:
    """
    Retrieves Extra Groups, optionally filtered by shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    filters = {}
    if shop_id:
        filters["shop"] = shop_id

    return frappe.get_list(
        "Product Extra Group", filters=filters, fields=["*"]
    )


@frappe.whitelist()
def update_extra_group(name: Any, data: Any) -> Any:
    """
    Updates an Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Group", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_group(name: Any) -> Any:
    """
    Deletes an Extra Group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    frappe.delete_doc("Product Extra Group", name)
    return {"status": "success"}


# --- Product Extra Value APIs ---


@frappe.whitelist()
def create_extra_value(data: Any) -> Any:
    """
    Creates a new Product Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Product Extra Value", **data})
    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_extra_values(group_id: Any) -> Any:
    """
    Retrieves Extra Values for a specific group.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_list(
        "Product Extra Value", filters={"extra_group": group_id}, fields=["*"]
    )


@frappe.whitelist()
def update_extra_value(name: Any, data: Any) -> Any:
    """
    Updates an Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Product Extra Value", name)
    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_extra_value(name: Any) -> Any:
    """
    Deletes an Extra Value.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    frappe.delete_doc("Product Extra Value", name)
    return {"status": "success"}
