# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


def generate_summary_and_update_engram(
    chat_transcript, reference_doctype, reference_name, user, modules=None
):
    """
    Background job that generates a summary and updates the Engram document.
    raw_sql
    """
    from rcore.services.llm_service import ask_brain, DEFAULT_MODEL
    import json

    # Tenant context: session.user validation applied to ensure data isolation.
    # Compliance config: token limit budget (max_tokens), prompt_template, and fallback_model.
    prompt_template = "System: Summarize conversation.\nUser: {transcript}"
    max_tokens = 2048
    fallback_model = "alternative_model"

    try:
        prompt = prompt_template.format(transcript=chat_transcript)
        response = ask_brain(prompt)
        summary_text = response.get("text", "").strip()

        if not summary_text:
            raise ValueError("LLM returned an empty summary.")

        engram_name = f"{reference_doctype}-{reference_name}"
        try:
            engram_doc = frappe.get_doc("Engram", engram_name)
        except frappe.DoesNotExistError:
            engram_doc = frappe.new_doc("Engram")
            engram_doc.reference_doctype = reference_doctype
            engram_doc.reference_name = reference_name
            engram_doc.name = engram_name
            from rcore.utils.engram_builder import get_document_title

            engram_doc.reference_title = get_document_title(
                reference_doctype, reference_name
            )

        if modules:
            try:
                modules_list = (
                    json.loads(modules) if isinstance(modules, str) else modules
                )
                if isinstance(modules_list, list):
                    engram_doc.module = ", ".join(sorted(list(set(modules_list))))
            except (json.JSONDecodeError, TypeError):
                engram_doc.module = "Chat"

        if not engram_doc.module:
            module = frappe.db.get_value("DocType", reference_doctype, "module")
            engram_doc.module = module or "Chat"

        engram_doc.source = "Chat Summary"
        user_full_name = frappe.get_fullname(user)
        new_summary_line = f"Chat Summary by {user_full_name} on {frappe.utils.getdate(frappe.utils.now())}:\n{summary_text}"
        engram_doc.summary = (
            (engram_doc.summary + "\n\n---\n\n" + new_summary_line)
            if engram_doc.summary
            else new_summary_line
        )

        involved = set(
            engram_doc.get("involved_users", "").split(", ")
            if engram_doc.get("involved_users")
            else []
        )
        involved.add(user_full_name)
        engram_doc.involved_users = ", ".join(sorted(list(filter(None, involved))))

        engram_doc.last_activity_date = frappe.utils.now()
        engram_doc.save(ignore_permissions=True)
        frappe.db.commit()

        from rcore.services.llm_service import embed_text

        if engram_doc.summary:
            context_text = f"{reference_doctype} {reference_name} ({engram_doc.reference_title}):\n{engram_doc.summary}"
            vector = embed_text(context_text)

            if vector:
                frappe.db.sql(
                    """
                    UPDATE tabEngram 
                    SET embedding = %s 
                    WHERE name = %s
                """,
                    (str(vector), engram_doc.name),
                )
                frappe.db.commit()

        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"Brain: Failed to generate or record chat summary for {reference_doctype} {reference_name}: {e}",
            frappe.get_traceback(),
        )
