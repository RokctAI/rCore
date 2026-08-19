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

"""Async anytime homework help — backend endpoints (product log #42 item 1:
ship #4's send-and-wait design plus #1's guide-don't-solve homework tool).

Send-and-wait (#4): a student submits a question anytime and gets the
response later — no live chat infrastructure. The student side is the
whitelisted submit/list/get/answer quartet; the fulfilment side is
System-Manager-gated (fetch pending, AI-draft an MCQ for operator review,
publish MCQ or decline), the same split as skills.py's read/publish and
admin.py's review endpoints.

Guide-don't-solve (#1, RESOLVED): the fulfilment side computes the real
answer internally and publishes the student's own question as a
multiple-choice set (correct answer + plausible wrong answers based on
common mistakes). The student must pick before anything is revealed:
student-facing reads NEVER include correct_index or explanation until an
attempt is recorded — answer_homework_mcq records the attempt and only
then returns the confirmation/correction ("wrong, B is correct").
Essay/written-argument questions are declined with a reason rather than
force-fitted into an MCQ.

All judgement lives in ../homework_rules.py (frappe-free, unit-tested
standalone — the time_gates.py pattern); this file owns the I/O only.
The doctype grants no student role permissions: every student path goes
through these endpoints with explicit member == session-user ownership
checks, so the raw document (with the answer inside) is never readable
via the generic resource API. Server is sole authority.
"""

import json

import frappe
from frappe import _

from .. import homework_draft_rules, homework_rules

DOCTYPE = "LMS Homework Question"

# The list/detail field set for student reads. mcq_json deliberately
# absent — it is loaded and stripped per-status by _student_view.
_STUDENT_FIELDS = [
    "name",
    "subject",
    "grade",
    "question_text",
    "attachment_refs",
    "status",
    "submitted_at",
    "decline_reason",
    "answered_index",
    "answer_outcome",
    "answered_at",
]


def _own_doc(name):
    """Loads one homework question, enforcing member == session user.

    Raises DoesNotExistError for both "missing" and "someone else's" — a
    student probing other ids learns nothing about whether they exist.
    """
    doc = frappe.db.get_value(
        DOCTYPE, name, _STUDENT_FIELDS + ["member", "mcq_json"], as_dict=True
    )
    if not doc or doc.member != frappe.session.user:
        frappe.throw(_("Homework question not found."), frappe.DoesNotExistError)
    return doc


def _mcq(doc):
    """The stored MCQ payload, parsed; None when absent/malformed."""
    raw = doc.get("mcq_json")
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        frappe.log_error(frappe.get_traceback(), "Malformed homework MCQ JSON")
        return None
    return parsed if isinstance(parsed, dict) else None


def _student_view(doc):
    """The one shape a student read returns. Before an attempt (Ready) the
    MCQ carries question + options ONLY; after the attempt (Completed) the
    reveal fields ride along — the attempt is already recorded."""
    out = {k: doc.get(k) for k in _STUDENT_FIELDS if k != "name"}
    out["id"] = doc.get("name")
    out["submitted_at"] = str(doc.get("submitted_at") or "") or None
    out["answered_at"] = str(doc.get("answered_at") or "") or None
    # The student's own photo refs, as a list — the raw stored JSON string
    # is an implementation detail, so it never leaves this function.
    out["attachments"] = homework_rules.parse_attachment_refs(
        out.pop("attachment_refs", None)
    )
    mcq = _mcq(doc)
    if mcq and doc.get("status") == homework_rules.STATUS_READY:
        out["mcq"] = homework_rules.student_mcq_view(mcq)
    elif mcq and doc.get("status") == homework_rules.STATUS_COMPLETED:
        out["mcq"] = homework_rules.student_mcq_view(mcq)
        answered = doc.get("answered_index")
        if answered is not None:
            out["reveal"] = homework_rules.check_answer(mcq, int(answered))
    return out


@frappe.whitelist()
def submit_homework_question(question_text, subject=None, grade=None, attachments=None):
    """Student submit (#4's send half): validates and queues the question,
    returning its id + status. The response comes later — send-and-wait."""
    try:
        text = homework_rules.validate_submission(question_text)
        attachment_list = homework_rules.validate_attachments(attachments)
    except ValueError as e:
        frappe.throw(_(str(e)))

    doc = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "member": frappe.session.user,
            "subject": (subject or "").strip() or None,
            "grade": int(grade) if grade not in (None, "") else None,
            "question_text": text,
            "attachment_refs": json.dumps(attachment_list) if attachment_list else None,
            "status": homework_rules.STATUS_SUBMITTED,
            "submitted_at": frappe.utils.now_datetime(),
        }
    )
    doc.insert(ignore_permissions=True)
    return {"id": doc.name, "status": doc.status}


@frappe.whitelist()
def list_homework_questions():
    """The student's own questions, newest first. Catch-and-degrade to an
    empty list (the skills.py student-read posture): a backend hiccup shows
    an empty inbox, never an error page."""
    try:
        rows = frappe.get_all(
            DOCTYPE,
            filters={"member": frappe.session.user},
            fields=_STUDENT_FIELDS + ["mcq_json"],
            order_by="submitted_at desc, creation desc",
        )
        return [_student_view(row) for row in rows]
    except Exception:
        frappe.log_error(frappe.get_traceback(), "list_homework_questions failed")
        return []


@frappe.whitelist()
def get_homework_question(name):
    """One of the student's own questions. When Ready, the MCQ arrives
    WITHOUT correct_index/explanation — the reveal only ever comes back
    from answer_homework_mcq, after the attempt is recorded."""
    return _student_view(_own_doc(name))


@frappe.whitelist()
def answer_homework_mcq(name, selected_index):
    """Records the student's attempt, THEN returns the reveal — correct or
    not, which option was right, and the explanation ("wrong, B is
    correct"). One attempt per question: the attempt moves the question to
    Completed, and Completed accepts no further answers."""
    doc = _own_doc(name)
    if doc.status != homework_rules.STATUS_READY:
        frappe.throw(_("This question is not ready to answer (status: {0}).").format(doc.status))
    mcq = _mcq(doc)
    if not mcq:
        frappe.throw(_("This question has no answer set yet."))

    try:
        selected = int(selected_index)
        reveal = homework_rules.check_answer(mcq, selected)
    except (TypeError, ValueError) as e:
        frappe.throw(_(str(e)))

    # Record the attempt FIRST — the reveal below exists because this row
    # now does (guide-don't-solve's ordering, enforced structurally).
    frappe.db.set_value(
        DOCTYPE,
        doc.name,
        {
            "answered_index": selected,
            "answer_outcome": "Correct" if reveal["correct"] else "Incorrect",
            "answered_at": frappe.utils.now_datetime(),
            "status": homework_rules.STATUS_COMPLETED,
        },
    )
    return reveal


@frappe.whitelist()
def homework_pending_requests():
    """Fulfilment side: questions awaiting an MCQ set or a decline
    (Submitted/In Review), oldest first. System Manager only — this is the
    only read that exposes raw questions across students."""
    frappe.only_for("System Manager")
    return frappe.get_all(
        DOCTYPE,
        filters={"status": ["in", list(homework_rules.PENDING_STATUSES)]},
        fields=[
            "name",
            "member",
            "subject",
            "grade",
            "question_text",
            "attachment_refs",
            "status",
            "submitted_at",
        ],
        order_by="submitted_at asc, creation asc",
    )


def _fulfilment_doc(name):
    doc = frappe.db.get_value(DOCTYPE, name, ["name", "status"], as_dict=True)
    if not doc:
        frappe.throw(_("Homework question not found."), frappe.DoesNotExistError)
    return doc


def _ai_draft_provider():
    """The assistant chat's provider path, late-bound from the agent module
    (the plan-gate posture mirrored: cross-module coupling is resolved at
    call time and failure degrades to a clear answer, never a crash at
    import). Returns (get_api_key, endpoint_url, extract_response_text,
    timeout_seconds) or None when the agent module isn't installed."""
    try:
        from rcore.agent.brain import ask_assistant as assistant_chat
        from rcore.agent.brain.assistant_rules import (
            extract_response_text,
            llm_endpoint,
        )
        from rcore.agent.services.llm_service import get_api_key
    except ImportError:
        return None
    return (
        get_api_key,
        llm_endpoint(assistant_chat._configured_model()),
        extract_response_text,
        assistant_chat.LLM_TIMEOUT_SECONDS,
    )


@frappe.whitelist()
def draft_homework_mcq(name):
    """Fulfilment side: asks AI to DRAFT the guided MCQ set for one pending
    question, for the operator to edit and approve. System Manager only.

    Returns the draft only — this endpoint never publishes and never
    touches the document; publish_homework_mcq (a human action) remains
    the only way anything reaches the student. Reuses the assistant chat's
    provider path end to end: same credential chain (llm_service
    .get_api_key), same configured model, same response parsing. Honesty
    posture: not configured (agent module absent or no key) or provider
    failure => a clear error with the detail in the server log — never a
    fabricated draft."""
    frappe.only_for("System Manager")
    doc = frappe.db.get_value(
        DOCTYPE,
        name,
        ["name", "status", "subject", "grade", "question_text"],
        as_dict=True,
    )
    if not doc:
        frappe.throw(_("Homework question not found."), frappe.DoesNotExistError)
    if not homework_rules.can_transition(doc.status, homework_rules.STATUS_READY):
        frappe.throw(_("Cannot draft an answer set from status {0}.").format(doc.status))

    provider = _ai_draft_provider()
    if provider is None:
        frappe.log_error(
            "draft_homework_mcq: agent module not importable on this site",
            "Homework AI draft",
        )
        frappe.throw(_("AI drafting isn't configured yet."))
    get_api_key, endpoint_url, extract_response_text, timeout_seconds = provider

    api_key = get_api_key("gemini")
    if not api_key:
        frappe.log_error(
            "draft_homework_mcq: no provider API key via Brain Settings / "
            "site_config.json / environment",
            "Homework AI draft",
        )
        frappe.throw(_("AI drafting isn't configured yet."))

    import requests

    payload = homework_draft_rules.build_draft_request(
        doc.question_text, doc.subject, doc.grade
    )
    try:
        response = requests.post(
            endpoint_url,
            json=payload,
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        text = extract_response_text(response.json())
        draft = homework_rules.validate_mcq_payload(
            homework_draft_rules.parse_draft_response(text)
        )
    except Exception as e:
        frappe.log_error(f"draft_homework_mcq failed for {doc.name}: {e}", "Homework AI draft")
        frappe.throw(
            _("The AI draft didn't come through. Try again, or write the answer set yourself.")
        )
    return {"id": doc.name, "mcq": draft}


@frappe.whitelist()
def publish_homework_mcq(name, mcq_json):
    """Fulfilment side: publishes the guided MCQ set for one question and
    moves it to Ready. System Manager only. The payload is validated
    structurally (homework_rules.validate_mcq_payload); pedagogy — real
    answer computed internally, wrong options modelled on common mistakes —
    is the caller's contract per product log #1."""
    frappe.only_for("System Manager")
    doc = _fulfilment_doc(name)
    if not homework_rules.can_transition(doc.status, homework_rules.STATUS_READY):
        frappe.throw(_("Cannot publish an answer set from status {0}.").format(doc.status))

    if isinstance(mcq_json, str):
        try:
            mcq_json = json.loads(mcq_json)
        except (TypeError, ValueError):
            frappe.throw(_("mcq_json must be valid JSON."))
    try:
        mcq = homework_rules.validate_mcq_payload(mcq_json)
    except ValueError as e:
        frappe.throw(_(str(e)))

    frappe.db.set_value(
        DOCTYPE,
        doc.name,
        {"mcq_json": json.dumps(mcq), "status": homework_rules.STATUS_READY},
    )
    return {"id": doc.name, "status": homework_rules.STATUS_READY}


@frappe.whitelist()
def decline_homework_question(name, reason):
    """Fulfilment side: declines a question that doesn't reduce to an
    objective MCQ (#1's essay/written-argument boundary), with a reason the
    student sees. System Manager only."""
    frappe.only_for("System Manager")
    doc = _fulfilment_doc(name)
    if not homework_rules.can_transition(doc.status, homework_rules.STATUS_DECLINED):
        frappe.throw(_("Cannot decline from status {0}.").format(doc.status))
    try:
        text = homework_rules.validate_decline(reason)
    except ValueError as e:
        frappe.throw(_(str(e)))

    frappe.db.set_value(
        DOCTYPE,
        doc.name,
        {"decline_reason": text, "status": homework_rules.STATUS_DECLINED},
    )
    return {"id": doc.name, "status": homework_rules.STATUS_DECLINED}
