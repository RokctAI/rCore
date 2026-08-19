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


@frappe.whitelist()
def get_story(page: int=1, lang: str='en') -> Any:
    """
    Retrieves a list of stories grouped by shop for Flutter.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    stories = frappe.get_list(
        "Story",
        fields=[
            "name",
            "shop",
            "image",
            "title",
            "product",
            "creation",
            "modified",
        ],
        limit_start=(page - 1) * 10,
        limit=10,
    )

    grouped = {}
    for s in stories:
        shop_id = s.shop
        if not shop_id:
            continue

        if shop_id not in grouped:
            grouped[shop_id] = []

        shop_logo = frappe.db.get_value("Shop", shop_id, "logo")

        grouped[shop_id].append(
            {
                "shop_id": int(shop_id) if shop_id.isdigit() else shop_id,
                "logo_img": shop_logo,
                "title": s.title,
                "product_uuid": s.product,
                "product_title": (
                    frappe.db.get_value("Product", s.product, "product_name")
                    if s.product
                    else None
                ),
                "url": s.image,
                "created_at": s.creation.isoformat() if s.creation else None,
                "updated_at": s.modified.isoformat() if s.modified else None,
            }
        )

    return list(grouped.values())
