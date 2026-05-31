import json
import frappe

@frappe.whitelist()
def chat_with_rok(message, session_id=None, model=None):
    """
    Secure gateway proxy for Next.js (Vercel) to chat with ROK agent on the Tenant VPS.
    """
    try:
        # Check if ROK is enabled for this subscription tier
        from rcore.utils.subscription_checker import get_cached_subscription_details
        sub = get_cached_subscription_details()
        if sub.get("is_free_plan", 0) or not sub.get("is_ai", 0):
            # Enforce 5 free messages daily limit
            user_id = frappe.session.user
            today_date = datetime.date.today().strftime("%Y-%m-%d")
            cache_key = f"free_rok_msg_count:{user_id}:{today_date}"
            current_count = frappe.cache().get_value(cache_key) or 0
            if current_count >= 5:
                frappe.throw(
                    "Quota Exceeded: Your daily free conversational ROK quota is complete! To make sure you don't lose any of the progress we've made, we are switching your Strategic Onboarding to Predefined (Offline) Mode. You can continue answering the remaining questions statically. To reactivate my smart auditing and reasoning right now, upgrade to a Pro plan!",
                    frappe.PermissionError
                )
            frappe.cache().set_value(cache_key, current_count + 1, expires_in_sec=86400)

        # Secure seat assignment and license gatekeeping
        from rcore.tenant.api import get_token_usage
        usage_tracker = get_token_usage()
        if usage_tracker.get("seat_limit_exceeded"):
            frappe.throw(
                "Your team's ROK seat limit has been reached. Please contact your administrator to upgrade your subscription.",
                frappe.PermissionError
            )
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

        payload = {
            "model": model or "hermes-agent",
            "messages": [
                {"role": "user", "content": message}
            ],
            "stream": False
        }

        import requests
        response = requests.post(url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        choices = result.get("choices", [])
        if choices:
            return {
                "status": "success",
                "message": choices[0].get("message", {}).get("content", ""),
                "tool_calls": choices[0].get("message", {}).get("tool_calls", None),
                "session_id": session_id
            }
        return {"status": "error", "message": "No response choice returned from ROK."}

    except Exception as e:
        frappe.log_error(f"ROK Tenant Chat Bridge failed: {e}")
        return {"status": "error", "message": str(e)}
