# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_status(session_id, api_key=None):
    client = JulesClient()
    return client.get_session(api_key, session_id)
