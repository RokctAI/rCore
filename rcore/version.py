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
    versions_file_path = os.path.join(rcore_path, 'versions.json')

    try:
        with open(versions_file_path, 'r') as f:
            versions = json.load(f)
        return versions.get('rcore', '0.1.0')  # Default fallback
    except Exception:
        return '0.1.0'  # Default fallback in case of any error
