# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""`agent.api.ask_assistant` — the real backend behind the assistant chat.

The Dart side (`agent_sdk`'s `AssistantService` -> `AgentRepository`) POSTs
`{question, subtopic_ref, student_id}` here and renders `response` in the
chat thread. The answer comes from a real LLM call (Gemini, the provider
`ai_config/models.json` and the bootstrap secrets handshake already
standardise on) — never from a canned string.

Honesty posture:
- No LLM credential configured => a clear "Assistant Not Configured" error
  through the normal frappe error path (the client surfaces it as an error,
  not as a chat answer).
- Provider call fails or returns nothing usable => "Assistant Unavailable"
  error, again through the normal error path.

Identity is server-authoritative: the acting student is `frappe.session.user`.
The client-sent `student_id` is accepted for wire compatibility but never
trusted for authorization.
"""

import json
import os

import frappe
import requests
from frappe import _

from rcore.agent.brain.assistant_rules import (
    DEFAULT_MODEL,
    PLAN_REFUSAL_MESSAGE,
    build_llm_payload,
    extract_response_text,
    governing_plan_flag,
    llm_endpoint,
    plan_allows_chat,
    success_response,
    validate_question,
)
from rcore.agent.services.llm_service import get_api_key

LLM_TIMEOUT_SECONDS = 60


def _configured_model():
    """Chat model id from ai_config/models.json (the models SSOT, FREE tier
    — fast/efficient, matching the chat use case), falling back to
    DEFAULT_MODEL when the file is missing or unreadable. `ai_config/` is a
    sibling of `brain/` both in src and in the composed app, so the relative
    path holds in both trees (the models.json-loading precedent in
    plan_builder/perform_bootstrap_secrets_handshake.py)."""
    models_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "ai_config", "models.json")
    )
    try:
        with open(models_file, "r", encoding="utf-8") as f:
            models_config = json.load(f)
        return models_config.get("FREE", {}).get("id") or DEFAULT_MODEL
    except Exception:
        return DEFAULT_MODEL


def _plan_allows_chat(user):
    """Whether [user]'s subscription plan includes the chat assistant,
    read from the lms module's records when they exist (LMS Billing Record
    -> LMS Plan `assistant_chat`, newest covering record first). FAIL-OPEN
    by decision: sites without the lms module, students without plan-linked
    billing records, and any lookup failure all allow — availability
    decisions default to not breaking paying students. Failures are logged
    for ops; the student never sees the diagnostic."""
    try:
        if not frappe.db.exists("DocType", "LMS Plan"):
            return True
        today = frappe.utils.getdate(frappe.utils.nowdate())
        rows = frappe.get_all(
            "LMS Billing Record",
            filters={"student": user},
            fields=["plan", "period_start", "period_end"],
            order_by="charged_at desc",
            limit_page_length=50,
        )
        records = []
        for row in rows:
            flag = (
                frappe.db.get_value("LMS Plan", row.plan, "assistant_chat")
                if row.plan
                else None
            )
            records.append(
                {
                    "assistant_chat": flag,
                    "period_start": frappe.utils.getdate(row.period_start)
                    if row.period_start
                    else None,
                    "period_end": frappe.utils.getdate(row.period_end)
                    if row.period_end
                    else None,
                }
            )
        return plan_allows_chat(governing_plan_flag(records, today))
    except Exception as e:
        frappe.log_error(
            f"ask_assistant plan gate lookup failed for {user}: {e}",
            "Assistant",
        )
        return True


@frappe.whitelist()
def ask_assistant(question=None, subtopic_ref=None, student_id=None):
    """Answers a student's chat question with a real LLM response.

    :param question: The student's question text (required, <= 4000 chars).
    :param subtopic_ref: Optional active lesson subtopic reference — scopes
        the system prompt to the lesson.
    :param student_id: Accepted for wire compatibility with the Dart client;
        identity is taken from the session, never from this field.
    :return: {"status": "success", "response": <text>, "intent": "question"}
    """
    try:
        question = validate_question(question)
    except ValueError as e:
        frappe.throw(_(str(e)), title=_("Invalid Question"))

    # Plan gate (owner's rule 2026-08-14): a plan that excludes the chat
    # assistant refuses with ONE friendly line; anything unresolvable
    # allows (fail-open — see _plan_allows_chat).
    if not _plan_allows_chat(frappe.session.user):
        frappe.throw(_(PLAN_REFUSAL_MESSAGE), title=_("Chat Unavailable"))

    # Credential lookup follows llm_service.get_api_key's documented priority:
    # Brain Settings (gemini_api_key) -> site_config.json (gemini_api_key) ->
    # environment (GEMINI_API_KEY). Missing credential fails honestly — no
    # canned fallback answer, ever.
    api_key = get_api_key("gemini")
    if not api_key:
        frappe.throw(
            _(
                "The assistant is not configured on this server: no Gemini "
                "API key found (Brain Settings / site_config.json "
                "`gemini_api_key`, or `GEMINI_API_KEY` in the environment). "
                "Please contact support."
            ),
            title=_("Assistant Not Configured"),
        )

    payload = build_llm_payload(question, subtopic_ref)
    try:
        response = requests.post(
            llm_endpoint(_configured_model()),
            json=payload,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        text = extract_response_text(response.json())
    except Exception as e:
        # Log the real cause for ops; the student gets an honest failure,
        # not a fabricated answer.
        frappe.log_error(f"ask_assistant LLM call failed: {e}", "Assistant")
        frappe.throw(
            _("The assistant is temporarily unavailable. Please try again."),
            title=_("Assistant Unavailable"),
        )

    return success_response(text)
