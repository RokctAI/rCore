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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""ShipRazor adapter -- first intercity logistics provider.

All endpoint paths, payload shapes and webhook status vocabulary below
are adapter-side placeholders to be confirmed against the ShipRazor API
documentation once the Merchant Agreement is signed. Nothing in this
module runs until intercity is enabled AND the API key + base URL are
configured in Delivery Provider Settings; no rates, references or
tracking data are ever fabricated locally.
"""

import json

import frappe

from .base import (
    DeliveryProvider,
    ProviderError,
    ProviderNotConfiguredError,
)

# ShipRazor webhook/tracking statuses -> normalised statuses (base.py).
SHIPRAZOR_STATUS_MAP = {
    "pending": "booked",
    "booked": "booked",
    "collected": "collected",
    "picked_up": "collected",
    "in_transit": "in_transit",
    "out_for_delivery": "out_for_delivery",
    "delivered": "delivered",
    "cancelled": "cancelled",
    "collection_failed": "failed_collection",
    "rto_initiated": "rto_initiated",
    "rto_in_transit": "rto_in_transit",
    "rto_delivered": "rto_complete",
}


class ShipRazorProvider(DeliveryProvider):
    name = "ShipRazor"

    # Mirrors the prohibited/restricted list in INTERCITY_DELIVERY_TERMS.md
    # (upstream: ShipRazor Merchant Agreement, Annexure B). Conservative,
    # word-boundary keyword gate applied before any booking is accepted.
    prohibited_keywords = (
        "paint",
        "thinner",
        "solvent",
        "insecticide",
        "pesticide",
        "lithium",
        "battery",
        "batteries",
        "magnet",
        "magnetized",
        "fuel",
        "infectious",
        "toxic",
        "bleach",
        "flammable",
        "ammunition",
        "firearm",
        "gun",
        "flare",
        "gunpowder",
        "firework",
        "fireworks",
        "knife",
        "knives",
        "sword",
        "weapon",
        "dry ice",
        "aerosol",
        "tobacco",
        "cigarette",
        "e-cigarette",
        "vape",
        "ketamine",
        "jewellery",
        "jewelry",
        "bullion",
        "gem",
        "gems",
        "precious stone",
        "precious stones",
        "currency",
        "cash",
        "coins",
        "poison",
        "alcohol",
        "liquor",
        "explosive",
        "explosives",
        "radioactive",
        "hazardous",
        "pornographic",
        "live plants",
        "drugs",
        "medicine",
        "medicines",
        "cbd",
        "counterfeit",
        "livestock",
        "human remains",
        "animal remains",
        "embryo",
        "organs",
    )

    # -- configuration -------------------------------------------------

    def validate_configured(self):
        api_key = self._get_secret("shiprazor_api_key")
        base_url = (self.settings.get("shiprazor_base_url") or "").strip()
        if not api_key or not base_url:
            raise ProviderNotConfiguredError(
                "ShipRazor is not configured. Set the API key and base URL "
                "in Delivery Provider Settings."
            )

    # -- HTTP helpers --------------------------------------------------

    def _headers(self):
        return {
            "Authorization": f"Bearer {self._get_secret('shiprazor_api_key')}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path):
        base_url = (self.settings.get("shiprazor_base_url") or "").strip()
        return base_url.rstrip("/") + path

    def _post(self, path, payload):
        self.validate_configured()
        return frappe.make_post_request(
            self._url(path), headers=self._headers(),
            data=json.dumps(payload or {}),
        )

    def _get(self, path, params=None):
        self.validate_configured()
        return frappe.make_get_request(
            self._url(path), headers=self._headers(), params=params or {},
        )

    # -- provider operations -------------------------------------------

    def get_quote(self, parcel):
        self.validate_configured()
        self.validate_parcel(parcel)
        payload = {
            "collection_address": parcel.get("address_from"),
            "delivery_address": parcel.get("address_to"),
            "dimensions": parcel.get("dimensions"),
            "weight": parcel.get("weight"),
            "declared_value": parcel.get("declared_value"),
        }
        # Pass the provider's rates through untouched -- pricing is never
        # computed or invented locally.
        return self._post("/api/v1/rates", payload)

    def create_shipment(self, parcel):
        self.validate_configured()
        self.validate_parcel(parcel)
        payload = {
            "warehouse_ref": parcel.get("pickup_location_ref"),
            "collection_address": parcel.get("address_from"),
            "delivery_address": parcel.get("address_to"),
            "sender_name": parcel.get("username_from"),
            "sender_phone": parcel.get("phone_from"),
            "recipient_name": parcel.get("username_to"),
            "recipient_phone": parcel.get("phone_to"),
            "description": parcel.get("description"),
            "dimensions": parcel.get("dimensions"),
            "weight": parcel.get("weight"),
            "declared_value": parcel.get("declared_value"),
            "cod_amount": parcel.get("cod_amount") or 0,
        }
        response = self._post("/api/v1/shipments", payload) or {}
        shipment_ref = response.get("shipment_id") or response.get("id")
        waybill_no = response.get("waybill") or response.get("waybill_no")
        if not shipment_ref or not waybill_no:
            raise ProviderError(
                "ShipRazor booking response is missing shipment/waybill "
                "references; the booking was not confirmed."
            )
        return {
            "provider_shipment_ref": shipment_ref,
            "waybill_no": waybill_no,
            "tracking_url": response.get("tracking_url"),
        }

    def cancel_shipment(self, ref):
        if not ref:
            raise ProviderError("A provider shipment reference is required.")
        return self._post(f"/api/v1/shipments/{ref}/cancel", {})

    def get_tracking(self, ref):
        if not ref:
            raise ProviderError("A provider shipment reference is required.")
        return self._get(f"/api/v1/shipments/{ref}/tracking")

    def handle_webhook(self, payload):
        payload = payload or {}
        shipment_ref = payload.get("shipment_id") or payload.get("id")
        if not shipment_ref:
            raise ProviderError(
                "ShipRazor webhook payload has no shipment reference."
            )
        raw_status = str(payload.get("status") or "").strip().lower()
        normalized = SHIPRAZOR_STATUS_MAP.get(raw_status)
        if not normalized:
            raise ProviderError(
                f"Unrecognised ShipRazor webhook status '{raw_status}'."
            )
        return {
            "provider_shipment_ref": shipment_ref,
            "status": normalized,
            "raw": payload,
        }

    def register_pickup_location(self, address, reference):
        response = self._post(
            "/api/v1/warehouses",
            {"name": reference, "address": address},
        ) or {}
        provider_ref = response.get("warehouse_id") or response.get("id")
        if not provider_ref:
            raise ProviderError(
                "ShipRazor warehouse response has no reference; the pickup "
                "location was not confirmed."
            )
        return provider_ref

    def delete_pickup_location(self, provider_ref):
        if not provider_ref:
            raise ProviderError("A provider warehouse reference is required.")
        return self._post(f"/api/v1/warehouses/{provider_ref}/delete", {})

    def list_pickup_locations(self):
        response = self._get("/api/v1/warehouses") or {}
        return response.get("warehouses") or []
