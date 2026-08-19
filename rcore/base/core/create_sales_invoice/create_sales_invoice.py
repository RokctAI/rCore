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
import os
import json
import pytz
import requests
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import validate_email_address, get_url, nowdate
from frappe.utils.data import add_days, getdate
from frappe.utils.install import complete_setup_wizard
from rcore.comms.tenant_utils import send_tenant_email
from rcore.tenant.api.helpers import *


def create_sales_invoice(invoice_data: Any, recurring: Any=False, frequency: Any=None, end_date: Any=None) -> Any:
    """
    Creates a new Sales Invoice and, optionally, sets up a recurring schedule for it.
    """
    if frappe.conf.get("app_role") != "tenant":
        frappe.throw(
            "This action can only be performed on a tenant site.",
            title="Action Not Allowed",
        )

    # --- Input Validation ---
    if (
        not isinstance(invoice_data, dict)
        or not invoice_data.get("customer")
        or not invoice_data.get("items")
    ):
        frappe.throw(
            "`invoice_data` must be a dictionary containing at least 'customer' and 'items'.",
            title="Invalid Input",
        )

    if recurring:
        if not frequency or not end_date:
            frappe.throw(
                "`frequency` and `end_date` are required for recurring invoices.",
                title="Missing Information",
            )
        allowed_frequencies = [
            "Daily",
            "Weekly",
            "Monthly",
            "Quarterly",
            "Half-yearly",
            "Yearly",
        ]
        if frequency not in allowed_frequencies:
            frappe.throw(
                f"Invalid frequency. Must be one of {', '.join(allowed_frequencies)}.",
                title="Invalid Input",
            )
    # --- End Validation ---

    try:
        invoice_doc = frappe.get_doc(invoice_data)
        invoice_doc.insert(ignore_permissions=False)
        invoice_doc.submit()

        response_data = {"invoice_name": invoice_doc.name}
        if recurring:
            auto_repeat = frappe.get_doc(
                {
                    "doctype": "Auto Repeat",
                    "reference_doctype": "Sales Invoice",
                    "reference_document": invoice_doc.name,
                    "frequency": frequency,
                    "end_date": end_date,
                }
            ).insert(ignore_permissions=False)
            auto_repeat.submit()
            response_data["auto_repeat_name"] = auto_repeat.name
            response_data["message"] = f"Sales Invoice {invoice_doc.name} created and scheduled for recurring generation."
        else:
            response_data["message"] = (
                f"Sales Invoice {invoice_doc.name} created successfully."
            )

        frappe.db.commit()
        return response_data

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Failed to create Sales Invoice")
        frappe.throw(f"An error occurred while creating the Sales Invoice: {e}")
