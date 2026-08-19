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


@frappe.whitelist(allow_guest=True)
def get_receipts(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of receipts, formatted for frontend compatibility.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    receipts = frappe.get_list(
        "Receipt", fields=["*"], offset=limit_start, limit=limit_page_length
    )

    # This is a simplified representation. A full implementation would
    # need to replicate the complex price calculation and relationship loading
    # from the original Laravel RestReceiptResource.

    return receipts


@frappe.whitelist(allow_guest=True)
def get_receipt(id: str) -> Any:
    """
    Retrieves a single receipt.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    receipt = frappe.get_doc("Receipt", id)

    # Again, this is a simplified representation.
    return receipt.as_dict()
