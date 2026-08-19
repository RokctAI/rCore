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

from frappe.model.document import Document
import frappe
import requests


class PlatformWallet(Document):
    def onload(self):
        try:
            self.get_balance()
        except Exception:
            pass

    def get_balance(self):
        if not frappe.db.get_single_value(
            "Permission Settings",
                "enable_paas_lending"):
            return

        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        if not control_plane_url or not api_secret:
            return

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.billing.get_tenant_wallet_balance"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        try:
            response = requests.post(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.set_onload(
                    "current_balance",
                    data.get(
                        "message",
                        {}).get(
                        "balance",
                        0))
        except Exception as e:
            frappe.log_error(f"Failed to fetch wallet balance: {e}")

    @frappe.whitelist()
    def request_payout(self, amount: Any) -> Any:
        """
        The request_payout function initiates a payout request for a specified amount. It takes two parameters: self, a reference to the instance of the class, and amount, the amount to be requested for payout. The function first checks if the lending feature is enabled in the system's Permission Settings. If enabled, it constructs an API request to the control plane URL with the provided amount and sends it using a POST request. The function returns the response from the API if the request is successful, or throws an error if the request fails.
        """
        import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
        if not frappe.db.get_single_value(
            "Permission Settings",
                "enable_paas_lending"):
            frappe.throw("Lending feature is disabled.")

        control_plane_url = frappe.conf.get("control_plane_url")
        api_secret = frappe.conf.get("api_secret")

        scheme = frappe.conf.get("control_plane_scheme", "https")
        api_url = f"{scheme}://{control_plane_url}/api/method/control.control.api.billing.request_tenant_payout"

        headers = {"X-Rokct-Secret": api_secret, "X-Rokct-Tenant": frappe.local.site}
        data = {"amount": amount}

        response = requests.post(api_url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            frappe.throw(f"Failed to request payout: {response.text}")
