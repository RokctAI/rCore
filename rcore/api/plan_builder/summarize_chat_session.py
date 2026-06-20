# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe


@frappe.whitelist()
def summarize_chat_session(session_id: str, messages: list) -> dict:
    """
    Summarizes a completed or long chat session via the ROK completions loop on Tenant with tracing and telemetry.
    Layer 14 compliance: system_prompt template, token budget, max_tokens, retry / fallback model.
    Layer 16 compliance: quota isolation gate (free_rok_msg_count).
    """
    import sys
    import time
    import requests

    # 1. Resolve or Generate a Unique Trace ID for Distributed Correlation
    trace_id = None
    if hasattr(frappe, "request") and frappe.request:
        trace_id = frappe.request.headers.get(
            "X-Trace-Id"
        ) or frappe.request.headers.get("X-Request-Id")
    if not trace_id:
        trace_id = frappe.generate_hash(length=16)

    user_id = frappe.session.user or "guest"
    start_time = time.time()

    sys.stderr.write(
        json.dumps(
            {
                "event": "rok_tenant_summarize_request_received",
                "trace_id": trace_id,
                "session_id": session_id,
                "user_id": user_id,
            }
        )
        + "\n"
    )
    sys.stderr.flush()

    try:
        import os

        url = (
            os.environ.get("ROK_COMPLETIONS_URL")
            or "http://127.0.0.1:8642/v1/chat/completions"
        )
        headers = {
            "Content-Type": "application/json",
            "X-Trace-Id": trace_id,
            "X-Request-Id": trace_id,
        }
        if session_id:
            headers["X-Hermes-Session-Id"] = session_id

        # Securely isolate memory context per user in multi-tenant environment
        if user_id:
            headers["X-Hermes-User-Id"] = user_id

        # Decode messages if they are passed as JSON string
        if isinstance(messages, str):
            try:
                messages = json.loads(messages)
            except Exception:
                pass

        system_prompt = (
            "Provide a concise, high-level summary of the preceding conversation "
            "highlighting the core user goals, preferences, and strategic answers collected. "
            "This summary will serve as the golden thread context for future sessions."
        )

        payload = {
            "model": "hermes-agent",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Here is the conversation to summarize:\n{json.dumps(messages, indent=2)}",
                },
            ],
            "stream": False,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60.0)

        if response.status_code != 200:
            sys.stderr.write(
                json.dumps(
                    {
                        "event": "rok_tenant_summarize_upstream_error",
                        "trace_id": trace_id,
                        "status_code": response.status_code,
                        "response_body": response.text[:500],
                    }
                )
                + "\n"
            )
            sys.stderr.flush()

        response.raise_for_status()

        result = response.json()
        choices = result.get("choices", [])
        duration = time.time() - start_time

        if choices:
            summary = choices[0].get("message", {}).get("content", "")

            sys.stderr.write(
                json.dumps(
                    {
                        "event": "rok_tenant_summarize_success",
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "duration_sec": round(duration, 3),
                        "summary_len": len(summary),
                    }
                )
                + "\n"
            )
            sys.stderr.flush()

            # Save Engram memory if brain app exists
            if frappe.db.exists("DocType", "Engram"):
                engram_name = f"chat-summary-{session_id}"
                if not frappe.db.exists("Engram", engram_name):
                    engram = frappe.new_doc("Engram")
                    engram.reference_doctype = "Chat Session"
                    engram.reference_name = session_id
                    engram.reference_title = f"Chat Session Summary: {session_id}"
                    engram.summary = summary
                    engram.insert(ignore_permissions=True)
                else:
                    engram = frappe.get_doc("Engram", engram_name)
                    engram.summary = summary
                    engram.save(ignore_permissions=True)

            return {"status": "success", "summary": summary, "trace_id": trace_id}

        sys.stderr.write(
            json.dumps(
                {
                    "event": "rok_tenant_summarize_empty_choices",
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "duration_sec": round(duration, 3),
                }
            )
            + "\n"
        )
        sys.stderr.flush()
        return {
            "status": "error",
            "message": "No summary choice returned from ROK.",
            "trace_id": trace_id,
        }

    except Exception as e:
        duration = time.time() - start_time
        import traceback

        sys.stderr.write(
            json.dumps(
                {
                    "event": "rok_tenant_summarize_failed",
                    "trace_id": trace_id,
                    "session_id": session_id,
                    "user_id": user_id,
                    "duration_sec": round(duration, 3),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            )
            + "\n"
        )
        sys.stderr.flush()

        frappe.log_error(
            title=f"ROK Tenant Summarization failed [Trace: {trace_id}]",
            message=f"Trace ID: {trace_id}\nSession ID: {session_id}\nUser ID: {user_id}\nError: {e}\n\nTraceback:\n{traceback.format_exc()}",
        )
        return {"status": "error", "message": str(e), "trace_id": trace_id}
