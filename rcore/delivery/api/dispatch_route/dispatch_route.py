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

"""Driver-facing endpoints for admin-composed Dispatch Routes.

An admin composes a Dispatch Route in the desk (deliveryman, Pickup or
Delivery mode, stops with an optional per-stop quantity — Ray's water
run: the driver knows the depot but not which shop takes how many
bottles) and sets it to Assigned. The driver app then reads it through
get_my_dispatch_route and ticks stops off through complete_dispatch_stop.
The server is authoritative for stop ordering.
"""

from typing import Any

import frappe
from frappe.utils import now_datetime

from rcore.delivery.api.route.route_utils import (
    haversine,
    order_stops,
    parse_location,
    stop_has_coordinates,
)

ACTIVE_ROUTE_STATUSES = ("Assigned", "In Progress")

STOP_STATUS_MAP = {
    "done": "Done",
    "skipped": "Skipped",
}


def _shop_coords(shop_name, cache=None):
    """(lat, lon) for a Shop from its `location` JSON field, or None.

    Reads the Geolocation/JSON `location` field the way get_shops does —
    NOT the phantom Shop.latitude/longitude columns some legacy paths
    reference (they do not exist on the doctype).
    """
    if not shop_name:
        return None
    if cache is not None and shop_name in cache:
        return cache[shop_name]
    location = frappe.db.get_value("Shop", shop_name, "location")
    coords = parse_location(location)
    if cache is not None:
        cache[shop_name] = coords
    return coords


def serialize_dispatch_stop(route, stop, shop_cache=None):
    """Serialize one Dispatch Route Stop child row to the shared stop
    shape, resolving coordinates from the linked Shop when the row has
    none of its own."""
    get = stop.get if isinstance(stop, dict) else (
        lambda key, default=None: getattr(stop, key, default)
    )
    data = {
        "stop_type": "pickup" if route.mode == "Pickup" else "delivery",
        "ref_doctype": "Dispatch Route Stop",
        "ref_name": get("name"),
        "label": get("label") or get("shop") or get("name"),
        "latitude": get("latitude"),
        "longitude": get("longitude"),
        "quantity": get("quantity"),
        "unit": get("unit"),
        "status": get("status") or "Pending",
        "meta": {
            "route_id": route.name,
            "route_mode": route.mode,
            "shop": get("shop"),
            "note": get("note"),
            "status": get("status") or "Pending",
            "completed_at": (
                str(get("completed_at")) if get("completed_at") else None
            ),
        },
    }
    if not stop_has_coordinates(data):
        coords = _shop_coords(get("shop"), cache=shop_cache)
        if coords:
            data["latitude"], data["longitude"] = coords
        else:
            data["latitude"] = None
            data["longitude"] = None
    return data


def _driver_position(user):
    """The driver's last reported position from Deliveryman Profile, or
    None when unknown/unset."""
    profile = frappe.db.get_value(
        "Deliveryman Profile",
        {"user": user},
        ["latitude", "longitude"],
        as_dict=True,
    )
    if not profile:
        return None
    probe = {
        "latitude": profile.get("latitude"),
        "longitude": profile.get("longitude"),
    }
    if not stop_has_coordinates(probe):
        return None
    return (float(probe["latitude"]), float(probe["longitude"]))


def _active_route_doc(user):
    routes = frappe.get_all(
        "Dispatch Route",
        filters={
            "deliveryman": user,
            "status": ["in", list(ACTIVE_ROUTE_STATUSES)],
        },
        fields=["name"],
        order_by="modified desc",
        limit=1,
    )
    if not routes:
        return None
    return frappe.get_doc("Dispatch Route", routes[0].get("name"))


def get_active_dispatch_stops(user, shop_cache=None):
    """(route_doc, pending stop dicts) for the driver's active route.

    Shared with the map module's merged get_driver_route — pending stops
    only, unordered (the caller runs the optimizer over the merged list).
    Returns (None, []) when no route is active.
    """
    doc = _active_route_doc(user)
    if not doc:
        return None, []
    stops = [
        serialize_dispatch_stop(doc, stop, shop_cache=shop_cache)
        for stop in (doc.get("stops") or [])
        if (
            (stop.get("status") if isinstance(stop, dict)
             else getattr(stop, "status", None)) or "Pending"
        ) == "Pending"
    ]
    return doc, stops


@frappe.whitelist()
def get_my_dispatch_route() -> Any:
    """The session driver's active Dispatch Route with stops resolved and
    ordered.

    Completed/skipped stops come first in the admin's order; pending
    stops follow, greedy-ordered from the driver's last known position
    when the route has optimize_order set, otherwise in the admin's
    order. Sequence numbers are the server-authoritative drive order.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    doc = _active_route_doc(user)
    if not doc:
        return {"route": None, "stops": []}

    shop_cache = {}
    done, pending = [], []
    for stop in doc.get("stops") or []:
        data = serialize_dispatch_stop(doc, stop, shop_cache=shop_cache)
        if data.get("status") == "Pending":
            pending.append(data)
        else:
            done.append(data)

    if doc.get("optimize_order"):
        pending = order_stops(_driver_position(user), pending)
    else:
        # Admin's order is authoritative: keep it verbatim, just annotate
        # leg distances and flag coordinate-less stops.
        previous = _driver_position(user)
        for stop in pending:
            if stop_has_coordinates(stop):
                stop["distance_from_previous_km"] = (
                    round(
                        haversine(
                            previous[0],
                            previous[1],
                            stop["latitude"],
                            stop["longitude"],
                        ),
                        3,
                    )
                    if previous
                    else None
                )
                previous = (
                    float(stop["latitude"]), float(stop["longitude"])
                )
            else:
                stop["missing_coordinates"] = True
                stop["distance_from_previous_km"] = None

    stops = done + pending
    for index, stop in enumerate(stops, start=1):
        stop["sequence"] = index

    return {
        "route": {
            "name": doc.name,
            "deliveryman": doc.deliveryman,
            "mode": doc.mode,
            "status": doc.status,
            "optimize_order": doc.get("optimize_order"),
            "notes": doc.get("notes"),
            "total_stops": len(stops),
            "pending_stops": len(
                [s for s in stops if s.get("status") == "Pending"]
            ),
        },
        "stops": stops,
    }


@frappe.whitelist()
def complete_dispatch_stop(
    route_id: Any, stop_name: Any, status: Any = "Done"
) -> Any:
    """Driver marks one stop of his route Done or Skipped.

    Idempotent-safe: re-sending a completion for a stop that already left
    Pending returns the current state without changing anything. The
    route flips to In Progress on the first completed stop and to
    Completed once no stop is Pending.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Unauthorized", frappe.AuthenticationError)

    normalized = STOP_STATUS_MAP.get(str(status or "").strip().lower())
    if not normalized:
        frappe.throw(
            "Unknown stop status '{0}'. Allowed: Done, Skipped.".format(
                status
            )
        )

    if not frappe.db.exists("Dispatch Route", route_id):
        frappe.throw("Dispatch Route {0} not found.".format(route_id))

    doc = frappe.get_doc("Dispatch Route", route_id)
    if doc.deliveryman != user:
        frappe.throw(
            "You are not the deliveryman assigned to this route.",
            frappe.PermissionError,
        )

    target = None
    for stop in doc.get("stops") or []:
        if stop.get("name") == stop_name:
            target = stop
            break
    if target is None:
        frappe.throw(
            "Stop {0} not found on route {1}.".format(stop_name, route_id)
        )

    if doc.status not in ACTIVE_ROUTE_STATUSES:
        # Idempotent replay: completing the LAST pending stop flips the
        # route to Completed, so a network retry of that same call must
        # return the current state instead of erroring.
        if (
            doc.status == "Completed"
            and (target.get("status") or "Pending") != "Pending"
        ):
            pending_replay = len(
                [
                    s
                    for s in (doc.get("stops") or [])
                    if (s.get("status") or "Pending") == "Pending"
                ]
            )
            return {
                "route_id": doc.name,
                "route_status": doc.status,
                "stop_name": stop_name,
                "stop_status": target.get("status"),
                "pending_stops": pending_replay,
            }
        frappe.throw(
            "Dispatch Route {0} is not active (status is {1}).".format(
                doc.name, doc.status
            )
        )

    changed = False
    if (target.get("status") or "Pending") == "Pending":
        target.status = normalized
        target.completed_at = now_datetime()
        changed = True

    pending_count = len(
        [
            s
            for s in (doc.get("stops") or [])
            if (s.get("status") or "Pending") == "Pending"
        ]
    )
    if pending_count == 0:
        doc.status = "Completed"
        changed = True
    elif doc.status == "Assigned" and changed:
        doc.status = "In Progress"

    if changed:
        doc.save(ignore_permissions=True)

    return {
        "route_id": doc.name,
        "route_status": doc.status,
        "stop_name": stop_name,
        "stop_status": target.get("status"),
        "pending_stops": pending_count,
    }
