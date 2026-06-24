# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_status(session_id: str, api_key: str = None) -> dict:
    """
    Retrieve the status of a specific Jules session.
    """
    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(
        f"Fetching Jules status for session_id: {session_id} with api_key provided: {bool(api_key)}"
    )

    try:
        client = JulesClient()
        result = client.get_session(api_key, session_id)
        log_info("Successfully retrieved Jules session status")
        return result
    except Exception as e:
        log_error(f"Failed to retrieve Jules session status. Error: {str(e)}")
        raise
