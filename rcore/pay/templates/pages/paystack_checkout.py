# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe import _


def get_context(context):
    """
    Provides the context to the Paystack checkout page.
    This is called by the user's browser when they are redirected.
    """
    context.no_cache = 1

    # Get details from the URL query parameters
    integration_request = frappe.form_dict.get("token")
    if not integration_request:
        frappe.throw(_("Payment token not found."))

    try:
        doc = frappe.get_doc("Integration Request", integration_request)
        data = doc.get_data()

        # Get Paystack public key from settings
        settings = frappe.get_doc("Paystack Settings")
        public_key = settings.public_key
        if not public_key:
            frappe.throw(_("Paystack public key is not configured."))

        # Pass the required details to the template
        context.public_key = public_key
        context.email = data.get("payer_email")
        context.amount = int(
            float(
                data.get("amount")) *
            100)  # Convert to kobo
        context.currency = data.get("currency")
        context.reference = doc.name  # Use the integration request name as the reference

    except frappe.DoesNotExistError:
        frappe.throw(_("Invalid payment token."))
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Paystack Checkout Context Error")
        frappe.throw(_("An error occurred while preparing the payment page."))
