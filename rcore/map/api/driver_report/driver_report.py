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
from rcore.delivery.api.delivery_man.delivery_man import (
    get_deliveryman_order_report as _get_report,
)


@frappe.whitelist()
def get_order_report(from_date: Any=None, to_date: Any=None) -> Any:
    """
    The get_order_report function generates a sales report for orders placed within a specified date range. It accepts two optional parameters: from_date and to_date, which represent the start and end dates of the reporting period, respectively. If either parameter is not provided, the function defaults to a date range of the last month, with from_date set to one month prior to the current date and to_date set to the current date. The function returns the sales report data for the specified period, obtained by calling the get_seller_sales_report function with the determined date range.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not from_date or not to_date:
        from_date = frappe.utils.add_months(frappe.utils.today(), -1)
        to_date = frappe.utils.today()

    return _get_report(from_date, to_date)
