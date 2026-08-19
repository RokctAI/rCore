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
from rcore.base.api.utils import _get_seller_shop


@frappe.whitelist()
def get_seller_stories(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of stories for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    stories = frappe.get_list(
        "Story",
        filters={"shop": shop},
        fields=["name", "title", "image", "expires_at"],
        offset=limit_start,
        limit=limit_page_length,
        order_by="creation desc",
    )
    return stories


@frappe.whitelist()
def create_seller_story(story_data: Any) -> Any:
    """
    Creates a new story for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(story_data, str):
        story_data = json.loads(story_data)

    story_data["shop"] = shop

    new_story = frappe.get_doc({"doctype": "Story", **story_data})
    new_story.insert(ignore_permissions=True)
    return new_story.as_dict()


@frappe.whitelist()
def update_seller_story(story_name: Any, story_data: Any) -> Any:
    """
    Updates a story for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    if isinstance(story_data, str):
        story_data = json.loads(story_data)

    story = frappe.get_doc("Story", story_name)

    if story.shop != shop:
        frappe.throw(
            "You are not authorized to update this story.",
            frappe.PermissionError,
        )

    story.update(story_data)
    story.save(ignore_permissions=True)
    return story.as_dict()


@frappe.whitelist()
def delete_seller_story(story_name: Any) -> Any:
    """
    Deletes a story for the current seller's shop.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    user = frappe.session.user
    shop = _get_seller_shop(user)

    story = frappe.get_doc("Story", story_name)

    if story.shop != shop:
        frappe.throw(
            "You are not authorized to delete this story.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Story", story_name, ignore_permissions=True)
    return {"status": "success", "message": "Story deleted successfully."}
