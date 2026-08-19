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

"""Pure routing helpers for driver stop ordering.

Deliberately frappe-free so the module is unit-testable without a bench
(the test_intercity_providers.py precedent) and importable from both the
delivery and map API modules once composed (paas.api.route.route_utils).

The ordering strategy is greedy nearest-next: with no cap on how many
orders a driver can hold (attach_order_to_me only checks the order is
unassigned) realistic batches are small, so a real TSP solver would be
overkill. The one hard constraint is that a pickup stop must be visited
before its own drop-off; stops declare the link through an optional
``pair_key`` (shared by the pickup and its drop-off) plus ``stop_type``
("pickup" or "dropoff").
"""

import json
import math

EARTH_RADIUS_KM = 6371.0


def haversine(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two lat/long points."""
    lat1, lon1, lat2, lon2 = (
        float(lat1), float(lon1), float(lat2), float(lon2)
    )
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def parse_location(value):
    """Parse a stored location payload into a ``(lat, lon)`` float tuple.

    The platform stores coordinates as JSON strings in Data/Geolocation
    fields (Order.location, Shop.location, Parcel Order.address_from/_to)
    with either ``latitude``/``longitude`` or ``lat``/``long``/``lng``
    spellings (the two shapes get_shops already tolerates). Dicts are
    accepted as-is. Anything malformed — plain text like
    ``"Customer: Jane"``, empty values, non-numeric coordinates — returns
    None instead of raising, so a bad row can never break route building.
    """
    if value is None:
        return None
    data = value
    if isinstance(data, str):
        text = data.strip()
        if not text:
            return None
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
    if not isinstance(data, dict):
        return None
    lat = data.get("latitude", data.get("lat"))
    lon = data.get("longitude", data.get("long", data.get("lng")))
    if lat is None or lon is None:
        return None
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lon)):
        # json.loads accepts the NaN/Infinity literals; neither is a
        # usable coordinate and Infinity would blow up haversine.
        return None
    return (lat, lon)


def stop_has_coordinates(stop):
    """Whether a stop dict carries a usable coordinate pair.

    Frappe Float fields default to 0.0, so an exact (0, 0) pair — a point
    in the Atlantic no ZA delivery ever means — is treated as "not set".
    """
    lat = stop.get("latitude")
    lon = stop.get("longitude")
    if lat is None or lon is None:
        return False
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return False
    if lat == 0 and lon == 0:
        return False
    return True


def order_stops(start, stops):
    """Order stops greedy nearest-next, keeping pickups before drop-offs.

    ``start`` is a ``(lat, lon)`` tuple or None. When None, the first stop
    keeps its given position (the first eligible stop in input order) and
    greedy ordering continues from there — "first stop as-is".

    Each stop is a dict; ``latitude``/``longitude`` are read via
    :func:`stop_has_coordinates`, and the optional ``pair_key`` +
    ``stop_type`` fields express the pickup-before-drop-off constraint. A
    drop-off is only held back while its own pickup is routable and not
    yet placed.

    Returns a NEW list of shallow-copied stop dicts:

    - routable stops first, greedy-ordered, each with
      ``distance_from_previous_km`` (None for the very first stop when
      there is no start position);
    - coordinate-less stops at the tail in input order, flagged
      ``missing_coordinates: True`` (a drop-off whose pickup lacks
      coordinates rides the tail too, after its pickup, so the constraint
      survives even there);
    - every stop numbered with a 1-based ``sequence``.
    """
    stops = [dict(stop) for stop in (stops or [])]

    routable, tail = [], []
    for stop in stops:
        if stop_has_coordinates(stop):
            routable.append(stop)
        else:
            stop["missing_coordinates"] = True
            tail.append(stop)

    # A drop-off whose pickup fell into the tail cannot be routed ahead of
    # it; demote it to the tail as well (placed after its pickup below).
    tail_pickup_keys = {
        s.get("pair_key")
        for s in tail
        if s.get("pair_key") and s.get("stop_type") == "pickup"
    }
    if tail_pickup_keys:
        still_routable = []
        for stop in routable:
            if (
                stop.get("stop_type") == "dropoff"
                and stop.get("pair_key") in tail_pickup_keys
            ):
                tail.append(stop)
            else:
                still_routable.append(stop)
        routable = still_routable

    # Within the tail, make sure each pickup precedes its own drop-off.
    for key in tail_pickup_keys:
        pickup_idx = next(
            (
                i
                for i, s in enumerate(tail)
                if s.get("pair_key") == key
                and s.get("stop_type") == "pickup"
            ),
            None,
        )
        drop_idx = next(
            (
                i
                for i, s in enumerate(tail)
                if s.get("pair_key") == key
                and s.get("stop_type") == "dropoff"
            ),
            None,
        )
        if (
            pickup_idx is not None
            and drop_idx is not None
            and drop_idx < pickup_idx
        ):
            drop = tail.pop(drop_idx)
            tail.insert(pickup_idx, drop)  # pickup shifted left by the pop

    routable_pickup_keys = {
        s.get("pair_key")
        for s in routable
        if s.get("pair_key") and s.get("stop_type") == "pickup"
    }

    ordered = []
    placed_pickup_keys = set()
    current = tuple(start) if start else None
    remaining = list(routable)
    while remaining:
        eligible = [
            s
            for s in remaining
            if not (
                s.get("stop_type") == "dropoff"
                and s.get("pair_key") in routable_pickup_keys
                and s.get("pair_key") not in placed_pickup_keys
            )
        ]
        if not eligible:  # defensive; cannot happen with well-formed pairs
            eligible = remaining
        if current is None:
            chosen = eligible[0]
            chosen_distance = None
        else:
            chosen = min(
                eligible,
                key=lambda s: haversine(
                    current[0],
                    current[1],
                    s["latitude"],
                    s["longitude"],
                ),
            )
            chosen_distance = haversine(
                current[0], current[1], chosen["latitude"],
                chosen["longitude"],
            )
        remaining.remove(chosen)
        chosen["distance_from_previous_km"] = (
            round(chosen_distance, 3)
            if chosen_distance is not None
            else None
        )
        if chosen.get("stop_type") == "pickup" and chosen.get("pair_key"):
            placed_pickup_keys.add(chosen.get("pair_key"))
        ordered.append(chosen)
        current = (float(chosen["latitude"]), float(chosen["longitude"]))

    for stop in tail:
        # Demoted drop-offs (pickup without coordinates) keep their own
        # coordinates and are NOT flagged missing_coordinates.
        stop["distance_from_previous_km"] = None
        ordered.append(stop)

    for index, stop in enumerate(ordered, start=1):
        stop["sequence"] = index
    return ordered
