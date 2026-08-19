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


@frappe.whitelist(allow_guest=True)
def get_branches(shop_id: str) -> Any:
    """
    The get_branches function retrieves a list of branches associated with a specific shop. It takes one parameter, shop_id, which is a string representing the unique identifier of the shop. The function first checks if the provided shop_id exists in the database, throwing an error if it does not. If the shop exists, it queries the database for a list of branches linked to the shop, returning their names, addresses, and geographic coordinates.
    """
    """
    Retrieves a list of branches for a given shop.
    """
    if not frappe.db.exists("Company", shop_id):
        frappe.throw("Shop not found.")

    branches = frappe.get_list(
        "Branch",
        filters={"shop": shop_id},
        fields=["name", "address", "latitude", "longitude"],
    )
    return branches


@frappe.whitelist(allow_guest=True)
def get_branch(branch_id: str) -> Any:
    """
    Retrieves a single branch.
    """
    return frappe.get_doc("Branch", branch_id).as_dict()


@frappe.whitelist()
def create_branch(branch_data: Any) -> Any:
    """
    Creates a new branch.
    """
    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch = frappe.get_doc(
        {
            "doctype": "Branch",
            "branch_name": branch_data.get("name"),
            "address": branch_data.get("address"),
            "latitude": branch_data.get("latitude"),
            "longitude": branch_data.get("longitude"),
            "shop": branch_data.get("shop"),
            "owner": frappe.session.user,
        }
    )
    branch.insert(ignore_permissions=True)
    return branch.as_dict()


@frappe.whitelist()
def update_branch(branch_id: Any, branch_data: Any) -> Any:
    """
    Updates an existing branch.
    """
    if isinstance(branch_data, str):
        branch_data = json.loads(branch_data)

    branch = frappe.get_doc("Branch", branch_id)
    if (
        branch.owner != frappe.session.user
        and "System Manager" not in frappe.get_roles(frappe.session.user)
    ):
        frappe.throw(
            "You are not authorized to update this branch.",
            frappe.PermissionError,
        )

    branch.branch_name = branch_data.get("name", branch.branch_name)
    branch.address = branch_data.get("address", branch.address)
    branch.latitude = branch_data.get("latitude", branch.latitude)
    branch.longitude = branch_data.get("longitude", branch.longitude)
    branch.shop = branch_data.get("shop", branch.shop)
    branch.save(ignore_permissions=True)
    return branch.as_dict()


@frappe.whitelist()
def delete_branch(branch_id: Any) -> Any:
    """
    Deletes a branch.
    """
    branch = frappe.get_doc("Branch", branch_id)
    if (
        branch.owner != frappe.session.user
        and "System Manager" not in frappe.get_roles(frappe.session.user)
    ):
        frappe.throw(
            "You are not authorized to delete this branch.",
            frappe.PermissionError,
        )

    frappe.delete_doc("Branch", branch_id, ignore_permissions=True)
    return {"status": "success", "message": "Branch deleted successfully."}
