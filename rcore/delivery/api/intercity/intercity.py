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

"""Intercity delivery API -- client-facing endpoints for the provider layer.

Client apps only ever call these endpoints; they never talk to a
logistics provider directly. Every endpoint is inert by default: while
``enable_intercity`` is off (the default) or no provider is configured,
requests fail with an explicit error and no provider call is made.
"""

from typing import Any
import hmac
import json

import frappe
from rcore.base.api.utils import api_response
from rcore.delivery.providers import lifecycle, registry
from rcore.delivery.providers.base import ProviderError, map_to_parcel_status


def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(
            "You must be logged in to use intercity delivery.",
            frappe.AuthenticationError,
        )


def _provider_or_throw(name=None):
    try:
        return registry.get_provider(name)
    except ProviderError as exc:
        frappe.throw(str(exc))


@frappe.whitelist()
def get_intercity_quote(quote_data: Any) -> Any:
    """
    Returns rates/options for a from/to + dimensions + declared value.
    Rates come from the configured provider only; nothing is priced locally.
    """
    _require_login()
    if isinstance(quote_data, str):
        quote_data = json.loads(quote_data)
    provider = _provider_or_throw()
    try:
        quote = provider.get_quote(quote_data)
    except ProviderError as exc:
        frappe.throw(str(exc))
    return api_response(data=quote)


def book_intercity_parcel(parcel_order) -> None:
    """
    Books a submitted intercity Parcel Order with the configured provider.
    Called from create_parcel_order after insert; raising here rolls the
    insert back, so an intercity order can never exist unbooked while the
    feature is disabled or unconfigured. Provider-side records created
    before a failure are reclaimed by the orphan sweep.
    """
    try:
        provider = registry.get_provider(parcel_order.get("provider") or None)
        parcel = {
            "description": parcel_order.get("note"),
            "category": parcel_order.get("parcel_type"),
            "items": [
                item.get("item_name") or item.get("item")
                for item in (parcel_order.get("items") or [])
            ],
            "declared_value": parcel_order.get("declared_value"),
            "cod_amount": parcel_order.get("cod_amount"),
            "address_from": parcel_order.get("address_from"),
            "address_to": parcel_order.get("address_to"),
            "username_from": parcel_order.get("username_from"),
            "phone_from": parcel_order.get("phone_from"),
            "username_to": parcel_order.get("username_to"),
            "phone_to": parcel_order.get("phone_to"),
        }
        provider.validate_parcel(parcel)
        pickup = lifecycle.ensure_pickup_location(
            provider,
            parcel_order.get("user"),
            parcel_order.get("address_from"),
        )
        parcel["pickup_location_ref"] = pickup["provider_ref"]
        booking = provider.create_shipment(parcel)
    except ProviderError as exc:
        frappe.throw(str(exc))
        return

    parcel_order.provider = provider.name
    parcel_order.provider_shipment_ref = booking["provider_shipment_ref"]
    parcel_order.waybill_no = booking.get("waybill_no")
    parcel_order.tracking_url = booking.get("tracking_url")
    parcel_order.save(ignore_permissions=True)


def _get_own_intercity_order(parcel_order_id):
    parcel_order = frappe.get_doc("Parcel Order", parcel_order_id)
    user = frappe.session.user
    is_admin = (
        "System Manager" in frappe.get_roles()
        or "Administrator" in frappe.get_roles()
    )
    if parcel_order.user != user and not is_admin:
        frappe.throw(
            "You are not authorized to access this parcel order.",
            frappe.PermissionError,
        )
    if not parcel_order.get("provider_shipment_ref"):
        frappe.throw("This parcel order has no intercity booking.")
    return parcel_order


@frappe.whitelist()
def cancel_intercity_shipment(parcel_order_id: Any) -> Any:
    """
    Cancels an intercity booking with the provider and the parcel order.
    """
    _require_login()
    parcel_order = _get_own_intercity_order(parcel_order_id)
    provider = _provider_or_throw(parcel_order.get("provider"))
    try:
        provider.cancel_shipment(parcel_order.provider_shipment_ref)
    except ProviderError as exc:
        frappe.throw(str(exc))
    parcel_order.status = "Canceled"
    parcel_order.save(ignore_permissions=True)
    lifecycle.release_pickup_location(
        provider,
        lifecycle.pickup_reference(
            parcel_order.user, parcel_order.address_from
        ),
    )
    return api_response(
        data=parcel_order.as_dict(), message="Intercity shipment canceled"
    )


@frappe.whitelist()
def get_intercity_tracking(parcel_order_id: Any) -> Any:
    """
    Returns provider tracking for an intercity parcel order.
    """
    _require_login()
    parcel_order = _get_own_intercity_order(parcel_order_id)
    provider = _provider_or_throw(parcel_order.get("provider"))
    try:
        tracking = provider.get_tracking(parcel_order.provider_shipment_ref)
    except ProviderError as exc:
        frappe.throw(str(exc))
    return api_response(data=tracking)


@frappe.whitelist(allow_guest=True)
def intercity_webhook(**kwargs: Any) -> Any:
    """
    Inbound provider status webhook. Authenticated with the configured
    webhook secret; maps provider statuses onto Parcel Order.status and
    releases pickup-location refcounts on terminal statuses.
    """
    settings = registry.get_settings()
    if not registry.is_intercity_enabled(settings):
        frappe.throw("Intercity delivery is disabled.")

    secret = settings.get_password(
        "shiprazor_webhook_secret", raise_exception=False
    )
    if not secret:
        frappe.throw("Intercity webhook secret is not configured.")
    provided = frappe.get_request_header("X-Webhook-Token") or ""
    if not hmac.compare_digest(str(provided), str(secret)):
        frappe.throw("Invalid webhook token.", frappe.AuthenticationError)

    if getattr(frappe, "request", None) is not None and frappe.request.data:
        payload = json.loads(frappe.request.data)
    else:
        payload = kwargs

    provider = _provider_or_throw()
    try:
        event = provider.handle_webhook(payload)
        parcel_status = map_to_parcel_status(event["status"])
    except ProviderError as exc:
        frappe.throw(str(exc))
        return

    name = frappe.db.get_value(
        "Parcel Order",
        {"provider_shipment_ref": event["provider_shipment_ref"]},
    )
    if not name:
        frappe.log_error(
            f"Intercity webhook for unknown shipment "
            f"{event['provider_shipment_ref']}",
            "Intercity Webhook",
        )
        return api_response(message="No matching parcel order")

    parcel_order = frappe.get_doc("Parcel Order", name)
    parcel_order.status = parcel_status
    parcel_order.save(ignore_permissions=True)

    if lifecycle.should_release_refcount(event["status"]):
        lifecycle.release_pickup_location(
            provider,
            lifecycle.pickup_reference(
                parcel_order.user, parcel_order.address_from
            ),
        )
    return api_response(message="ok")
