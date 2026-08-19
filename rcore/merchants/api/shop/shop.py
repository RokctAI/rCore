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

import frappe
from frappe.model.document import Document
import uuid
from rcore.base.api.utils import api_response
from rcore.base.api.idempotency import idempotent


def get_shop_coords(shop: Any) -> tuple:
    """
    Returns (latitude, longitude) as floats for a Shop, or (None, None).

    The Shop doctype has no latitude/longitude columns -- coordinates live
    only inside the ``location`` Geolocation field, a JSON string using
    either latitude/longitude or lat/long keys. Accepts a shop name, a Shop
    document, or any dict-like row that carries ``location``. Tolerant of
    missing, empty, or malformed location data.
    """
    import json

    location = None
    if isinstance(shop, str):
        location = frappe.db.get_value("Shop", shop, "location")
    elif shop is not None and hasattr(shop, "get"):
        location = shop.get("location")

    if isinstance(location, str) and location:
        try:
            location = json.loads(location)
        except ValueError:
            return (None, None)

    if not isinstance(location, dict):
        return (None, None)

    lat = location.get("latitude") or location.get("lat")
    lon = location.get("longitude") or location.get("long")
    if not lat or not lon:
        return (None, None)

    try:
        return (float(lat), float(lon))
    except (TypeError, ValueError):
        return (None, None)


@frappe.whitelist()
@idempotent
def create_shop(shop_data: Any) -> Any:
    """
    Creates a new Shop document.
    Only users with 'System Manager' or 'Seller' roles can create a shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if (
        "System Manager" not in frappe.get_roles()
        and "Seller" not in frappe.get_roles()
    ):
        frappe.throw(
            "You are not authorized to create a shop.", frappe.PermissionError
        )

    if not isinstance(shop_data, dict):
        frappe.throw("shop_data must be a dictionary.", frappe.ValidationError)

    # Set the current user as the owner if not specified
    if "user" not in shop_data:
        shop_data["user"] = frappe.session.user

    # Generate UUID and slug
    shop_data["uuid"] = str(uuid.uuid4())
    shop_data["slug"] = frappe.utils.slug(shop_data.get("shop_name"))

    try:
        shop = frappe.get_doc({"doctype": "Shop", **shop_data})
        shop.insert(ignore_permissions=True)
        frappe.db.commit()
        return api_response(
            data=shop.as_dict(), message="Shop created successfully"
        )
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Shop Creation Failed")
        frappe.throw(f"An error occurred while creating the shop: {e}")


@frappe.whitelist(allow_guest=True)
def get_shops(limit_start: int=0, limit_page_length: int=20, order_by: str='name', order: str='desc', latitude: float=None, longitude: float=None, **kwargs) -> Any:
    """
    Retrieves a list of shops with pagination and filters. Supports geo-sorting.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    from rcore.base.api.utils import haversine
    import json

    filters = {"status": "approved", "visibility": 1, "open": 1}

    if kwargs.get("delivery"):
        filters["delivery"] = 1

    if kwargs.get("takeaway"):
        filters["pickup"] = 1

    # If we are sorting by distance, we might need to fetch more items or all items
    # and then paginate in Python. For simplicity, we'll fetch all matching and then slice.
    # For a few hundred shops, this is fine.
    # Note: Using get_all for potential performance if many shops.
    shops = frappe.get_all(
        "Shop",
        filters=filters,
        fields=[
            "name",
            "shop_name",
            "uuid",
            "slug",
            "user",
            "logo",
            "cover_photo",
            "phone",
            "address",
            "location",
            "status",
            "type",
            "min_amount",
            "tax",
            "delivery_time_type",
            "delivery_time_from",
            "delivery_time_to",
            "open",
            "visibility",
            "verify",
            "service_fee",
            "percentage",
            "enable_cod",
            "enable_credit",
            "credit_mode",
            "shop_type",
            "is_ecommerce",
        ],
    )

    # Calculate distance if coordinates provided
    if latitude and longitude:
        for shop in shops:
            loc = shop.get("location")
            if isinstance(loc, str) and loc:
                try:
                    loc_data = json.loads(loc)
                    s_lat = loc_data.get("latitude") or loc_data.get("lat")
                    s_lon = loc_data.get("longitude") or loc_data.get("long")
                    if s_lat and s_lon:
                        shop["distance"] = haversine(
                            float(latitude),
                            float(longitude),
                            float(s_lat),
                            float(s_lon),
                        )
                    else:
                        shop["distance"] = 99999.0
                except (ValueError, json.JSONDecodeError):
                    shop["distance"] = 99999.0
            else:
                shop["distance"] = 99999.0

    # Sort
    if order_by == "distance" and latitude and longitude:
        shops.sort(key=lambda x: x.get("distance", 99999.0))
    else:
        # Standard sorting
        rev = True if order.lower() == "desc" else False
        shops.sort(
            key=lambda x: str(x.get(order_by or "name")).lower(), reverse=rev
        )

    # Paginate
    shops_slice = shops[limit_start: limit_start + limit_page_length]

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {"gateway_controller": "Cash", "enabled": 1}
    )
    is_global_cod_enabled = bool(cash_gateway)

    # Replicating the structure of the legacy ShopResource
    formatted_shops = []
    for shop in shops_slice:
        # Hierarchical COD: Global AND Shop
        is_cod = is_global_cod_enabled and (
            shop.enable_cod if shop.get("enable_cod") is not None else 1
        )

        formatted_shops.append(
            {
                "id": shop.name,
                "uuid": shop.uuid,
                "slug": shop.slug,
                "user_id": shop.user,
                "tax": shop.tax,
                "service_fee": shop.service_fee,
                "percentage": shop.percentage,
                "phone": shop.phone,
                "open": bool(shop.open),
                "visibility": bool(shop.visibility),
                "verify": bool(shop.verify),
                "logo_img": shop.logo,
                "background_img": shop.cover_photo,
                "min_amount": shop.min_amount,
                "status": shop.status,
                "enable_cod": bool(is_cod),
                "enable_credit": bool(shop.get("enable_credit")),
                "credit_mode": shop.get("credit_mode") or "All Orders",
                "type": shop.shop_type or shop.get("type"),
                "shop_type": shop.shop_type,
                "is_ecommerce": bool(shop.is_ecommerce),
                "distance": shop.get("distance"),
                "delivery_time": {
                    "type": shop.delivery_time_type,
                    "from": shop.delivery_time_from,
                    "to": shop.delivery_time_to,
                },
                "location": shop.location,
                "working_hours": frappe.get_all(
                    "Shop Booking Working Day",
                    filters={"parent": shop.name},
                    fields=["day", "from_time", "to_time"],
                ),
                "closed_dates": frappe.get_all(
                    "Shop Booking Closed Date",
                    filters={"parent": shop.name},
                    fields=["date"],
                ),
                "translation": {"title": shop.name, "address": shop.address},
            }
        )

    return api_response(data=formatted_shops)


@frappe.whitelist(allow_guest=True)
def get_shop_details(uuid: str) -> Any:
    """
    Retrieves a single shop by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    shop = frappe.get_doc("Shop", {"uuid": uuid})

    if not shop:
        frappe.throw(
            f"Shop with UUID {uuid} not found.", frappe.DoesNotExistError
        )

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {"gateway_controller": "Cash", "enabled": 1}
    )
    is_global_cod_enabled = bool(cash_gateway)

    # Hierarchical COD: Global AND Shop
    # Note: shop object from get_doc has attributes directly
    is_cod = is_global_cod_enabled and (
        shop.enable_cod if shop.enable_cod is not None else 1
    )

    # Replicating the structure of the legacy ShopResource
    return api_response(
        data={
            "id": shop.name,
            "uuid": shop.uuid,
            "slug": shop.slug,
            "user_id": shop.user,
            "tax": shop.tax,
            "service_fee": shop.service_fee,
            "percentage": shop.percentage,
            "phone": shop.phone,
            "open": bool(shop.open),
            "visibility": bool(shop.visibility),
            "verify": bool(shop.verify),
            "logo_img": shop.logo,
            "background_img": shop.cover_photo,
            "min_amount": shop.min_amount,
            "status": shop.status,
            "enable_cod": bool(is_cod),
            "enable_credit": bool(shop.get("enable_credit")),
            "credit_mode": shop.get("credit_mode") or "All Orders",
            "type": shop.shop_type
            or shop.type,  # Map new shop_type to legacy type field
            "shop_type": shop.shop_type,
            "is_ecommerce": bool(shop.is_ecommerce),
            "delivery_time": {
                "type": shop.delivery_time_type,
                "from": shop.delivery_time_from,
                "to": shop.delivery_time_to,
            },
            "location": shop.location,
            "working_hours": [d.as_dict() for d in shop.booking_working_days],
            "closed_dates": [d.as_dict() for d in shop.booking_closed_dates],
            "translation": {"title": shop.name, "address": shop.address},
        }
    )


@frappe.whitelist(allow_guest=True)
def search_shops(search: str, category_id: int=None, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Searches for shops by name, optionally filtered by category.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    t_shop = frappe.qb.DocType("Shop")
    query = (
        frappe.qb.from_(t_shop)
        .select(
            t_shop.name,
            t_shop.uuid,
            t_shop.slug,
            t_shop.user,
            t_shop.logo,
            t_shop.cover_photo,
            t_shop.phone,
            t_shop.address,
            t_shop.location,
            t_shop.status,
            t_shop.type,
            t_shop.min_amount,
            t_shop.tax,
            t_shop.delivery_time_type,
            t_shop.delivery_time_from,
            t_shop.delivery_time_to,
            t_shop.open,
            t_shop.visibility,
            t_shop.verify,
            t_shop.service_fee,
            t_shop.percentage,
            t_shop.enable_cod,
            t_shop.enable_credit,
            t_shop.credit_mode,
            t_shop.shop_type,
            t_shop.is_ecommerce,
        )
        .where(t_shop.open == 1)
        .where(t_shop.status == "approved")
        .where(t_shop.visibility == 1)
    )

    if category_id:
        query = query.where(t_shop.category == category_id)

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    query = query.where(
        to_tsvector("english", t_shop.shop_name).matches(
            plainto_tsquery("english", search)
        )
    )

    shops = (
        query.limit(limit_page_length)
        .offset(limit_start)
        .orderby(t_shop.shop_name)
        .run(as_dict=True)
    )

    # Global COD Check
    cash_gateway = frappe.db.get_value(
        "PaaS Payment Gateway", {"gateway_controller": "Cash", "enabled": 1}
    )
    is_global_cod_enabled = bool(cash_gateway)

    formatted_shops = []
    for shop in shops:
        # Hierarchical COD: Global AND Shop
        is_cod = is_global_cod_enabled and (
            shop.enable_cod if shop.enable_cod is not None else 1
        )

        formatted_shops.append(
            {
                "id": shop.name,
                "uuid": shop.uuid,
                "slug": shop.slug,
                "user_id": shop.user,
                "tax": shop.tax,
                "service_fee": shop.service_fee,
                "percentage": shop.percentage,
                "phone": shop.phone,
                "open": bool(shop.open),
                "visibility": bool(shop.visibility),
                "verify": bool(shop.verify),
                "logo_img": shop.logo,
                "background_img": shop.cover_photo,
                "min_amount": shop.min_amount,
                "status": shop.status,
                "enable_cod": bool(is_cod),
                "enable_credit": bool(shop.get("enable_credit")),
                "credit_mode": shop.get("credit_mode") or "All Orders",
                "type": shop.shop_type
                or shop.type,  # Map new shop_type to legacy type field
                "shop_type": shop.shop_type,
                "is_ecommerce": bool(shop.is_ecommerce),
                "delivery_time": {
                    "type": shop.delivery_time_type,
                    "from": shop.delivery_time_from,
                    "to": shop.delivery_time_to,
                },
                "location": shop.location,
                "translation": {"title": shop.name, "address": shop.address},
            }
        )

    return api_response(data=formatted_shops)


@frappe.whitelist(allow_guest=True)
def get_shop_types() -> Any:
    """
    Retrieves all available Shop Types.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    types = frappe.get_all(
        "Shop Type",
        fields=["name", "title", "description", "icon"],
        order_by="title asc",
    )
    return api_response(data=types)


@frappe.whitelist(allow_guest=True)
def get_nearby_shops(latitude: float, longitude: float, radius_km: float=10, lang: str='en') -> Any:
    """
    Retrieves a list of shops within a given radius.
    bypass_sql
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if latitude is None or longitude is None:
        return get_shops()

    if latitude is None or longitude is None:
        return get_shops()

    try:
        lat = float(latitude)
        lon = float(longitude)
        radius = float(radius_km)
    except (ValueError, TypeError):
        return get_shops()

    # The Shop doctype has no latitude/longitude columns -- coordinates
    # live inside the location JSON (Geolocation) field, so fetch the
    # candidates and distance-filter in Python. Shops without usable
    # coordinates are excluded, matching the old "IS NOT NULL" intent.
    from rcore.base.api.utils import haversine

    candidates = frappe.get_all("Shop", fields=["name", "location"])
    nearby_shop_ids = []
    for candidate in candidates:
        s_lat, s_lon = get_shop_coords(candidate)
        if s_lat is None or s_lon is None:
            continue
        if haversine(lat, lon, s_lat, s_lon) < radius:
            nearby_shop_ids.append(candidate.name)

    # Include Ecommerce shops (global reach)
    ecommerce_shops = frappe.get_all(
        "Shop", filters={"is_ecommerce": 1}, pluck="name"
    )
    nearby_shop_ids.extend(ecommerce_shops)

    # Unique IDs
    nearby_shop_ids = list(set(nearby_shop_ids))

    # Now use generic get_shops_by_ids to return formatted data
    return get_shops_by_ids(shop_ids=nearby_shop_ids)


@frappe.whitelist()
def get_shops_recommend(latitude: float, longitude: float, lang: str='en') -> Any:
    """
    Returns recommended shops based on location and rating.
    Currently aliases to get_nearby_shops as we lack a rating field.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    return get_nearby_shops(latitude, longitude, radius_km=20, lang=lang)


@frappe.whitelist(allow_guest=True)
def check_driver_zone(shop_id: Any=None, address: Any=None) -> Any:
    """
    Checks if the address is within the shop's delivery zone.
    Expects address as dict/json with latitude/longitude.
    bypass_sql
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    import json

    if isinstance(address, str):
        try:
            address = json.loads(address)
        except ValueError:
            frappe.throw("Invalid address format", frappe.ValidationError)

    if (
        not address
        or not address.get("latitude")
        or not address.get("longitude")
    ):
        frappe.throw(
            "Address must contain latitude and longitude",
            frappe.ValidationError,
        )

    user_lat = float(address.get("latitude"))
    user_lon = float(address.get("longitude"))

    # Get Shop Location (coordinates live in the Shop.location JSON field;
    # the Shop doctype has no latitude/longitude columns)
    shop_lat, shop_lon = get_shop_coords(shop_id)
    if shop_lat is None or shop_lon is None:
        return api_response(
            data={"status": False, "message": "Shop location not found"}
        )

    # Great-circle distance in Python (paas.api.utils.haversine, km) —
    # same as get_nearby_shops; avoids depending on the PostgreSQL
    # cube/earthdistance extensions (this SQL was unreachable dead code
    # before the phantom-column fix, so the extension may well not be
    # installed).
    from rcore.base.api.utils import haversine

    distance_km = haversine(user_lat, user_lon, shop_lat, shop_lon)

    # Default Max Radius: 50km (Can be made configurable in Shop settings
    # later)
    max_radius_km = 50.0

    return api_response(
        data={
            "status": distance_km <= max_radius_km,
            "distance": round(distance_km, 2),
        }
    )


@frappe.whitelist(allow_guest=True)
def get_shops_by_ids(shop_ids: list=None, **kwargs) -> Any:
    """
    Retrieves shops by a list of IDs.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    _filters = {}  # noqa: F841
    ids_to_filter = shop_ids

    # Handle possible JSON string or alternative kwarg
    if kwargs.get("shops"):
        try:
            import json

            ids_to_filter = (
                json.loads(kwargs.get("shops"))
                if isinstance(kwargs.get("shops"), str)
                else kwargs.get("shops")
            )
        except Exception:
            ids_to_filter = None

    if not ids_to_filter:
        return api_response(data=[])

    shops = frappe.get_list(
        "Shop",
        filters={"name": ["in", ids_to_filter]},
        fields=[
            "name",
            "shop_name",
            "uuid",
            "slug",
            "user",
            "logo",
            "cover_photo",
            "phone",
            "address",
            "location",
            "status",
            "type",
            "min_amount",
            "tax",
            "delivery_time_type",
            "delivery_time_from",
            "delivery_time_to",
            "open",
            "visibility",
            "verify",
            "service_fee",
            "percentage",
            "enable_cod",
            "enable_credit",
            "credit_mode",
            "shop_type",
            "is_ecommerce",
        ],
    )

    # Simple formatter (reuse get_shops logic ideally, but keep simple here)
    formatted_shops = []
    for shop in shops:
        formatted_shops.append(
            {
                "id": shop.name,
                "uuid": shop.uuid,
                "slug": shop.slug,
                "logo_img": shop.logo,
                "background_img": shop.cover_photo,
                "translation": {"title": shop.name, "address": shop.address},
            }
        )

    return api_response(data=formatted_shops)


@frappe.whitelist()
def check_cashback(shop_id: str, amount: float, lang: str='en') -> Any:
    """
    Checks the cashback for a given shop and amount based on defined rules.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    cashback_rule = frappe.db.get_value(
        "Cashback Rule",
        filters={"shop": shop_id, "min_amount": ["<=", amount]},
        fieldname=["percentage"],
        order_by="min_amount desc",
    )

    if cashback_rule:
        cashback_amount = (amount * cashback_rule) / 100
        return {"cashback_amount": cashback_amount}

    return {"cashback_amount": 0}


@frappe.whitelist(allow_guest=True)
def get_nearest_delivery_points(latitude: float, longitude: float, radius_km: float=50) -> Any:
    """
    Retrieves a list of active Delivery Points within a given radius.
    bypass_sql
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if latitude is None or longitude is None:
        frappe.throw(
            "Latitude and Longitude are required.", frappe.ValidationError
        )

    try:
        lat = float(latitude)
        lon = float(longitude)
        radius = float(radius_km) * 1000  # meters
    except ValueError:
        frappe.throw(
            "Invalid Latitude or Longitude format.", frappe.ValidationError
        )

    # Calculate distance in SQL: earth_distance(ll_to_earth(lat, lon), ll_to_earth(db_lat, db_lon))
    # We select fields matchng the original response
    query = """
        SELECT
            name, latitude, longitude, address, price, active,
            (earth_distance(ll_to_earth(%s, %s), ll_to_earth(latitude, longitude)) / 1000) as distance_km
        FROM "tabDelivery Point"
        WHERE
            active = 1
            AND latitude IS NOT NULL AND longitude IS NOT NULL
            AND earth_box(ll_to_earth(%s, %s), %s) @> ll_to_earth(latitude, longitude)
            AND earth_distance(ll_to_earth(%s, %s), ll_to_earth(latitude, longitude)) < %s
        ORDER BY distance_km ASC
    """

    nearby_points = frappe.db.sql(
        query, (lat, lon, lat, lon, radius, lat, lon, radius), as_dict=True
    )

    # Format explicitly if needed (frappe.db.sql returns dicts/values)
    # The original returned list of dicts.
    return nearby_points
