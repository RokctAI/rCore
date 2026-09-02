# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from typing import Any

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import json
import os


@frappe.whitelist(allow_guest=True)
def get_version() -> Any:
    """
    Get version API endpoint. Reads the "rcore" key from versions.json
    (which lives alongside this file in the rcore package).
    """
    rcore_path = os.path.abspath(os.path.dirname(__file__))
    versions_file_path = os.path.join(rcore_path, "versions.json")

    try:
        with open(versions_file_path, "r") as f:
            versions = json.load(f)
        return versions.get("rcore", "0.1.0")  # Default fallback
    except Exception:
        return "0.1.0"  # Default fallback in case of any error
