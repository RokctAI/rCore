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
import unittest
# "rcore" is a template placeholder substituted at install time; resolve
# it dynamically so this file stays valid Python before rendering.
PayFastSettings = frappe.get_attr(
    "rcore.gateways.doctype.payfast_settings.payfast_settings.PayFastSettings"
)


class TestPayFastSettings(unittest.TestCase):
    def setUp(self):
        # Create a test PayFast Settings document
        self.payfast_settings = frappe.get_doc(
            {
                "doctype": "PayFast Settings",
                "gateway_name": "PayFast Test",
                "merchant_id": "10000100",
                "merchant_key": "46f0cd694581a",
                "is_sandbox": 1,
            }
        )
        self.payfast_settings.insert(ignore_permissions=True)
        self.payfast_settings.set("passphrase", "test_passphrase")
        self.payfast_settings.save(ignore_permissions=True)

    def tearDown(self):
        if frappe.db.table_exists("Payment Gateway") and frappe.db.exists("Payment Gateway", "PayFast"):
            frappe.delete_doc("Payment Gateway", "PayFast", force=True)
        self.payfast_settings.delete(ignore_permissions=True)

    def test_get_payment_url(self):
        payment_details = {
            "amount": "100.00",
            "title": "Test Payment",
            "description": "A test payment",
            "payer_email": "test@example.com",
            "payer_name": "Test User",
        }

        url = self.payfast_settings.get_payment_url(**payment_details)

        self.assertTrue(url.startswith("https://sandbox.payfast.co.za/eng/process?"))
        self.assertIn("merchant_id=10000100", url)
        self.assertIn("amount=100.00", url)
        self.assertIn("item_name=Test+Payment", url)
        self.assertIn("signature=", url)

    # Note: Testing the callback directly is complex as it requires a live request.
    # We can test the signature generation, but that is implicitly tested in get_payment_url.
    # The core logic of the callback (updating documents) should be tested via
    # integration tests if possible.
