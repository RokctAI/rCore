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

"""AI drafting for the homework fulfilment queue, pinned standalone (no
frappe, no site, no network — `python -m unittest
tests.test_homework_draft_rules`).

Loaded by file path rather than package import, matching
test_homework_rules.py: workspace python modules import through an
`rcore` placeholder and only resolve inside a composed app;
homework_draft_rules.py is deliberately frappe-free so this test runs
anywhere python does. homework_rules.py is loaded alongside it to pin the
contract that a parsed draft is exactly what publish_homework_mcq accepts.
"""

import importlib.util
import json
import os
import unittest

_DIR = os.path.join(os.path.dirname(__file__), "..")


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_DIR, filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


draft_rules = _load("rlms_homework_draft_rules", "homework_draft_rules.py")
homework_rules = _load("rlms_homework_rules_for_draft", "homework_rules.py")


VALID_DRAFT_JSON = json.dumps(
    {
        "question": "Solve for x: 2x + 6 = 14",
        "options": ["x = 4", "x = 10", "x = 7", "x = -4"],
        "correct_index": 0,
        "explanation": "Subtract 6 from both sides (2x = 8), then divide by 2.",
    }
)


class TestOptionBoundsLockstep(unittest.TestCase):
    def test_draft_bounds_match_publish_validator(self):
        # The prompt asks inside exactly the bounds validate_mcq_payload
        # enforces — a drift here would produce drafts publish rejects.
        self.assertEqual(draft_rules.MIN_OPTIONS, homework_rules.MIN_OPTIONS)
        self.assertEqual(draft_rules.MAX_OPTIONS, homework_rules.MAX_OPTIONS)


class TestDraftPrompt(unittest.TestCase):
    def test_system_prompt_carries_the_pedagogy_contract(self):
        prompt = draft_rules.DRAFT_SYSTEM_PROMPT
        # Guide-don't-solve: one correct option, common-mistake distractors,
        # post-attempt explanation, no answer leakage, human review.
        self.assertIn("exactly one correct", prompt)
        self.assertIn("common mistake", prompt)
        self.assertIn("after the student has picked", prompt)
        self.assertIn("Do not reveal", prompt)
        self.assertIn("human operator will review", prompt)
        # Bounds and the exact output keys the validator expects.
        self.assertIn("between 2 and 6", prompt)
        for key in ('"question"', '"options"', '"correct_index"', '"explanation"'):
            self.assertIn(key, prompt)

    def test_user_prompt_includes_question_and_context(self):
        text = draft_rules.draft_user_prompt(
            "  What is 3/4 + 1/8?  ", subject="Maths", grade=6
        )
        self.assertIn("Subject: Maths", text)
        self.assertIn("Grade: 6", text)
        self.assertIn("Student's question: What is 3/4 + 1/8?", text)

    def test_user_prompt_omits_absent_context(self):
        text = draft_rules.draft_user_prompt("Why is the sky blue?")
        self.assertNotIn("Subject:", text)
        self.assertNotIn("Grade:", text)
        self.assertEqual(text, "Student's question: Why is the sky blue?")

    def test_request_shape_and_json_mode(self):
        body = draft_rules.build_draft_request("Solve 2x = 8", "Maths", 7)
        self.assertEqual(
            body["system_instruction"]["parts"][0]["text"],
            draft_rules.DRAFT_SYSTEM_PROMPT,
        )
        self.assertEqual(body["contents"][0]["role"], "user")
        self.assertIn("Solve 2x = 8", body["contents"][0]["parts"][0]["text"])
        self.assertEqual(
            body["generationConfig"]["response_mime_type"], "application/json"
        )


class TestParseDraftResponse(unittest.TestCase):
    def test_plain_json(self):
        parsed = draft_rules.parse_draft_response(VALID_DRAFT_JSON)
        self.assertEqual(parsed["correct_index"], 0)
        self.assertEqual(len(parsed["options"]), 4)

    def test_fenced_json(self):
        parsed = draft_rules.parse_draft_response(
            "```json\n%s\n```" % VALID_DRAFT_JSON
        )
        self.assertEqual(parsed["correct_index"], 0)

    def test_json_with_surrounding_prose(self):
        parsed = draft_rules.parse_draft_response(
            "Here is the draft you asked for:\n%s\nHope that helps!"
            % VALID_DRAFT_JSON
        )
        self.assertEqual(parsed["question"], "Solve for x: 2x + 6 = 14")

    def test_empty_and_non_json_raise(self):
        for bad in ("", None, "no json here", "```\n\n```"):
            with self.assertRaises(ValueError):
                draft_rules.parse_draft_response(bad)

    def test_broken_json_raises(self):
        with self.assertRaises(ValueError):
            draft_rules.parse_draft_response('{"question": "unclosed"')

    def test_json_array_is_not_a_draft(self):
        with self.assertRaises(ValueError):
            draft_rules.parse_draft_response('["not", "an", "object"]')


class TestDraftMatchesPublishContract(unittest.TestCase):
    def test_parsed_draft_passes_publish_validation(self):
        # The endpoint's exact pipeline: parse, then validate with the SAME
        # function publish_homework_mcq uses — shape parity by construction.
        draft = homework_rules.validate_mcq_payload(
            draft_rules.parse_draft_response(VALID_DRAFT_JSON)
        )
        self.assertEqual(
            set(draft), {"question", "options", "correct_index", "explanation"}
        )

    def test_model_shape_drift_is_rejected_not_repaired(self):
        # A model answer with the wrong shape must fail validation loudly —
        # the operator sees an honest error, never a half-broken prefill.
        drifted = json.dumps(
            {"question": "Solve", "options": ["only one"], "correct_index": 0}
        )
        with self.assertRaises(ValueError):
            homework_rules.validate_mcq_payload(
                draft_rules.parse_draft_response(drifted)
            )


if __name__ == "__main__":
    unittest.main()
