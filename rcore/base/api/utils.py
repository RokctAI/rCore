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

import frappe
import math
import json


def _require_admin():
    """Helper function to ensure the user has the System Manager role."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw(
            "You are not authorized to perform this action.",
            frappe.PermissionError,
        )


def _get_seller_shop(user_id):
    """Helper function to get the shop for a given user."""
    if not user_id or user_id == "Guest":
        frappe.throw(
            "You must be logged in to perform this action.",
            frappe.AuthenticationError,
        )

    # Assuming 'user' is the field on the Shop doctype linking to the User
    shop = frappe.db.get_value("Shop", {"user": user_id}, "name")
    if not shop:
        frappe.throw("User is not linked to any shop.", frappe.PermissionError)

    return shop


def api_response(data=None, message=None, status_code=200):
    """
    Standard API response wrapper.
    """
    response = {}
    if data is not None:
        response["data"] = data
    if message:
        response["message"] = message
    if status_code:
        response["status_code"] = status_code

    return response


def haversine(lat1, lon1, lat2, lon2):
    """
    Calculates the great-circle distance between two points on Earth (in km).
    """
    R = 6371  # Earth radius in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(
        math.radians(lat1)
    ) * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
