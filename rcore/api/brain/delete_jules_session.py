import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def delete_jules_session(session_id, api_key=None):
    client = JulesClient()
    return client.delete_session(api_key, session_id)
