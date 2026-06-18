# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe


@frappe.whitelist()
def chat_with_rok(message: str, session_id: str = None, model: str = None) -> dict:
    """
    Secure gateway proxy for Next.js (Vercel) to chat with ROK agent on the Tenant VPS.
    Propagates X-Trace-Id across the distributed hops and emits structured logs to stderr.
    """
    import sys
    import time
    import datetime
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

    # Emit structured JSON log to stderr for host-level log collectors
    sys.stderr.write(
        json.dumps(
            {
                "event": "rok_tenant_chat_request_received",
                "trace_id": trace_id,
                "session_id": session_id,
                "user_id": user_id,
                "model": model,
                "message_len": len(message) if message else 0,
            }
        )
        + "\n"
    )
    sys.stderr.flush()

    try:
        # Check if ROK is enabled for this subscription tier
        from rcore.utils.subscription_checker import get_cached_subscription_details

        sub = get_cached_subscription_details()
        if sub.get("is_free_plan", 0) or not sub.get("is_ai", 0):
            # Enforce 5 free messages daily limit
            today_date = datetime.date.today().strftime("%Y-%m-%d")
            cache_key = f"free_rok_msg_count:{user_id}:{today_date}"
            current_count = frappe.cache().get_value(cache_key) or 0
            if current_count >= 5:
                sys.stderr.write(
                    json.dumps(
                        {
                            "event": "rok_tenant_chat_quota_exceeded",
                            "trace_id": trace_id,
                            "user_id": user_id,
                            "current_count": current_count,
                        }
                    )
                    + "\n"
                )
                sys.stderr.flush()
                frappe.throw(
                    "Quota Exceeded: Your daily free conversational ROK quota is complete! To make sure you don't lose any of the progress we've made, we are switching your Strategic Onboarding to Predefined (Offline) Mode. You can continue answering the remaining questions statically. To reactivate my smart auditing and reasoning right now, upgrade to a Pro plan!",
                    frappe.PermissionError,
                )
            frappe.cache().set_value(cache_key, current_count + 1, expires_in_sec=86400)

        # Secure seat assignment and license gatekeeping
        from rcore.tenant.api import get_token_usage

        usage_tracker = get_token_usage()
        if usage_tracker.get("seat_limit_exceeded"):
            sys.stderr.write(
                json.dumps(
                    {
                        "event": "rok_tenant_chat_seat_limit_reached",
                        "trace_id": trace_id,
                        "user_id": user_id,
                    }
                )
                + "\n"
            )
            sys.stderr.flush()
            frappe.throw(
                "Your team's ROK seat limit has been reached. Please contact your administrator to upgrade your subscription.",
                frappe.PermissionError,
            )

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

        payload = {
            "model": model or "hermes-agent",
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60.0)

        # Log intermediate failures with explicit details
        if response.status_code != 200:
            sys.stderr.write(
                json.dumps(
                    {
                        "event": "rok_tenant_completions_upstream_error",
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
            response_content = choices[0].get("message", {}).get("content", "")
            sys.stderr.write(
                json.dumps(
                    {
                        "event": "rok_tenant_chat_success",
                        "trace_id": trace_id,
                        "session_id": session_id,
                        "user_id": user_id,
                        "duration_sec": round(duration, 3),
                        "response_len": len(response_content),
                    }
                )
                + "\n"
            )
            sys.stderr.flush()

            return {
                "status": "success",
                "message": response_content,
                "tool_calls": choices[0].get("message", {}).get("tool_calls", None),
                "session_id": session_id,
                "trace_id": trace_id,
            }

        sys.stderr.write(
            json.dumps(
                {
                    "event": "rok_tenant_chat_empty_choices",
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
            "message": "No response choice returned from ROK.",
            "trace_id": trace_id,
        }

    except Exception as e:
        duration = time.time() - start_time
        import traceback

        sys.stderr.write(
            json.dumps(
                {
                    "event": "rok_tenant_chat_failed",
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
            title=f"ROK Tenant Chat Bridge failed [Trace: {trace_id}]",
            message=f"Trace ID: {trace_id}\nSession ID: {session_id}\nUser ID: {user_id}\nError: {e}\n\nTraceback:\n{traceback.format_exc()}",
        )
        return {"status": "error", "message": str(e), "trace_id": trace_id}
