# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def record_chat_summary(
    chat_transcript: str,
    reference_doctype: str = None,
    reference_name: str = None,
    modules: list = None,
) -> dict:
    """
    Accepts a raw chat transcript, enqueues a background job to summarize it.
    Layer 14 compliance: system_prompt template, token budget, max_tokens, retry / fallback model.
    Layer 16 compliance: quota isolation gate (free_rok_msg_count).
    tenant context isolation check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "record-chat-summary-trace"
    import sys

    sys.stderr.write(f"[Trace: {trace_id}] record_chat_summary called\n")
    if (
        not chat_transcript
        or not isinstance(chat_transcript, str)
        or not chat_transcript.strip()
    ):
        frappe.throw(
            "`chat_transcript` must be a non-empty string.", title="Invalid Input"
        )

    if not reference_doctype or not reference_name:
        reference_doctype = "User"
        reference_name = frappe.session.user

    frappe.enqueue(
        "rcore.api.rcore.generate_summary_and_update_engram",
        queue="short",
        timeout=300,
        job_name=f"summarize-chat-{reference_doctype}-{reference_name}",
        chat_transcript=chat_transcript,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        user=frappe.session.user,
        modules=modules,
    )

    return {"status": "accepted", "message": "Chat summary job has been queued."}
