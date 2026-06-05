# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def start_jules_session(
    prompt: str,
    source_repo: str,
    api_key: str = None,
    automation_mode: str = "AUTO_CREATE_PR",
    require_approval: bool = False,
    title: str = None,
) -> dict:
    """
    Start a new Jules session with the given prompt and source repository.
    """
    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(
        f"Starting Jules session with prompt: {prompt[:50]}... if len(prompt) > 50 else prompt, source_repo: {source_repo}, api_key provided: {bool(api_key)}"
    )

    try:
        client = JulesClient()
        result = client.create_session(
            api_key, prompt, source_repo, automation_mode, require_approval, title
        )
        log_info("Successfully started Jules session")
        return result
    except Exception as e:
        log_error(f"Failed to start Jules session. Error: {str(e)}")
        raise
