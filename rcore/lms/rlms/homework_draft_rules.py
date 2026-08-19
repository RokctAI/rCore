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

"""AI drafting rules for the homework fulfilment queue — frappe-free pure
module (the homework_rules.py / time_gates.py pattern).

Today the operator hand-writes every MCQ set in the fulfilment queue. This
module shapes an AI request that drafts one FOR the operator to edit and
approve — the human stays in the loop: the draft never publishes itself,
publish_homework_mcq remains the only door to the student's Ready state.

This module owns the prompt (engineered for #1's guide-don't-solve
contract: one correct answer, plausible common-mistake distractors, a
friendly post-attempt explanation) and the parsing of the provider's text
back into a candidate payload. The canonical shape judgement stays with
homework_rules.validate_mcq_payload — the API layer runs every parsed
draft through it, so a draft can never be shaped differently from what
publish_homework_mcq accepts. Credentials, HTTP, and error translation
live in api/homework.py, which reuses the assistant chat's provider path.
"""

import json

# Draft option-count guidance, kept in lockstep with homework_rules
# (test-pinned equal): the prompt asks inside the same bounds the publish
# validator enforces.
MIN_OPTIONS = 2
MAX_OPTIONS = 6

# The drafting persona: the operator-side counterpart of the tutor chat's
# guide-don't-solve posture. The model solves internally, but what it
# emits is a check the student must attempt — never a worked answer blob.
DRAFT_SYSTEM_PROMPT = (
    "You draft multiple-choice checks for a homework-help team inside a "
    "learning app for school students. A student sent a homework question; "
    "a human operator will review and edit whatever you draft before "
    "anything reaches the student. Work out the real answer carefully, "
    "then turn the student's own question into one multiple-choice check: "
    "restate the question clearly, give between %d and %d answer options "
    "with exactly one correct, and make every wrong option the plausible "
    "result of a common mistake a student actually makes on this kind of "
    "problem — never obviously silly fillers. Write a short, friendly, "
    "age-appropriate explanation of the steps that will be shown only "
    "after the student has picked an option. Do not reveal or hint at "
    "which option is correct anywhere in the question or option text. "
    "Respond with ONLY a JSON object, no markdown fences and no prose, "
    'with exactly these keys: "question" (string), "options" (array of '
    'strings), "correct_index" (integer, 0-based), "explanation" (string).'
) % (MIN_OPTIONS, MAX_OPTIONS)


def draft_user_prompt(question_text, subject=None, grade=None):
    """The user-turn text: the student's question plus whatever
    subject/grade context the submission carried."""
    lines = []
    subject = (subject or "").strip() if isinstance(subject, str) else subject
    if subject:
        lines.append("Subject: %s" % subject)
    if grade not in (None, ""):
        lines.append("Grade: %s" % grade)
    lines.append("Student's question: %s" % (question_text or "").strip())
    return "\n".join(lines)


def build_draft_request(question_text, subject=None, grade=None):
    """Gemini generateContent request body for one draft. Asks the provider
    for a JSON response outright (response_mime_type) so parsing does not
    depend on the model resisting markdown habits."""
    return {
        "system_instruction": {"parts": [{"text": DRAFT_SYSTEM_PROMPT}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": draft_user_prompt(question_text, subject, grade)}
                ],
            }
        ],
        "generationConfig": {"response_mime_type": "application/json"},
    }


def parse_draft_response(text):
    """The provider's answer text as a candidate MCQ dict.

    Tolerates markdown code fences and stray prose around the JSON object
    (models drift even when asked not to), but never repairs the content:
    no parsable object, or a parsed non-object, raises ValueError — the
    endpoint fails honestly rather than fabricating a draft. The returned
    dict is a CANDIDATE only; callers must pass it through
    homework_rules.validate_mcq_payload before showing it to anyone.
    """
    raw = (text or "").strip()
    if not raw:
        raise ValueError("AI draft response was empty.")
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else ""
        raw = raw.rsplit("```", 1)[0].strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("AI draft response contained no JSON object.")
    try:
        parsed = json.loads(raw[start : end + 1])
    except (TypeError, ValueError):
        raise ValueError("AI draft response was not valid JSON.")
    if not isinstance(parsed, dict):
        raise ValueError("AI draft response was not a JSON object.")
    return parsed
