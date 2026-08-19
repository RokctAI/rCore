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
import frappe
import json
from rcore.base.api.utils import api_response


@frappe.whitelist(allow_guest=True)
def get_products(limit_start: int=0, limit_page_length: int=20, category_id: str=None, brand_id: str=None, shop_id: str=None, order_by: str=None, rating: str=None, search: str=None) -> Any:
    """
    Retrieves a list of products (Items) with pagination, advanced filters, and sorting.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    params = {}
    conditions = [
        "t_item.disabled = 0",
        "t_item.has_variants = 0",
        # Assuming is_visible_in_website is the correct field for frontend
        # visibility
        "t_item.is_visible_in_website = 1",
        "t_item.status = 'Published'",
        "t_item.approval_status = 'Approved'",
    ]

    if category_id:
        conditions.append("t_item.item_group = %(category_id)s")
        params["category_id"] = category_id

    if brand_id:
        conditions.append("t_item.brand = %(brand_id)s")
        params["brand_id"] = brand_id

    if shop_id:
        conditions.append("t_item.shop = %(shop_id)s")
        params["shop_id"] = shop_id

    if search:
        conditions.append("t_item.item_name LIKE %(search)s")
        params["search"] = f"%{search}%"

    # --- Joins and Ordering Logic ---
    t_item = frappe.qb.DocType("Item")
    query = (
        frappe.qb.from_(t_item)
        .select(
            t_item.name,
            t_item.item_name,
            t_item.description,
            t_item.image,
            t_item.standard_rate,
            t_item.creation,
        )
        .where(t_item.disabled == 0)
        .where(t_item.has_variants == 0)
        # Assuming is_visible_in_website is the correct field for frontend
        # visibility
        .where(t_item.is_visible_in_website == 1)
        .where(t_item.status == "Published")
        .where(t_item.approval_status == "Approved")
    )

    if category_id:
        query = query.where(t_item.item_group == category_id)

    if brand_id:
        query = query.where(t_item.brand == brand_id)

    if shop_id:
        query = query.where(t_item.shop == shop_id)

    if search:
        from frappe.query_builder.functions import Function
        from pypika.terms import Term

        class MatchTerm(Term):
            def __init__(self, left, right, alias=None):
                super().__init__(alias)
                self.left = left
                self.right = right

            def get_sql(self, **kwargs):
                return f"{
                    self.left.get_sql(
                        **kwargs)} @@ {
                    self.right.get_sql(
                        **kwargs)}"

        # Instantiate functions
        ts_vector = Function("to_tsvector", "english", t_item.item_name)
        ts_query = Function("plainto_tsquery", "english", search)

        # Use custom term for @@ operator
        query = query.where(MatchTerm(ts_vector, ts_query))

    # Rating filter and sorting
    if rating or order_by in ["high_rating", "low_rating"]:
        t_review = frappe.qb.DocType("Review")
        from frappe.query_builder.functions import Avg, Count, Sum

        # Subquery for average rating
        subquery = (
            frappe.qb.from_(t_review)
            .select(
                t_review.reviewable_id, Avg(t_review.rating).as_("avg_rating")
            )
            .where(t_review.reviewable_type == "Item")
            .groupby(t_review.reviewable_id)
        ).as_("t_reviews")

        query = query.left_join(subquery).on(
            subquery.reviewable_id == t_item.name
        )

        if rating:
            try:
                min_rating, max_rating = map(float, rating.split(","))
                query = query.where(subquery.avg_rating >= min_rating).where(
                    subquery.avg_rating <= max_rating
                )
            except (ValueError, IndexError):
                pass  # Ignore invalid rating format

        if order_by == "high_rating":
            query = query.orderby(
                subquery.avg_rating, order=frappe.qb.desc
            ).orderby(subquery.avg_rating.isnull())
        elif order_by == "low_rating":
            query = query.orderby(
                subquery.avg_rating, order=frappe.qb.asc
            ).orderby(subquery.avg_rating.isnull())

    # Sales-based sorting
    elif order_by in ["best_sale", "low_sale"]:
        t_sales_item = frappe.qb.DocType("Sales Invoice Item")
        from frappe.query_builder.functions import Sum

        # Subquery for sales quantity
        subquery = (
            frappe.qb.from_(t_sales_item)
            .select(
                t_sales_item.item_code, Sum(t_sales_item.qty).as_("total_qty")
            )
            .groupby(t_sales_item.item_code)
        ).as_("t_sales")

        query = query.left_join(subquery).on(subquery.item_code == t_item.name)

        if order_by == "best_sale":
            query = query.orderby(
                subquery.total_qty, order=frappe.qb.desc
            ).orderby(subquery.total_qty.isnull())
        elif order_by == "low_sale":
            query = query.orderby(
                subquery.total_qty, order=frappe.qb.asc
            ).orderby(subquery.total_qty.isnull())

    elif order_by == "new":
        query = query.orderby(t_item.creation, order=frappe.qb.desc)
    elif order_by == "old":
        query = query.orderby(t_item.creation, order=frappe.qb.asc)
    else:
        # Default order
        query = query.orderby(t_item.creation, order=frappe.qb.desc)

    # Pagination
    query = query.limit(limit_page_length).offset(limit_start)

    products = query.run(as_dict=True)

    if not products:
        return []

    # --- Eager Loading for Performance ---
    product_names = [p["name"] for p in products]

    # Get stock levels
    stocks = frappe.get_all(
        "Bin",
        fields=["item_code", "actual_qty"],
        filters={"item_code": ["in", product_names], "actual_qty": [">", 0]},
    )
    stocks_map = {s["item_code"]: s["actual_qty"] for s in stocks}

    # Get active discounts
    today = frappe.utils.nowdate()
    discounts_map = {}

    # Check if Pricing Rule exists and has item_code (to avoid issues in test
    # envs or limited installs)
    if frappe.db.exists("DocType", "Pricing Rule") and frappe.db.has_column(
        "Pricing Rule", "item_code"
    ):
        try:
            pricing_rules = frappe.get_all(
                "Pricing Rule",
                filters={
                    "disable": 0,
                    "valid_from": ["<=", today],
                    "valid_upto": [">=", today],
                    "apply_on": "Item Code",
                    "item_code": ["in", product_names],
                },
                fields=[
                    "item_code",
                    "rate_or_discount",
                    "discount_percentage",
                ],
            )
            discounts_map = {rule["item_code"]: rule for rule in pricing_rules}
        except Exception:
            # Fallback if something is wrong with Pricing Rule schema
            pass

    # Get review averages and counts
    # Using frappe.qb for reviews aggregation as well
    from frappe.query_builder.functions import Avg, Count, Sum  # noqa: F811

    t_review = frappe.qb.DocType("Review")
    reviews_query = (
        frappe.qb.from_(t_review)
        .select(
            t_review.reviewable_id,
            Avg(t_review.rating).as_("avg_rating"),
            Count("*").as_("reviews_count"),
        )
        .where(t_review.reviewable_type == "Item")
        .where(t_review.reviewable_id.isin(product_names))
        .groupby(t_review.reviewable_id)
    )
    reviews_data = reviews_query.run(as_dict=True)

    reviews_map = {r["reviewable_id"]: r for r in reviews_data}

    # --- Assemble Final Response ---
    for p in products:
        p["stock_quantity"] = stocks_map.get(p.name, 0)
        p["discount"] = discounts_map.get(p.name)
        p["reviews"] = reviews_map.get(
            p.name, {"avg_rating": 0, "reviews_count": 0}
        )

    return api_response(data=products)


@frappe.whitelist(allow_guest=True)
def most_sold_products(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of most sold products.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    from frappe.query_builder.functions import Sum

    t_sales_item = frappe.qb.DocType("Sales Invoice Item")
    most_sold_items = (
        frappe.qb.from_(t_sales_item)
        .select(t_sales_item.item_code, Sum(t_sales_item.qty).as_("total_qty"))
        .groupby(t_sales_item.item_code)
        .orderby("total_qty", order=frappe.qb.desc)
        .limit(limit_page_length)
        .offset(limit_start)
    ).run(as_dict=True)

    item_codes = [d.item_code for d in most_sold_items]

    if not item_codes:
        return api_response(data=[])

    items = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"name": ("in", item_codes)},
        order_by="name",
    )
    return api_response(data=items)


@frappe.whitelist(allow_guest=True)
def get_discounted_products(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of products with active discounts.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    today = frappe.utils.nowdate()

    # Get all active pricing rules
    active_rules = frappe.get_all(
        "Pricing Rule",
        filters={
            "disable": 0,
            "valid_from": ("<=", today),
            "valid_upto": (">=", today),
        },
        fields=["name", "apply_on", "item_code", "item_group", "brand"],
    )

    item_codes = set()

    # Check if keys exist in Pricing Rule schema to avoid errors
    has_item_code = frappe.db.has_column("Pricing Rule", "item_code")
    has_item_group = frappe.db.has_column("Pricing Rule", "item_group")
    has_brand = frappe.db.has_column("Pricing Rule", "brand")

    for rule in active_rules:
        if rule.apply_on == "Item Code" and has_item_code and rule.item_code:
            item_codes.add(rule.item_code)
        elif (
            rule.apply_on == "Item Group"
            and has_item_group
            and rule.item_group
        ):
            items_in_group = frappe.get_all(
                "Item", filters={"item_group": rule.item_group}, pluck="name"
            )
            item_codes.update(items_in_group)
        elif rule.apply_on == "Brand" and has_brand and rule.brand:
            items_in_brand = frappe.get_all(
                "Item", filters={"brand": rule.brand}, pluck="name"
            )
            item_codes.update(items_in_brand)

    if not item_codes:
        return api_response(data=[])

    # Paginate on the final list of item codes
    paginated_item_codes = list(item_codes)[
        limit_start: limit_start + limit_page_length
    ]

    if not paginated_item_codes:
        return api_response(data=[])

    items = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"name": ("in", paginated_item_codes)},
        order_by="name",
    )
    return api_response(data=items)


@frappe.whitelist(allow_guest=True)
def get_products_by_ids(ids: list, **kwargs) -> Any:
    """
    Retrieves a list of products by their IDs.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    filters = {}
    product_ids_to_filter = ids

    if kwargs.get("product_ids"):
        p_ids = kwargs.get("product_ids")
        if isinstance(p_ids, str):
            import json  # noqa: F811

            try:
                p_ids = json.loads(p_ids)
            except json.JSONDecodeError:
                pass  # Handle invalid JSON gracefully
        if isinstance(p_ids, list):
            product_ids_to_filter = p_ids

    if not product_ids_to_filter:
        return api_response(data=[])

    filters["name"] = ["in", product_ids_to_filter]

    items = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters=filters,
        order_by="name",
    )
    return api_response(data=items)


def _public_product_data(product: Any) -> dict:
    """
    Builds the public (guest-safe) representation of an Item.

    Explicit allowlist: unauthenticated endpoints must never return the
    full document (``as_dict()``), which would expose internal fields
    such as cost/valuation rates, approval workflow state, and
    ownership/audit metadata.
    """
    return {
        "id": product.name,
        "uuid": product.get("uuid"),
        "name": product.item_name,
        "description": product.description,
        "img": product.image,
        "price": product.standard_rate,
        "unit": product.stock_uom,
        "shop_id": product.get("shop"),
        "category_id": product.item_group,
        "brand_id": product.get("brand"),
        "keywords": product.get("keywords"),
        "tax": product.get("tax"),
        "interval": product.get("interval"),
        "min_qty": product.get("min_qty"),
        "max_qty": product.get("max_qty"),
        "created_at": product.creation,
        "updated_at": product.modified,
        "galleries": [],
        "stocks": [],
        "extras": [],
    }


@frappe.whitelist(allow_guest=True)
def get_product_by_slug(slug: str) -> Any:
    """
    Retrieves a single product by its slug.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    product = frappe.get_doc("Item", {"route": slug})
    return api_response(data=_public_product_data(product))


@frappe.whitelist(allow_guest=True)
def read_product_file(uuid: str) -> Any:
    """
    Reads a product file.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    product = frappe.get_doc("Item", {"uuid": uuid})
    if not product.image:
        frappe.throw("Product does not have an image.")

    try:
        file = frappe.get_doc("File", {"file_url": product.image})
        return api_response(data=file.get_content())
    except frappe.DoesNotExistError:
        frappe.throw("File not found.")


@frappe.whitelist(allow_guest=True)
def get_product_reviews(uuid: str, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves reviews for a specific product by its UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    product_name = frappe.db.get_value("Item", {"uuid": uuid}, "name")
    if not product_name:
        frappe.throw("Product not found.")

    reviews = frappe.get_list(
        "Review",
        fields=["name", "user", "rating", "comment", "creation"],
        filters={
            "reviewable_type": "Item",
            "reviewable_id": product_name,
            "published": 1,
        },
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return api_response(data=reviews)


@frappe.whitelist(allow_guest=True)
def order_products_calculate(products: list) -> Any:
    """
    Calculates the total price of a list of products.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    total_price = 0
    for product in products:
        item = frappe.get_doc("Item", product.get("product_id"))
        total_price += item.standard_rate * product.get("quantity", 1)
    return api_response(data={"total_price": total_price})


@frappe.whitelist(allow_guest=True)
def get_products_by_brand(brand_id: str, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of products for a given brand.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    products = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"brand": brand_id},
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return api_response(data=products)


@frappe.whitelist(allow_guest=True)
def products_search(search: str, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Searches for products by a search term.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    t_item = frappe.qb.DocType("Item")
    query = frappe.qb.from_(t_item).select(
        t_item.name,
        t_item.item_name,
        t_item.description,
        t_item.image,
        t_item.standard_rate,
    )

    from frappe.query_builder.functions import Function

    to_tsvector = Function("to_tsvector")
    plainto_tsquery = Function("plainto_tsquery")
    query = query.where(
        to_tsvector("english", t_item.item_name).matches(
            plainto_tsquery("english", search)
        )
    )

    products = (
        query.limit(limit_page_length)
        .offset(limit_start)
        .orderby(t_item.name)
        .run(as_dict=True)
    )
    return api_response(data=products)


@frappe.whitelist(allow_guest=True)
def get_products_by_category(uuid: str, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of products for a given category.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    category_name = frappe.db.get_value("Category", {"uuid": uuid}, "name")
    if not category_name:
        frappe.throw("Category not found.")

    products = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"item_group": category_name},
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return api_response(data=products)


@frappe.whitelist(allow_guest=True)
def get_products_by_shop(shop_id: str, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of products for a given shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    products = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"shop": shop_id},
        offset=limit_start,
        limit=limit_page_length,
        order_by="name",
    )
    return api_response(data=products)


@frappe.whitelist()
def add_product_review(uuid: str, rating: float, comment: str=None) -> Any:
    """
    Adds a review for a product by its UUID, but only if the user has purchased it.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user

    if user == "Guest":
        frappe.throw("You must be logged in to leave a review.")

    product_name = frappe.db.get_value("Item", {"uuid": uuid}, "name")
    if not product_name:
        frappe.throw("Product not found.")

    # Check if user has purchased this item
    has_purchased = frappe.db.exists(
        "Sales Invoice Item",
        {
            "item_code": product_name,
            "parent": (
                "in",
                frappe.get_all(
                    "Sales Invoice", filters={"customer": user}, pluck="name"
                ),
            ),
        },
    )

    if not has_purchased:
        frappe.throw("You can only review products you have purchased.")

    # Check if user has already reviewed this item
    if frappe.db.exists(
        "Review",
        {
            "reviewable_type": "Item",
            "reviewable_id": product_name,
            "user": user,
        },
    ):
        frappe.throw("You have already reviewed this product.")

    review = frappe.get_doc(
        {
            "doctype": "Review",
            "reviewable_type": "Item",
            "reviewable_id": product_name,
            "user": user,
            "rating": rating,
            "comment": comment,
            "published": 1,
        }
    )
    review.insert(ignore_permissions=True)
    return api_response(
        data=review.as_dict(), message="Review added successfully"
    )


@frappe.whitelist()
def get_product_history(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves the viewing history for the current user, specific to products (Items).
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to view your history.")

    # Get the names of the items the user has viewed
    viewed_item_names = frappe.get_all(
        "View Log",
        filters={"user": user, "doctype": "Item"},
        fields=["docname"],
        order_by="creation desc",
        offset=limit_start,
        limit=limit_page_length,
        distinct=True,
    )

    item_names = [d.docname for d in viewed_item_names]

    if not item_names:
        return api_response(data=[])

    # Fetch the actual product details for the viewed items
    products = frappe.get_list(
        "Item",
        fields=["name", "item_name", "description", "image", "standard_rate"],
        filters={"name": ("in", item_names)},
    )

    return api_response(data=products)


@frappe.whitelist(allow_guest=True)
def get_product_by_uuid(uuid: Any) -> Any:
    """
    Retrieves a single product by UUID.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    try:
        product_name = frappe.db.get_value("Item", {"uuid": uuid}, "name")
        if not product_name:
            frappe.throw("Product not found", frappe.DoesNotExistError)

        product = frappe.get_doc("Item", product_name)

        # Explicit public shape — never the full document
        return api_response(data=_public_product_data(product))
    except Exception as e:
        frappe.throw(f"Error fetching product: {str(e)}")


@frappe.whitelist(allow_guest=True)
def calculate_product_price(products: Any) -> Any:
    """
    Calculates prices for products.
    Expects 'products' as a list of dicts: [{'id': ..., 'quantity': ...}] or JSON string.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if isinstance(products, str):
        import json  # noqa: F811

        products = json.loads(products)

    total_price = 0
    total_tax = 0

    for item in products:
        # Resolve item ID to price
        # item['id'] usually maps to stock_id/variant
        rate = (
            frappe.db.get_value("Item", item.get("id"), "standard_rate") or 0
        )
        qty = float(item.get("quantity", 0))
        total_price += rate * qty

    return api_response(
        data={
            "total_price": total_price,
            "total_tax": total_tax,
            "total_shop_tax": 0,
        }
    )


@frappe.whitelist()
def add_product_review(product_uuid: Any, rating: Any, comment: Any=None, images: Any=None) -> Any:
    """
    Adds a review for a product by its UUID, verifying ownership if enabled.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("You must be logged in to leave a review.")

    product_name = frappe.db.get_value("Item", {"uuid": product_uuid}, "name")
    if not product_name:
        frappe.throw("Product not found.")

    # Check if user has purchased this item (Highly recommended for
    # high-quality data)
    has_purchased = frappe.db.exists(
        "Sales Invoice Item",
        {
            "item_code": product_name,
            "parent": (
                "in",
                frappe.get_all(
                    "Sales Invoice", filters={"customer": user}, pluck="name"
                ),
            ),
        },
    )

    if not has_purchased:
        # We might want to allow reviews even without purchase in some cases,
        # but for now, following the stricter requirement.
        frappe.throw("You can only review products you have purchased.")

    # Check if user has already reviewed this item
    if frappe.db.exists(
        "Review",
        {
            "reviewable_type": "Item",
            "reviewable_id": product_name,
            "user": user,
        },
    ):
        frappe.throw("You have already reviewed this product.")

    review_data = {
        "doctype": "Review",
        "reviewable_type": "Item",
        "reviewable_id": product_name,
        "user": user,
        "rating": rating,
        "comment": comment,
        "published": 1,
    }

    # Handle images if provided
    if images and isinstance(images, list) and len(images) > 0:
        # Assuming we just store the first image in a field if 'Review' has it,
        # or we might need a child table for multi-image.
        # Standard 'Review' usually doesn't have multiple images by default.
        pass

    review = frappe.get_doc(review_data)
    review.insert(ignore_permissions=True)

    return api_response(
        data=review.as_dict(), message="Review added successfully"
    )


@frappe.whitelist()
def get_suggest_price(item_code: str=None, lang: str='en', currency: str='ZAR') -> Any:
    """
    Retrieves a suggested price range based on similar items in the same category.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    import datetime

    min_price = 1.0
    max_price = 1000.0

    if item_code:
        category = frappe.db.get_value("Item", item_code, "item_group")
        if category:
            prices = frappe.get_all(
                "Item",
                filters={"item_group": category, "standard_rate": [">", 0]},
                pluck="standard_rate",
            )
            if prices:
                min_price = min(prices)
                max_price = max(prices)

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "status": True,
        "message": "Suggested price retrieved",
        "data": {
            "min": float(min_price),
            "max": float(max_price),
            "currency": currency,
        },
    }


@frappe.whitelist()
def get_product_calculations(item_code: str, quantity: int, lang: str='en') -> Any:
    """
    Calculates the price for a single product.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    item = frappe.get_doc("Item", item_code)
    # Using standard_rate as per other functions in this file
    price = item.standard_rate or 0.0
    total_price = price * quantity
    return {"total_price": total_price}
