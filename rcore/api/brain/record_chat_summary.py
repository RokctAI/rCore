import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def record_chat_summary(chat_transcript, reference_doctype=None, reference_name=None, modules=None):
    """
    Accepts a raw chat transcript, enqueues a background job to summarize it.
    """
    if not chat_transcript or not isinstance(chat_transcript, str) or not chat_transcript.strip():
        frappe.throw("`chat_transcript` must be a non-empty string.", title="Invalid Input")

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
        modules=modules
    )

    return {"status": "accepted", "message": "Chat summary job has been queued."}
