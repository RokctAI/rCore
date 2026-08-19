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

"""Ephemeral pickup-location ("warehouse") lifecycle.

We never mirror thousands of client addresses into a provider. A
deterministic reference is derived from the normalised collection
address, a provider-side warehouse is created on demand, and a
refcount of in-flight shipments keeps it alive. On terminal status the
refcount is released; at zero the provider-side record is deleted
(optionally after a grace period). A scheduled orphan sweep reconciles
provider-side warehouses against active mappings.
"""

import hashlib
import re

import frappe
from frappe.utils import add_to_date, cint, now_datetime

from .base import REFCOUNT_HOLD_STATUSES, TERMINAL_STATUSES

PICKUP_LOCATION_DOCTYPE = "Provider Pickup Location"

#: Only provider-side warehouses we created (this prefix) may be swept.
REFERENCE_PREFIX = "RKT-"


def normalize_address(address):
    """Lowercase, strip punctuation and collapse whitespace."""
    text = re.sub(r"[^a-z0-9 ]+", " ", str(address or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def pickup_reference(user_id, address):
    """Deterministic provider-side reference for a collection address."""
    digest = hashlib.sha1(
        normalize_address(address).encode("utf-8")
    ).hexdigest()[:8]
    return f"{REFERENCE_PREFIX}{user_id}-{digest}"


def should_release_refcount(normalized_status):
    """Terminal statuses release the refcount; RTO statuses hold it."""
    if normalized_status in REFCOUNT_HOLD_STATUSES:
        return False
    return normalized_status in TERMINAL_STATUSES


def ensure_pickup_location(provider, user_id, address):
    """Ensure a live provider-side warehouse for this address; refcount it."""
    reference = pickup_reference(user_id, address)
    existing = frappe.db.get_value(
        PICKUP_LOCATION_DOCTYPE,
        {"reference": reference, "provider": provider.name, "status": "Active"},
        ["name", "refcount", "provider_ref"],
        as_dict=True,
    )
    if existing:
        frappe.db.set_value(
            PICKUP_LOCATION_DOCTYPE,
            existing.name,
            {"refcount": cint(existing.refcount) + 1, "release_after": None},
        )
        return {"reference": reference, "provider_ref": existing.provider_ref}

    provider_ref = provider.register_pickup_location(address, reference)
    frappe.get_doc({
        "doctype": PICKUP_LOCATION_DOCTYPE,
        "provider": provider.name,
        "reference": reference,
        "provider_ref": provider_ref,
        "user": user_id,
        "normalized_address": normalize_address(address),
        "refcount": 1,
        "status": "Active",
    }).insert(ignore_permissions=True)
    return {"reference": reference, "provider_ref": provider_ref}


def release_pickup_location(provider, reference):
    """Decrement the refcount; delete/deactivate when it reaches zero."""
    row = frappe.db.get_value(
        PICKUP_LOCATION_DOCTYPE,
        {"reference": reference, "provider": provider.name, "status": "Active"},
        ["name", "refcount", "provider_ref"],
        as_dict=True,
    )
    if not row:
        return
    refcount = max(cint(row.refcount) - 1, 0)
    if refcount > 0:
        frappe.db.set_value(
            PICKUP_LOCATION_DOCTYPE, row.name, {"refcount": refcount}
        )
        return

    grace_hours = cint(
        provider.settings.get("pickup_location_grace_hours") or 0
    )
    if grace_hours > 0:
        # Delay deletion so a client shipping daily from the same address
        # doesn't churn create/delete calls.
        frappe.db.set_value(
            PICKUP_LOCATION_DOCTYPE,
            row.name,
            {
                "refcount": 0,
                "release_after": add_to_date(now_datetime(), hours=grace_hours),
            },
        )
    else:
        _deactivate(provider, row)


def _deactivate(provider, row):
    provider.delete_pickup_location(row.provider_ref)
    frappe.db.set_value(
        PICKUP_LOCATION_DOCTYPE,
        row.name,
        {"status": "Inactive", "refcount": 0, "release_after": None},
    )


def process_due_pickup_releases():
    """Scheduled (hourly): delete warehouses whose grace period lapsed.

    No-op while intercity is disabled or unconfigured -- makes no
    provider calls in the default state.
    """
    from . import registry

    settings = registry.get_settings()
    if not registry.is_intercity_enabled(settings):
        return

    due = frappe.get_all(
        PICKUP_LOCATION_DOCTYPE,
        filters={
            "status": "Active",
            "refcount": 0,
            "release_after": ["<=", now_datetime()],
        },
        fields=["name", "provider", "provider_ref", "refcount"],
    )
    for row in due:
        try:
            provider = registry.get_provider(row.provider, settings)
            _deactivate(provider, row)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(), "Intercity pickup release failed"
            )


def sweep_orphan_pickup_locations():
    """Scheduled (daily): reconcile provider-side warehouses with mappings.

    Covers missed webhooks/crashes. Only touches provider-side records
    carrying our reference prefix. No-op while intercity is disabled.
    """
    from . import registry

    settings = registry.get_settings()
    if not registry.is_intercity_enabled(settings):
        return

    for provider_name in registry.PROVIDERS:
        try:
            provider = registry.get_provider(provider_name, settings)
        except Exception:
            continue  # unconfigured providers are skipped, never called
        try:
            remote_locations = provider.list_pickup_locations()
        except NotImplementedError:
            continue
        except Exception:
            frappe.log_error(
                frappe.get_traceback(), "Intercity orphan sweep listing failed"
            )
            continue

        active_refs = {
            row.reference
            for row in frappe.get_all(
                PICKUP_LOCATION_DOCTYPE,
                filters={"provider": provider_name, "status": "Active"},
                fields=["reference"],
            )
        }
        for location in remote_locations:
            reference = (location or {}).get("name") or ""
            if not reference.startswith(REFERENCE_PREFIX):
                continue  # not ours -- never delete records we didn't create
            if reference in active_refs:
                continue
            try:
                provider_ref = location.get("warehouse_id") or location.get("id")
                provider.delete_pickup_location(provider_ref)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(), "Intercity orphan sweep delete failed"
                )
