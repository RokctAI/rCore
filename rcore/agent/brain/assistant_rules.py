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

"""Pure assistant-chat rules for `agent.api.ask_assistant` — validation,
LLM request payload shaping, and LLM response parsing.

Deliberately frappe-free (the rlms `time_gates.py` / `homework_rules.py`
pattern): no `frappe` import and no app_name-templated imports, so the
logic is unit-testable standalone with stdlib `unittest`
(`tests/brain_tests/test_assistant_rules.py`) even though the surrounding
`brain` package only becomes importable after compose-time templating.

The frappe endpoint (`ask_assistant.py`) owns everything environmental:
session identity, credential lookup (`llm_service.get_api_key`), the HTTP
call, and error translation to `frappe.throw`.
"""

# Submission guardrail, mirroring the homework question cap.
MAX_QUESTION_CHARS = 4000

# Fallback model when ai_config/models.json is missing or unreadable.
# Chat uses the FREE tier entry (fast/efficient); models.json is the SSOT.
DEFAULT_MODEL = "gemini-2.5-flash"

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# The tutor persona contract: guide, don't hand over final answers wholesale,
# and stay anchored to the active lesson scope when one is provided.
SYSTEM_PROMPT = (
    "You are a friendly tutoring assistant inside a live-lesson learning app "
    "for school students. Answer the student's question clearly and "
    "age-appropriately. Guide the student toward understanding: explain the "
    "concept and the steps, and encourage them to attempt the final step "
    "themselves where that helps learning. If the question is unrelated to "
    "schoolwork, gently redirect the student back to the lesson. Keep "
    "answers concise enough to read in a chat bubble."
)


def validate_question(question):
    """Returns the stripped question text, or raises ValueError with a
    user-presentable reason. The endpoint converts the ValueError into the
    normal frappe error path."""
    if question is None or not isinstance(question, str) or not question.strip():
        raise ValueError("Question text is required.")
    question = question.strip()
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError(
            "Question is too long (limit %d characters)." % MAX_QUESTION_CHARS
        )
    return question


def system_instruction(subtopic_ref=None):
    """The system prompt, scoped to the active subtopic when the client
    sends one (the Dart service forwards its `subtopic_ref`)."""
    prompt = SYSTEM_PROMPT
    subtopic_ref = (subtopic_ref or "").strip()
    if subtopic_ref:
        prompt += (
            " The active lesson subtopic reference is: %s. Keep the answer "
            "anchored to that scope." % subtopic_ref
        )
    return prompt


def llm_endpoint(model):
    """Gemini generateContent URL for a model id (models.json `id` values)."""
    return "%s/%s:generateContent" % (GEMINI_BASE_URL, model or DEFAULT_MODEL)


def build_llm_payload(question, subtopic_ref=None):
    """Gemini generateContent request body for a validated question."""
    return {
        "system_instruction": {"parts": [{"text": system_instruction(subtopic_ref)}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
    }


def extract_response_text(response_json):
    """Pulls the answer text out of a Gemini generateContent response, or
    raises ValueError when the provider returned no usable text (empty
    candidates, safety block, malformed body). Never fabricates a fallback
    answer — the endpoint surfaces the failure honestly."""
    if not isinstance(response_json, dict):
        raise ValueError("LLM response was not a JSON object.")
    candidates = response_json.get("candidates") or []
    if not candidates:
        raise ValueError("LLM returned no candidates (possibly safety-blocked).")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(
        part.get("text", "") for part in parts if isinstance(part, dict)
    ).strip()
    if not text:
        raise ValueError("LLM returned an empty answer.")
    return text


def success_response(text):
    """The wire shape the Dart side pins (`AssistantQuestionResponse`)."""
    return {"status": "success", "response": text, "intent": "question"}


# Friendly refusal when the caller's plan excludes the chat assistant.
# One student-facing line only — diagnostic detail belongs in the server
# log, never in this message.
PLAN_REFUSAL_MESSAGE = "Chat isn't included in your plan."


def plan_allows_chat(flag):
    """The plan gate decision from a resolved `assistant_chat` plan value
    (the lms module's LMS Plan checkbox). FAIL-OPEN by decision: None —
    plan info unresolvable (no billing record, legacy record without a
    plan link, lms module absent) — allows, as does any unparseable
    value; only an explicit 0 disables. Availability decisions default to
    not breaking paying students."""
    if flag is None:
        return True
    try:
        return bool(int(flag))
    except (TypeError, ValueError):
        return True


def governing_plan_flag(records, today):
    """Pick the `assistant_chat` flag that governs [today] from a
    student's billing records (dicts with `assistant_chat`/`period_start`
    /`period_end` date values, NEWEST FIRST): the first record whose
    coverage includes today and that carries a resolvable flag wins.
    None when no record governs — plan_allows_chat then allows."""
    for record in records or []:
        start = record.get("period_start")
        end = record.get("period_end")
        if start and start > today:
            continue
        if end and end < today:
            continue
        if record.get("assistant_chat") is None:
            continue
        return record.get("assistant_chat")
    return None
