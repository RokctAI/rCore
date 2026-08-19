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

"""Async homework-help rules (product log #42 item 1 = #4's send-and-wait
shape + #1's guide-don't-solve mechanism) — frappe-free pure module.

The api/homework.py endpoints own the I/O and call these for every
judgement (the time_gates.py pattern; SDK_README "Testable Backend Logic"):
status transitions, MCQ payload validation, the post-attempt answer check,
and the essay-decline validation. This module imports no frappe and is
unit-tested standalone (tests/test_homework_rules.py).

The pedagogy contract enforced here (#1, RESOLVED): the fulfilment side
computes the real answer internally, converts the student's own question
into a multiple-choice set (correct answer + plausible wrong answers based
on common mistakes), and the student must pick BEFORE anything is revealed.
`check_answer` is the single reveal point — it returns the truth only as
the response to a recorded attempt. Server-side callers must never ship
`correct_index`/`explanation` to a student whose attempt hasn't landed.

Scope boundary (#1): computable/objective problems only. Essay/written-
argument questions get a decline with a reason, never a force-fitted MCQ.
"""

import json

# Send-and-wait lifecycle (#4): a student submits and gets the response
# later — there is no live channel, so every state is a stored state.
#
#   Submitted  -> the student's question is in the queue
#   In Review  -> the fulfilment side has picked it up
#   Ready      -> an MCQ set is published; waiting for the student's attempt
#   Declined   -> not reducible to an objective MCQ (essay-type), with reason
#   Completed  -> the student answered; the reveal has happened
STATUS_SUBMITTED = "Submitted"
STATUS_IN_REVIEW = "In Review"
STATUS_READY = "Ready"
STATUS_DECLINED = "Declined"
STATUS_COMPLETED = "Completed"

STATUSES = (
    STATUS_SUBMITTED,
    STATUS_IN_REVIEW,
    STATUS_READY,
    STATUS_DECLINED,
    STATUS_COMPLETED,
)

# Legal transitions. Terminal states (Declined, Completed) go nowhere.
TRANSITIONS = {
    STATUS_SUBMITTED: (STATUS_IN_REVIEW, STATUS_READY, STATUS_DECLINED),
    STATUS_IN_REVIEW: (STATUS_READY, STATUS_DECLINED),
    STATUS_READY: (STATUS_COMPLETED,),
    STATUS_DECLINED: (),
    STATUS_COMPLETED: (),
}

# States the fulfilment side may still act on (publish an MCQ / decline).
PENDING_STATUSES = (STATUS_SUBMITTED, STATUS_IN_REVIEW)

# Guardrails on the submission itself, not pedagogy: an empty question has
# nothing to convert, and a book-length paste is not a homework question.
MAX_QUESTION_CHARS = 4000

# Photo attachments riding on a submission: the client caps its picker at 3,
# the server tolerates up to 5 (headroom for future clients, still bounded).
# Refs must be server-relative file URLs minted by the upload endpoint —
# never arbitrary strings, external URLs, or data blobs. Size is handled
# client-side by compression; the count cap + URL shape is the server's job.
MAX_ATTACHMENTS = 5
ATTACHMENT_URL_PREFIXES = ("/files/", "/private/files/")

# The shared knowledge-check MCQ primitive renders 2-6 options comfortably
# (lesson exercises ship 3-4); one option is not a choice at all.
MIN_OPTIONS = 2
MAX_OPTIONS = 6


def can_transition(from_status, to_status):
    """Whether `from_status` -> `to_status` is a legal lifecycle move."""
    return to_status in TRANSITIONS.get(from_status, ())


def validate_submission(question_text):
    """Validates a student's submitted question text.

    Returns the normalized (stripped) text. Raises ValueError with a
    human-readable message otherwise — the API layer converts that into a
    frappe.throw so the client surfaces the server's own words.
    """
    text = (question_text or "").strip()
    if not text:
        raise ValueError("Please type the homework question you are stuck on.")
    if len(text) > MAX_QUESTION_CHARS:
        raise ValueError(
            "That question is too long (%d characters, max %d). "
            "Send the specific problem you are stuck on."
            % (len(text), MAX_QUESTION_CHARS)
        )
    return text


def validate_attachments(attachments):
    """Validates the photo refs riding on a submission.

    Accepts None/empty (no attachments — returns None), a list of strings,
    or a JSON string encoding such a list (form-encoded clients). Each ref
    must be a server-relative file URL minted by the upload endpoint
    (ATTACHMENT_URL_PREFIXES); anything else — wrong container type, too
    many, non-string entries, external/absolute URLs — raises ValueError
    with a human-readable message, same posture as validate_submission.

    Returns the normalized (stripped) list, or None when absent.
    """
    if attachments is None or attachments == "":
        return None
    if isinstance(attachments, str):
        try:
            attachments = json.loads(attachments)
        except (TypeError, ValueError):
            raise ValueError("Attachments must be a list of uploaded file URLs.")
    if not isinstance(attachments, list):
        raise ValueError("Attachments must be a list of uploaded file URLs.")
    if not attachments:
        return None
    if len(attachments) > MAX_ATTACHMENTS:
        raise ValueError(
            "Too many photos (%d, max %d). Send just the pages that show "
            "the problem." % (len(attachments), MAX_ATTACHMENTS)
        )
    normalized = []
    for ref in attachments:
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("Attachments must be a list of uploaded file URLs.")
        ref = ref.strip()
        if not ref.startswith(ATTACHMENT_URL_PREFIXES):
            raise ValueError(
                "Attachment %r is not an uploaded file URL." % ref
            )
        normalized.append(ref)
    return normalized


def parse_attachment_refs(raw):
    """The stored attachment_refs JSON as a list for student reads.

    Catch-and-degrade (the list_homework_questions posture): malformed or
    unexpected stored content reads as no attachments, never an error.
    """
    if not raw:
        return []
    if isinstance(raw, list):
        parsed = raw
    else:
        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return []
    if not isinstance(parsed, list):
        return []
    return [ref for ref in parsed if isinstance(ref, str) and ref.strip()]


def validate_mcq_payload(payload):
    """Validates the fulfilment side's MCQ set before it is published.

    `payload` is a dict: question (the restatement of the student's own
    problem), options (correct answer + plausible wrong answers based on
    common mistakes), correct_index, optional explanation. Returns the
    normalized payload; raises ValueError on any violation.
    """
    if not isinstance(payload, dict):
        raise ValueError("mcq payload must be an object.")

    question = str(payload.get("question") or "").strip()
    if not question:
        raise ValueError("mcq payload needs a non-empty question restatement.")

    options = payload.get("options")
    if not isinstance(options, list):
        raise ValueError("mcq payload needs an options list.")
    normalized_options = [str(o or "").strip() for o in options]
    if any(not o for o in normalized_options):
        raise ValueError("mcq options must all be non-empty.")
    if not (MIN_OPTIONS <= len(normalized_options) <= MAX_OPTIONS):
        raise ValueError(
            "mcq needs between %d and %d options (got %d)."
            % (MIN_OPTIONS, MAX_OPTIONS, len(normalized_options))
        )
    if len(set(normalized_options)) != len(normalized_options):
        raise ValueError("mcq options must be distinct.")

    correct_index = payload.get("correct_index")
    if not isinstance(correct_index, int) or isinstance(correct_index, bool):
        raise ValueError("mcq correct_index must be an integer.")
    if not (0 <= correct_index < len(normalized_options)):
        raise ValueError(
            "mcq correct_index %d is out of range for %d options."
            % (correct_index, len(normalized_options))
        )

    explanation = str(payload.get("explanation") or "").strip()

    return {
        "question": question,
        "options": normalized_options,
        "correct_index": correct_index,
        "explanation": explanation,
    }


def validate_decline(reason):
    """Validates a decline (#1's essay/written-argument boundary).

    A decline must carry a reason the student sees — a silent decline reads
    as a lost question. Returns the normalized reason; raises ValueError.
    """
    text = (reason or "").strip()
    if not text:
        raise ValueError(
            "A decline needs a reason the student will see "
            "(e.g. why this question doesn't reduce to multiple choice)."
        )
    return text


def student_mcq_view(mcq):
    """The MCQ as a student may see it BEFORE their attempt: question and
    options only. correct_index and explanation stay server-side — the
    guide-don't-solve reveal happens exclusively through check_answer."""
    return {
        "question": mcq["question"],
        "options": list(mcq["options"]),
    }


def check_answer(mcq, selected_index):
    """Judges a recorded attempt and returns the reveal payload.

    This is the ONLY function that hands the truth to the student side, and
    only as a response to their pick — confirming or correcting after the
    attempt ("wrong, B is correct"), never before. Raises ValueError when
    selected_index isn't a valid option index.
    """
    options = mcq["options"]
    if not isinstance(selected_index, int) or isinstance(selected_index, bool):
        raise ValueError("selected_index must be an integer.")
    if not (0 <= selected_index < len(options)):
        raise ValueError(
            "selected_index %d is out of range for %d options."
            % (selected_index, len(options))
        )
    correct_index = mcq["correct_index"]
    return {
        "correct": selected_index == correct_index,
        "selected_index": selected_index,
        "correct_index": correct_index,
        "correct_option": options[correct_index],
        "explanation": mcq.get("explanation") or "",
    }
