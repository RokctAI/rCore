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


@frappe.whitelist()
def create_stock(data: Any) -> Any:
    """
    Creates a new Stock (Variant) for a Product.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    # Extract extras if present
    extras = data.pop("extras", [])

    doc = frappe.get_doc({"doctype": "Stock", **data})

    # Add extras to child table
    for extra_value_id in extras:
        doc.append("stock_extras", {"extra_value": extra_value_id})

    doc.insert()
    return doc.as_dict()


@frappe.whitelist()
def get_product_stocks(product_id: Any) -> Any:
    """
    Retrieves all Stock variants for a Product.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return frappe.get_list(
        "Stock", filters={"product": product_id}, fields=["*"]
    )


@frappe.whitelist()
def update_stock(name: Any, data: Any) -> Any:
    """
    Updates a Stock item.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Stock", name)

    # Handle extras update if provided
    if "extras" in data:
        extras = data.pop("extras")
        doc.set("stock_extras", [])  # Clear existing
        for extra_value_id in extras:
            doc.append("stock_extras", {"extra_value": extra_value_id})

    doc.update(data)
    doc.save()
    return doc.as_dict()


@frappe.whitelist()
def delete_stock(name: Any) -> Any:
    """
    Deletes a Stock item.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    frappe.delete_doc("Stock", name)
    return {"status": "success"}
