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
from frappe.utils import now_datetime
from ..utils import api_response


@frappe.whitelist()
def create_blog(data: Any) -> Any:
    """
    Creates a new Blog post.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc({"doctype": "Blog", **data})
    doc.insert()
    return api_response(
        data=doc.as_dict(), message="Blog created successfully."
    )


@frappe.whitelist(allow_guest=True)
def get_blogs(type: Any=None, limit: Any=10, start: Any=0) -> Any:
    """
    Retrieves Blogs, optionally filtered by type.
    """
    filters = {"active": 1, "published_at": ["<=", now_datetime()]}
    if type:
        filters["type"] = type

    runs = frappe.get_list(
        "Blog",
        filters=filters,
        fields=[
            "name",
            "title",
            "short_description",
            "img",
            "published_at",
            "author",
            "type",
        ],
        order_by="published_at desc",
        offset=start,
        limit=limit,
    )
    return api_response(data=runs)


@frappe.whitelist(allow_guest=True)
def get_blog_details(name: Any) -> Any:
    """
    Retrieves full details of a Blog post.
    """
    return api_response(data=frappe.get_doc("Blog", name).as_dict())


@frappe.whitelist()
def update_blog(name: Any, data: Any) -> Any:
    """
    Updates a Blog post.
    """
    if isinstance(data, str):
        data = json.loads(data)

    doc = frappe.get_doc("Blog", name)
    doc.update(data)
    doc.save()
    return api_response(
        data=doc.as_dict(), message="Blog updated successfully."
    )


@frappe.whitelist()
def delete_blog(name: Any) -> Any:
    """
    Deletes a Blog post.
    """
    frappe.delete_doc("Blog", name)
    return api_response(message="Blog deleted successfully.")


@frappe.whitelist()
def get_admin_blogs(page: int=1, limit: int=10, lang: str='en') -> Any:
    """
    Retrieves all Blogs for Admin (including inactive).
    """
    blogs = frappe.get_list(
        "Blog",
        fields=[
            "name",
            "title",
            "short_description",
            "img",
            "published_at",
            "author",
            "type",
            "active",
        ],
        order_by="creation desc",
        offset=(page - 1) * limit,
        limit=limit,
    )
    return api_response(data=blogs)


# --- Admin Aliases ---
@frappe.whitelist()
def create_admin_blog(data: Any) -> Any:
    """
    Alias for create_blog (Admin usage).
    """
    return create_blog(data)


@frappe.whitelist()
def update_admin_blog(name: Any, data: Any) -> Any:
    """
    Alias for update_blog (Admin usage).
    """
    return update_blog(name, data)


@frappe.whitelist()
def delete_admin_blog(name: Any) -> Any:
    """
    Alias for delete_blog (Admin usage).
    """
    return delete_blog(name)


@frappe.whitelist(allow_guest=True)
def get_blog(name: Any) -> Any:
    """
    Alias for get_blog_details.
    """
    return get_blog_details(name)
