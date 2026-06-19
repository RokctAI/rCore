# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def delete_jules_session(session_id: str, api_key: str = None) -> dict:
    """
    Delete a Jules session.
    """
    trace_id = frappe.form_dict.get("trace_id") or "delete-jules-session-trace"
    import sys

    sys.stderr.write(
        f"[Trace: {trace_id}] delete_jules_session called for {session_id}\n"
    )
    client = JulesClient()
    return client.delete_session(api_key, session_id)
