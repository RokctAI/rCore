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
from rcore.base.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_statistics() -> Any:
    """
    Retrieves sales and order statistics for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    progress_orders_count = frappe.db.count(
        "Order",
        {"shop": shop, "status": ["in", ["New", "Accepted", "Shipped"]]},
    )
    cancel_orders_count = frappe.db.count(
        "Order", {"shop": shop, "status": "Cancelled"}
    )
    delivered_orders_count = frappe.db.count(
        "Order", {"shop": shop, "status": "Delivered"}
    )

    # Products out of stock: Count Stock items with quantity <= 0 for this
    # shop's products
    t_stock = frappe.qb.DocType("Stock")
    t_product = frappe.qb.DocType("Product")

    products_out_of_count = (
        frappe.qb.from_(t_stock)
        .join(t_product)
        .on(t_stock.product == t_product.name)
        .select(frappe.qb.fn.Count(t_stock.name))
        .where(t_product.shop == shop)
        .where(t_stock.quantity <= 0)
        .where(t_product.active == 1)
    ).run()[0][0]

    products_count = frappe.db.count("Product", {"shop": shop, "active": 1})

    # Reviews count (assuming Review DocType has a 'shop' field or linked via
    # 'order')
    try:
        reviews_count = frappe.db.count("Review", {"shop": shop})
    except Exception:
        reviews_count = 0

    # Financials (Delivered orders only)
    t_order = frappe.qb.DocType("Order")
    financials_query = (
        frappe.qb.from_(t_order)
        .select(
            frappe.qb.fn.Sum(t_order.grand_total).as_("total_earned"),
            frappe.qb.fn.Sum(t_order.delivery_fee).as_("delivery_earned"),
            frappe.qb.fn.Sum(t_order.tax).as_("tax_earned"),
            frappe.qb.fn.Sum(t_order.commission_fee).as_("commission_earned"),
        )
        .where(t_order.shop == shop)
        .where(t_order.status == "Delivered")
    )
    financials = financials_query.run(as_dict=True)[0]

    t_order_item = frappe.qb.DocType("Order Item")
    t_item = frappe.qb.DocType("Item")

    top_selling_products = (
        frappe.qb.from_(t_order_item)
        .join(t_order)
        .on(t_order.name == t_order_item.parent)
        .join(t_item)
        .on(t_item.name == t_order_item.product)
        .select(
            t_order_item.product,
            t_item.item_name,
            frappe.qb.fn.Sum(t_order_item.quantity).as_("total_quantity"),
        )
        .where(t_order.shop == shop)
        .groupby(t_order_item.product)
        .groupby(t_item.item_name)
        .orderby("total_quantity", order=frappe.qb.desc)
        .limit(10)
    ).run(as_dict=True)

    return {
        "progress_orders_count": progress_orders_count,
        "cancel_orders_count": cancel_orders_count,
        "delivered_orders_count": delivered_orders_count,
        "products_out_of_count": products_out_of_count,
        "products_count": products_count,
        "reviews_count": reviews_count,
        "total_earned": financials.get("total_earned") or 0,
        "delivery_earned": financials.get("delivery_earned") or 0,
        "tax_earned": financials.get("tax_earned") or 0,
        "commission_earned": financials.get("commission_earned") or 0,
        "top_selling_products": top_selling_products,
    }


@frappe.whitelist()
def get_seller_sales_report(from_date: str, to_date: str) -> Any:
    """
    Retrieves a sales report for the current seller's shop within a date range.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    sales_report = frappe.get_all(
        "Order",
        filters={"shop": shop, "creation": ["between", [from_date, to_date]]},
        fields=["name", "user", "grand_total", "status", "creation"],
        order_by="creation desc",
    )
    return sales_report
