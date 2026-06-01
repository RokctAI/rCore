import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_sessions(api_key: str = None) -> dict:
    """
    Retrieve a list of Jules sessions associated with the provided API key.
    If no API key is provided, uses the default credentials configured in the system.
    """
    trace_id = str(uuid.uuid4())
    
    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)
    
    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Fetching Jules sessions with api_key provided: {bool(api_key)}")
    
    try:
        client = JulesClient()
        result = client.get_sessions(api_key)
        log_info("Successfully retrieved Jules sessions")
        return result
    except Exception as e:
        log_error(f"Failed to retrieve Jules sessions. Error: {str(e)}")
        raise