import json
import frappe

@frappe.whitelist()
def summarize_chat_session(session_id, messages):
    """
    Summarizes a completed or long chat session via the ROK completions loop on Tenant.
    """
    try:
        import os
        url = os.environ.get("ROK_COMPLETIONS_URL") or "http://127.0.0.1:8642/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if session_id:
            headers["X-Hermes-Session-Id"] = session_id

        # Securely isolate memory context per user in multi-tenant environment
        user_id = frappe.session.user
        if user_id:
            headers["X-Hermes-User-Id"] = user_id

        # Decode messages if they are passed as JSON string
        if isinstance(messages, str):
            try:
                import json
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
                {"role": "user", "content": f"Here is the conversation to summarize:\n{json.dumps(messages, indent=2)}"}
            ],
            "stream": False
        }

        import requests
        response = requests.post(url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        choices = result.get("choices", [])
        if choices:
            summary = choices[0].get("message", {}).get("content", "")
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

            return {
                "status": "success",
                "summary": summary
            }
        return {"status": "error", "message": "No summary choice returned from ROK."}

    except Exception as e:
        frappe.log_error(f"ROK Summarization failed: {e}")
        return {"status": "error", "message": str(e)}
