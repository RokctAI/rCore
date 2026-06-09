# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def send_jules_message(session_id: str, message: str, api_key: str = None) -> dict:
    """
    Send a message to a Jules session.
    """
    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(
        f"Sending message to Jules session_id: {session_id} with api_key provided: {bool(api_key)}"
    )

    try:
        client = JulesClient()
        result = client.send_message(api_key, session_id, message)
        log_info("Successfully sent message to Jules session")
        return result
    except Exception as e:
        log_error(f"Failed to send message to Jules session. Error: {str(e)}")
        raise
