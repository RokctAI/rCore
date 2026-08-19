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
# Tenant context: session.user validation
import frappe
import json
from ..utils import _require_admin


@frappe.whitelist()
def get_admin_statistics() -> Any:
    """
    The get_admin_statistics function retrieves detailed statistics for the admin dashboard, including cards and charts. This function does not take any parameters. It returns a dictionary containing two main sections: cards and charts. The cards section provides an overview of key metrics such as total users, shops, orders, sales, and product reviews. The charts section includes data for visualizing orders per day, new users per day, new shops per day, and order status breakdown over the last 30 days. The function requires admin privileges to execute.
    """
    """
    Retrieves detailed statistics for the admin dashboard including cards and charts.
    """
    _require_admin()

    # Cards
    total_users = frappe.db.count("User")
    total_shops = frappe.db.count("Company")
    total_orders = frappe.db.count("Order")

    t_order = frappe.qb.DocType("Order")
    total_sales = (
        frappe.qb.from_(t_order)
        .select(frappe.qb.fn.Sum(t_order.grand_total))
        .where(t_order.status == "Delivered")
    ).run()[0][0] or 0

    in_progress_orders = frappe.db.count(
        "Order",
        {"status": ["in", ["Pending", "Processing", "Ready", "On the way"]]},
    )
    cancelled_orders = frappe.db.count("Order", {"status": "Cancelled"})
    delivered_orders = frappe.db.count("Order", {"status": "Delivered"})
    total_products = frappe.db.count("Product")
    total_reviews = frappe.db.count("Review")

    # Charts Data (Last 30 Days)
    from frappe.utils import add_days, nowdate

    # helper for date grouping compatible with most dbs
    # using frappe.qb.fn.Date for Date extraction

    cutoff_date = add_days(nowdate(), -30)

    # Orders per Day
    orders_chart = (
        frappe.qb.from_(t_order)
        .select(
            frappe.qb.fn.Date(t_order.creation).as_("date"),
            frappe.qb.fn.Count("*").as_("count"),
        )
        .where(t_order.creation > cutoff_date)
        .groupby(frappe.qb.fn.Date(t_order.creation))
        .orderby(frappe.qb.fn.Date(t_order.creation), order=frappe.qb.asc)
    ).run(as_dict=True)

    # New Users per Day
    t_user = frappe.qb.DocType("User")
    users_chart = (
        frappe.qb.from_(t_user)
        .select(
            frappe.qb.fn.Date(t_user.creation).as_("date"),
            frappe.qb.fn.Count("*").as_("count"),
        )
        .where(t_user.creation > cutoff_date)
        .groupby(frappe.qb.fn.Date(t_user.creation))
        .orderby(frappe.qb.fn.Date(t_user.creation), order=frappe.qb.asc)
    ).run(as_dict=True)

    # New Shops per Day
    t_company = frappe.qb.DocType("Company")
    shops_chart = (
        frappe.qb.from_(t_company)
        .select(
            frappe.qb.fn.Date(t_company.creation).as_("date"),
            frappe.qb.fn.Count("*").as_("count"),
        )
        .where(t_company.creation > cutoff_date)
        .groupby(frappe.qb.fn.Date(t_company.creation))
        .orderby(frappe.qb.fn.Date(t_company.creation), order=frappe.qb.asc)
    ).run(as_dict=True)

    # Order Status Breakdown
    status_chart = (
        frappe.qb.from_(t_order)
        .select(t_order.status, frappe.qb.fn.Count("*").as_("count"))
        .groupby(t_order.status)
    ).run(as_dict=True)

    return {
        "cards": {
            "total_users": total_users,
            "total_shops": total_shops,
            "total_orders": total_orders,
            "total_sales": total_sales,
            "in_progress_orders": in_progress_orders,
            "cancelled_orders": cancelled_orders,
            "delivered_orders": delivered_orders,
            "total_products": total_products,
            "total_reviews": total_reviews,
        },
        "charts": {
            "orders_per_day": orders_chart,
            "new_users": users_chart,
            "new_shops": shops_chart,
            "order_status": status_chart,
        },
    }


@frappe.whitelist()
def get_multi_company_sales_report(from_date: str, to_date: str, company: str=None) -> Any:
    """
    The get_multi_company_sales_report function generates a sales report for a specified date range, allowing administrators to retrieve data for a single company or all companies. The function takes three parameters: from_date and to_date, which define the date range for the report, and an optional company parameter, which filters the results to a specific company if provided. If the company parameter is not specified, the function returns data for all companies. The report includes order details such as name, shop, user, grand total, status, and creation date, as well as calculated commission amounts based on the sales commission rate for each company.
    """
    """
    Retrieves a sales report for a specific company or all companies within a date range (for admins).
    """
    _require_admin()

    filters = {"creation": ["between", [from_date, to_date]]}
    if company:
        filters["shop"] = company

    sales_report = frappe.get_all(
        "Order",
        filters=filters,
        fields=["name", "shop", "user", "grand_total", "status", "creation"],
        order_by="creation desc",
    )

    # Get commission rates for all shops
    commission_rates = frappe.get_all(
        "Company",
        fields=["name", "sales_commission_rate"],
        filters={"sales_commission_rate": [">", 0]},
    )
    commission_map = {
        c["name"]: c["sales_commission_rate"] for c in commission_rates
    }

    for order in sales_report:
        commission_rate = commission_map.get(order.shop, 0)
        order.commission = (order.grand_total * commission_rate) / 100

    return sales_report


@frappe.whitelist()
def get_admin_report(doctype: str, fields: str, filters: str=None, limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a report for a specified doctype with given fields and filters (for admins).
    """
    _require_admin()

    if isinstance(fields, str):
        fields = json.loads(fields)

    if filters and isinstance(filters, str):
        filters = json.loads(filters)

    return frappe.get_list(
        doctype,
        fields=fields,
        filters=filters,
        limit_start=limit_start,
        limit_page_length=limit_page_length,
    )


@frappe.whitelist()
def get_all_wallet_histories(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all wallet histories on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Wallet History",
        fields=["name", "wallet", "type", "price", "status", "created_at"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def get_all_transactions(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all transactions on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Transaction",
        fields=[
            "name",
            "transaction_date",
            "reference_doctype",
            "reference_name",
            "debit",
            "credit",
            "currency",
        ],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )


@frappe.whitelist()
def get_all_seller_payouts(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all seller payouts on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Seller Payout",
        fields=["name", "shop", "amount", "payout_date", "status"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="payout_date desc",
    )


@frappe.whitelist()
def get_all_shop_bonuses(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all shop bonuses on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Shop Bonus",
        fields=["name", "shop", "amount", "bonus_date", "reason"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="bonus_date desc",
    )
