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


@frappe.whitelist(allow_guest=True)
def check_coupon(code: str, shop_id: str, qty: int=1) -> Any:
    """
    Checks if a coupon is valid for a given shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if not code or not shop_id:
        frappe.throw("Code and shop ID are required.")

    coupon = frappe.db.get_value(
        "Coupon",
        filters={"code": code, "shop": shop_id},
        fieldname=["name", "expired_at", "quantity"],
        as_dict=True,
    )

    if not coupon:
        return {"status": "error", "message": "Invalid Coupon"}

    if (
        coupon.get("expired_at")
        and coupon.get("expired_at") < frappe.utils.now_datetime()
    ):
        return {"status": "error", "message": "Coupon expired"}

    if coupon.get("quantity") is not None and coupon.get("quantity") < qty:
        return {"status": "error", "message": "Coupon has been fully used"}

    # Check if the user has already used this coupon
    if frappe.session.user != "Guest" and frappe.db.exists(
        "Coupon Usage", {"user": frappe.session.user, "coupon": coupon.name}
    ):
        return {
            "status": "error",
            "message": "You have already used this coupon.",
        }

    return frappe.get_doc("Coupon", coupon.name).as_dict()
