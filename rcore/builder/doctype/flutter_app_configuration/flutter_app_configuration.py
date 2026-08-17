# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class FlutterAppConfiguration(Document):
    def onload(self):  # noqa: C901
        """
        Populate read-only fields from system settings for display purposes.
        These values are not saved to the DB if read-only, but help the user see what will be used.
        """
        # Google Maps Key
        try:
            if not self.google_api_key:
                self.google_api_key = frappe.db.get_single_value(
                    "Location Settings", "google_map_key")
        except Exception:
            pass

        # Firebase Web Key
        try:
            if not self.firebase_web_key:
                self.firebase_web_key = frappe.db.get_single_value(
                    "Push Notification Settings", "api_key")
        except Exception:
            pass

        # PayFast Credentials
        try:
            # Only fetch if any are missing
            if not (
                    self.payfast_merchant_id and self.payfast_merchant_key and self.payfast_passphrase):
                pf_settings = frappe.get_doc("Payment Gateway", "PayFast")
                if pf_settings:
                    settings_dict = {
                        s.key: s.value for s in pf_settings.settings}

                    if not self.payfast_merchant_id:
                        self.payfast_merchant_id = settings_dict.get(
                            "merchant_id")

                    if not self.payfast_merchant_key:
                        self.payfast_merchant_key = settings_dict.get(
                            "merchant_key")

                    if not self.payfast_passphrase:
                        self.payfast_passphrase = settings_dict.get(
                            "pass_phrase")
        except Exception:
            pass

        # Demo Location
        try:
            if not (self.default_latitude and self.default_longitude):
                if frappe.db.exists("DocType", "Location Settings"):
                    loc_settings = frappe.get_doc("Location Settings")
                    if not self.default_latitude:
                        self.default_latitude = loc_settings.location_latitude
                    if not self.default_longitude:
                        self.default_longitude = loc_settings.location_longitude
        except Exception:
            pass

        # URI Prefix Fallback
        if not self.uri_prefix:
            self.uri_prefix = self.web_url
