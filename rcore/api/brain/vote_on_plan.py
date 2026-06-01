# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def vote_on_plan(session_id, action, api_key=None):
    if action != "approve":
        frappe.throw("Only 'approve' action is currently supported.")
    client = JulesClient()
    return client.approve_plan(api_key, session_id)
