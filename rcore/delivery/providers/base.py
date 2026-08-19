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

"""Abstract interface for third-party intercity logistics providers.

Mirrors the payment-provider pattern: one common interface, per-tenant
configuration in the ``Delivery Provider Settings`` doctype, and
provider-specific adapters behind it. Client apps never talk to a
provider directly -- only to our API. Provider credentials live
server-side only and are never exposed to Dart/Next.js clients
(ShipRazor Merchant Agreement clause 1.2).
"""

import re
from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Base error for the intercity provider layer."""


class IntercityDisabledError(ProviderError):
    """Intercity fulfilment is switched off (the default state)."""


class ProviderNotConfiguredError(ProviderError):
    """No provider is configured, or its credentials are missing."""


class ProhibitedItemError(ProviderError):
    """Parcel contents match the provider's prohibited/restricted list."""


# Normalised provider statuses -> Parcel Order.status
PARCEL_STATUS_MAP = {
    "booked": "Accepted",
    "collected": "On a way",
    "in_transit": "On a way",
    "out_for_delivery": "On a way",
    "delivered": "Delivered",
    "cancelled": "Canceled",
    "failed_collection": "Canceled",
    "rto_initiated": "On a way",
    "rto_in_transit": "On a way",
    "rto_complete": "Canceled",
}

# Statuses that end a shipment and release its pickup-location refcount.
TERMINAL_STATUSES = frozenset(
    {"delivered", "cancelled", "rto_complete", "failed_collection"}
)

# RTO statuses keep the origin warehouse alive until the return closes.
REFCOUNT_HOLD_STATUSES = frozenset({"rto_initiated", "rto_in_transit"})


def map_to_parcel_status(normalized_status):
    """Map a normalised provider status onto ``Parcel Order.status``."""
    status = PARCEL_STATUS_MAP.get(normalized_status)
    if not status:
        raise ProviderError(
            f"Unknown normalised provider status '{normalized_status}'."
        )
    return status


def find_prohibited_match(text, keywords):
    """Return the first prohibited keyword found in ``text``, else None."""
    haystack = (text or "").lower()
    for keyword in keywords:
        if re.search(r"\b" + re.escape(keyword) + r"\b", haystack):
            return keyword
    return None


class DeliveryProvider(ABC):
    """Common interface every intercity logistics provider implements."""

    #: Human-readable provider name; also the registry key.
    name = None

    #: Provider-specific prohibited/restricted keyword list.
    prohibited_keywords = ()

    def __init__(self, settings):
        # `settings` is the Delivery Provider Settings document (or any
        # object exposing .get / .get_password). It is the sole authority
        # for credentials and configuration -- nothing here may fall back
        # to invented defaults.
        self.settings = settings

    def _get_secret(self, fieldname):
        """Read a Password field from settings, tolerating plain objects."""
        getter = getattr(self.settings, "get_password", None)
        if callable(getter):
            try:
                return getter(fieldname, raise_exception=False)
            except TypeError:
                return getter(fieldname)
        return self.settings.get(fieldname)

    # -- configuration -------------------------------------------------

    @abstractmethod
    def validate_configured(self):
        """Raise ProviderNotConfiguredError unless fully configured."""

    # -- compliance ----------------------------------------------------

    def validate_parcel(self, parcel):
        """Prohibited-items gate + declared-value requirement.

        Enforces the back-to-back Terms: declared value is required for
        intercity (liability caps key off it), and anything on the
        provider's prohibited/restricted list is rejected before booking.
        """
        try:
            declared_value = float(parcel.get("declared_value") or 0)
        except (TypeError, ValueError):
            declared_value = 0
        if declared_value <= 0:
            raise ProviderError(
                "A declared value is required for intercity parcels; "
                "liability caps are keyed off it."
            )

        parts = [
            str(parcel.get(key) or "")
            for key in ("description", "category", "note")
        ]
        for item in parcel.get("items") or []:
            parts.append(str(item or ""))
        match = find_prohibited_match(" ".join(parts), self.prohibited_keywords)
        if match:
            raise ProhibitedItemError(
                f"Parcel contents ('{match}') are prohibited or restricted "
                f"for intercity delivery via {self.name}."
            )

    # -- provider operations -------------------------------------------

    @abstractmethod
    def get_quote(self, parcel):
        """Rates/options for a from/to + dimensions + declared value.

        Must return the provider's response; rates are never computed or
        invented locally.
        """

    @abstractmethod
    def create_shipment(self, parcel):
        """Book a shipment; returns waybill/tracking references."""

    @abstractmethod
    def cancel_shipment(self, ref):
        """Cancel a booked shipment by provider reference."""

    @abstractmethod
    def get_tracking(self, ref):
        """Fetch tracking events for a shipment."""

    @abstractmethod
    def handle_webhook(self, payload):
        """Normalise a provider webhook payload.

        Returns ``{"provider_shipment_ref", "status", "raw"}`` where
        ``status`` is one of the normalised statuses in PARCEL_STATUS_MAP.
        """

    @abstractmethod
    def register_pickup_location(self, address, reference):
        """Create a provider-side pickup location; returns its provider ref."""

    @abstractmethod
    def delete_pickup_location(self, provider_ref):
        """Delete a provider-side pickup location."""

    def list_pickup_locations(self):
        """Provider-side pickup locations, for the orphan sweep.

        Optional; providers without a listing API may leave this
        unimplemented and the sweep will skip them.
        """
        raise NotImplementedError
