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
def get_careers(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of active careers, formatted for frontend compatibility.
    """
    careers = frappe.get_list(
        "Career",
        filters={"is_active": 1},
        fields=["name", "title", "description", "location", "category"],
        offset=limit_start,
        limit=limit_page_length,
    )

    formatted_careers = []
    for career in careers:
        # The original response has a nested translation object.
        # We will simulate this structure.
        formatted_careers.append(
            {
                "id": career.name,
                "location": career.location,
                "active": True,
                "category": {"name": career.category},
                "translation": {
                    "title": career.title,
                    "description": career.description,
                },
            }
        )

    return formatted_careers


@frappe.whitelist(allow_guest=True)
def get_career(id: str) -> Any:
    """
    Retrieves a single career by its ID (name).
    """
    career = frappe.get_doc("Career", id)
    if not career.is_active:
        frappe.throw("Career not active.", frappe.PermissionError)

    return {
        "id": career.name,
        "location": career.location,
        "active": True,
        "category": {"name": career.category},
        "translation": {
            "title": career.title,
            "description": career.description,
        },
    }


@frappe.whitelist()
def get_admin_careers(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all careers on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Career",
        fields=["name", "title", "location", "category", "is_active"],
        offset=limit_start,
        limit=limit_page_length,
    )
