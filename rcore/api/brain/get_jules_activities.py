import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_activities(session_id: str, api_key: str = None) -> dict:
    """
    Retrieve a list of Jules activities for a given session.
    If session_id is not provided, returns activities for all sessions associated with the API key.
    """
    trace_id = str(uuid.uuid4())
    
    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)
    
    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Fetching Jules activities for session_id: {session_id} with api_key provided: {bool(api_key)}")
    
    try:
        client = JulesClient()
        result = client.get_activities(api_key, session_id)
        log_info("Successfully retrieved Jules activities")
        return result
    except Exception as e:
        log_error(f"Failed to retrieve Jules activities. Error: {str(e)}")
        raise