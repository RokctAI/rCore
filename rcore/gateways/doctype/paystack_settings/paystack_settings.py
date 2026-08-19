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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import requests
from frappe import _
from frappe.model.document import Document

from rcore.gateways.utils import create_payment_gateway


class PaystackSettings(Document):
    # Upstream gateway-controller convention (razorpay/stripe precedent):
    # currencies Paystack can charge in.
    supported_currencies = ("NGN", "USD", "GHS", "ZAR", "KES")

    def validate(self):
        # Singleton convention: no gateway_settings/gateway_controller on the
        # Payment Gateway record, so get_payment_gateway_controller() resolves
        # it as frappe.get_doc("Paystack Settings"). Replaces the old
        # after_insert write of a python dotted path into gateway_controller,
        # which upstream's resolver could not read.
        create_payment_gateway("Paystack")

    def validate_transaction_currency(self, currency):
        if currency not in self.supported_currencies:
            frappe.throw(
                _(
                    "Please select another payment method. Paystack does not support transactions in currency '{0}'"
                ).format(currency)
            )

    def charge_customer(self, customer_email, amount_in_base_unit, currency, **kwargs):
        """
        Charges a customer using their saved payment token (authorization code) on Paystack. Tenant context trace.
        """
        secret_key = self.get_password("secret_key")
        if not secret_key:
            return {
                "success": False,
                "message": "Paystack secret key is not configured.",
            }

        customer = frappe.get_doc(
            "Customer", {"customer_primary_email": customer_email}
        )
        auth_code = customer.get("paystack_authorization_code")
        if not auth_code:
            return {
                "success": False,
                "message": f"No Paystack authorization code found for customer {customer.name}.",
            }

        amount_in_kobo = int(float(amount_in_base_unit) * 100)
        base_url = "https://api.paystack.co"

        headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": customer_email,
            "amount": amount_in_kobo,
            "authorization_code": auth_code,
            "currency": currency,
        }
        url = f"{base_url}/transaction/charge_authorization"

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()

            if (
                response_data.get("status")
                and response_data.get("data", {}).get("status") == "success"
            ):
                return {"success": True, "message": "Payment successful."}
            else:
                failure_reason = response_data.get("data", {}).get(
                    "gateway_response", "Unknown reason."
                )
                return {
                    "success": False,
                    "message": f"Payment failed: {failure_reason}",
                }

        except requests.exceptions.RequestException as e:
            frappe.log_error(
                f"Paystack API request failed: {e}", "Paystack Integration Error"
            )
            return {"success": False, "message": f"Failed to connect to Paystack: {e}"}
        except Exception as e:
            frappe.log_error(
                f"An unexpected error occurred during Paystack charge: {e}",
                "Paystack Integration Error",
            )
            return {"success": False, "message": f"An unexpected error occurred: {e}"}

    def get_payment_url(self, **kwargs):
        """
        Creates an Integration Request and returns the URL for the Paystack checkout page.
        """
        # Create an Integration Request to hold the payment details
        integration_request = frappe.get_doc(
            {
                "doctype": "Integration Request",
                "integration_type": "Remote",
                "integration_request_service": "Paystack",
                "request_description": kwargs.get("description"),
                "data": frappe.as_json(kwargs),
            }
        )
        integration_request.insert(ignore_permissions=True)
        frappe.db.commit()

        # Return the URL to our custom checkout page, passing the token
        return f"/paystack_checkout?token={integration_request.name}"


@frappe.whitelist()
def verify_transaction_and_get_auth(reference: str) -> dict:
    """
    Verifies a transaction using the reference from Paystack's frontend.
    If successful, returns the authorization details. This is kept as a standalone
    function because it's called directly from a whitelisted API, not from the controller instance.

    :param reference: The transaction reference from Paystack.
    :return: A dictionary with the result.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "paystack-verify-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] verify_transaction_and_get_auth called for {reference}\n")
    settings = frappe.get_doc("Paystack Settings")
    secret_key = settings.get_password("secret_key")
    base_url = "https://api.paystack.co"

    if not secret_key:
        return {"success": False, "message": "Paystack secret key is not configured."}

    headers = {"Authorization": f"Bearer {secret_key}"}
    url = f"{base_url}/transaction/verify/{reference}"

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json().get("data", {})

        if data.get("status") == "success" and data.get("authorization"):
            return {
                "success": True,
                "authorization": data.get("authorization"),
                "customer_email": data.get("customer", {}).get("email"),
            }
        else:
            return {
                "success": False,
                "message": data.get("gateway_response", "Verification failed."),
            }

    except requests.exceptions.RequestException as e:
        frappe.log_error(
            f"Paystack API request failed: {e}", "Paystack Integration Error"
        )
        return {"success": False, "message": f"Failed to connect to Paystack: {e}"}
    except Exception as e:
        frappe.log_error(
            f"An unexpected error occurred during Paystack verification: {e}",
            "Paystack Integration Error",
        )
        return {"success": False, "message": f"An unexpected error occurred: {e}"}
