# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_sources(api_key: str = None) -> dict:
    """
    Retrieve a list of Jules sources (data sources) associated with the provided API key.
    If no API key is provided, uses the default credentials configured in the system.
    """
    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Fetching Jules sources with api_key provided: {bool(api_key)}")

    try:
        client = JulesClient()
        result = client.get_sources(api_key)
        log_info("Successfully retrieved Jules sources")
        return result
    except Exception as e:
        log_error(f"Failed to retrieve Jules sources. Error: {str(e)}")
        raise
