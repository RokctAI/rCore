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
import hashlib
import ipaddress
import socket
from urllib.parse import urlencode
from frappe import _
from frappe.model.document import Document

from rcore.gateways.utils import create_payment_gateway


class PayFastSettings(Document):
    # Upstream gateway-controller convention (razorpay/stripe precedent):
    # PayFast settles in South African Rand only.
    supported_currencies = ("ZAR",)

    def validate(self):
        # Singleton convention: no gateway_settings/gateway_controller on the
        # Payment Gateway record, so get_payment_gateway_controller() resolves
        # it as frappe.get_doc("PayFast Settings"). Replaces the old
        # after_insert write of a python dotted path into gateway_controller,
        # which upstream's resolver could not read.
        create_payment_gateway("PayFast")

    def validate_transaction_currency(self, currency):
        if currency not in self.supported_currencies:
            frappe.throw(
                _(
                    "Please select another payment method. PayFast does not support transactions in currency '{0}'"
                ).format(currency)
            )

    def get_payment_url(self, **kwargs):
        """
        Constructs the PayFast redirect URL with all required parameters and a security signature.
        """
        if self.is_sandbox:
            redirect_url = "https://sandbox.payfast.co.za/eng/process"
        else:
            redirect_url = "https://www.payfast.co.za/eng/process"

        # Create an Integration Request to track the transaction
        integration_request = frappe.get_doc(
            {
                "doctype": "Integration Request",
                "integration_type": "Remote",
                "integration_request_service": "PayFast",
                "request_description": kwargs.get("description"),
                "data": frappe.as_json(kwargs),
            }
        ).insert(ignore_permissions=True)
        frappe.db.commit()

        # Prepare the data dictionary for PayFast
        payment_data = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": kwargs.get("redirect_to")
            or frappe.utils.get_url("/payment-success"),
            "cancel_url": frappe.utils.get_url("/payment-cancel"),
            "notify_url": frappe.utils.get_url(
                "/api/method/rcore.gateways.doctype.payfast_settings.payfast_settings.handle_payfast_callback"
            ),
            "name_first": kwargs.get("payer_name"),
            "email_address": kwargs.get("payer_email"),
            "m_payment_id": integration_request.name,
            "amount": str(kwargs.get("amount")),
            "item_name": kwargs.get("title"),
        }

        # Generate the signature
        passphrase = self.get_password("passphrase")

        # Create a string by concatenating the POST data
        # The data needs to be sorted by key for consistent signature
        # generation
        pf_param_string = urlencode(
            {k: str(v) for k, v in sorted(payment_data.items())}
        )

        if passphrase:
            pf_param_string += f"&passphrase={passphrase}"

        signature = hashlib.md5(pf_param_string.encode("utf-8")).hexdigest()
        payment_data["signature"] = signature

        # Append the encoded data to the redirect URL
        return f"{redirect_url}?{urlencode(payment_data)}"


def validate_payfast_ip(request_ip):
    """
    Validates if the request IP belongs to PayFast.
    Checks against known CIDR ranges and dynamically resolves PayFast domains.
    """
    # Allow localhost for testing if in developer mode
    if request_ip in ("127.0.0.1", "::1") and frappe.conf.developer_mode:
        return True

    # Known PayFast IP ranges
    valid_networks = [
        "197.97.145.144/28",
        "41.74.179.192/27",
        "102.216.36.0/28",
        "144.126.193.139/32",
    ]

    try:
        ip_obj = ipaddress.ip_address(request_ip)
        for net in valid_networks:
            if ip_obj in ipaddress.ip_network(net):
                return True
    except ValueError:
        frappe.log_error(f"Invalid IP format: {request_ip}", "PayFast IP Validation")
        return False

    # Dynamic DNS Check for GCP/New Infrastructure
    # PayFast publishes outbound IPs via A records on these domains
    domains = ["www.payfast.co.za", "sandbox.payfast.co.za", "wpes.payfast.co.za"]
    for domain in domains:
        try:
            # Use getaddrinfo to get all IPv4 addresses
            infos = socket.getaddrinfo(domain, None, family=socket.AF_INET)
            resolved_ips = set(info[4][0] for info in infos)
            if request_ip in resolved_ips:
                return True
        except Exception:
            # DNS lookup failed, continue to next domain
            pass

    return False


@frappe.whitelist(allow_guest=True)
def handle_payfast_callback() -> dict:
    """
    Handles the PayFast payment callback (notify_url).
    Verifies the payment signature and updates the Integration Request.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "payfast-callback-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] handle_payfast_callback called\n")
    data = frappe.form_dict

    # 1. Verify the source of the request
    # Get the client IP, handling proxies if configured in Frappe
    client_ip = frappe.local.request.remote_addr

    if not validate_payfast_ip(client_ip):
        frappe.log_error(
            f"PayFast callback rejected from unauthorized IP: {client_ip}",
            "PayFast Security Warning",
        )
        # Fail securely
        frappe.throw("Unauthorized Request Source", frappe.PermissionError)

    # 2. Verify the signature
    settings = frappe.get_doc("PayFast Settings")
    passphrase = settings.get_password("passphrase")

    # Create a string by concatenating the POST data
    pf_param_string = urlencode(
        {k: str(v) for k, v in sorted(data.items()) if k != "signature"}
    )

    if passphrase:
        pf_param_string += f"&passphrase={passphrase}"

    signature = hashlib.md5(pf_param_string.encode("utf-8")).hexdigest()

    if signature != data.get("signature"):
        frappe.log_error("PayFast callback signature mismatch", "PayFast Error")
        # A 400 Bad Request response is appropriate here
        frappe.throw("Signature mismatch", frappe.AuthenticationError)

    # 3. Get the Integration Request
    integration_request_name = data.get("m_payment_id")
    if not integration_request_name:
        frappe.log_error(
            "PayFast callback received without m_payment_id", "PayFast Error"
        )
        return

    try:
        doc = frappe.get_doc("Integration Request", integration_request_name)

        # 4. Update the document based on payment status
        payment_status = data.get("payment_status")
        if payment_status == "COMPLETE":
            doc.status = "Completed"
            doc.run_method("on_payment_authorized", "Completed")
        elif payment_status == "FAILED":
            doc.status = "Failed"
        else:
            doc.status = "Cancelled"

        doc.save(ignore_permissions=True)
        frappe.db.commit()

    except frappe.DoesNotExistError:
        frappe.log_error(
            f"Integration Request '{integration_request_name}' not found for PayFast callback.",
            "PayFast Error",
        )
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "PayFast Callback Error")
        # It's important to commit any changes even if a later part of the hook
        # fails
        frappe.db.commit()
