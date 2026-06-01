import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def vote_on_plan(session_id: str, action: str, api_key: str = None) -> dict:
    """
    Register a vote (approval) for a plan via the Jules service.
    This function contacts the Jules API to approve a plan given a session ID and optional API key.
    """
    trace_id = str(uuid.uuid4())
    
    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)
    
    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Received vote_on_plan request for session_id: {session_id}, action: {action}")
    
    if action != "approve":
        log_error("Only 'approve' action is currently supported.")
        frappe.throw("Only 'approve' action is currently supported.")
    
    try:
        client = JulesClient()
        result = client.approve_plan(api_key, session_id)
        log_info(f"Successfully voted on plan for session_id: {session_id}")
        return result
    except Exception as e:
        log_error(f"Failed to vote on plan for session_id: {session_id}. Error: {str(e)}")
        raise