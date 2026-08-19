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


def _require_admin():
    """Helper function to ensure the user has the System Manager role."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to perform this action.",
            frappe.PermissionError,
        )


@frappe.whitelist(allow_guest=True)
def get_page(route: str) -> Any:
    """
    Retrieves a single web page by its route.
    """
    page = frappe.get_doc("Web Page", {"route": route})
    if not page.published:
        frappe.throw("Page not published.", frappe.PermissionError)

    # The original response has a nested translation object.
    # We will simulate this structure.
    return {
        "id": page.name,
        "type": page.route,
        "img": page.image,
        "active": page.published,
        "translation": {
            "title": page.title,
            "description": page.main_section,
        },
    }


@frappe.whitelist()
def get_admin_pages(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all web pages on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Web Page",
        fields=["name", "title", "route", "published"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def get_admin_web_page(route: str) -> Any:
    """
    Retrieves a web page for admin management.
    """
    _require_admin()
    return frappe.get_doc("Web Page", {"route": route}).as_dict()


@frappe.whitelist()
def update_admin_web_page(route: str, page_data: Any) -> Any:
    """
    Updates a web page (for admins).
    """
    _require_admin()
    if isinstance(page_data, str):
        page_data = json.loads(page_data)

    page = frappe.get_doc("Web Page", {"route": route})
    page.update(page_data)
    page.save(ignore_permissions=True)
    return page.as_dict()
