# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def start_jules_session(
    prompt,
    source_repo,
    api_key=None,
    automation_mode="AUTO_CREATE_PR",
    require_approval=False,
    title=None,
):
    client = JulesClient()
    return client.create_session(
        api_key, prompt, source_repo, automation_mode, require_approval, title
    )
