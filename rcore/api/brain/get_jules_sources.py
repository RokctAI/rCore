import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def get_jules_sources(api_key=None):
    client = JulesClient()
    return client.get_sources(api_key)
