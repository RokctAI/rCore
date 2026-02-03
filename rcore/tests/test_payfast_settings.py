# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import unittest
from rcore.pay.doctype.payfast_settings.payfast_settings import PayFastSettings

class TestPayFastSettings(unittest.TestCase):
    def setUp(self):
        # Create a test PayFast Settings document
        self.payfast_settings = frappe.get_doc({
            "doctype": "PayFast Settings",
            "gateway_name": "PayFast Test",
            "merchant_id": "10000100",
            "merchant_key": "46f0cd694581a",
            "is_sandbox": 1
        })
        self.payfast_settings.insert(ignore_permissions=True)
        self.payfast_settings.set("passphrase", "test_passphrase")
        self.payfast_settings.save(ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        self.payfast_settings.delete(ignore_permissions=True)
        frappe.db.commit()

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
    # The core logic of the callback (updating documents) should be tested via integration tests if possible.
