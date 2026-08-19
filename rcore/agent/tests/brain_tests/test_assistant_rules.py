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

"""Standalone-runnable tests for brain/assistant_rules.py (the frappe-free
half of `agent.api.ask_assistant`).

The surrounding packages only become importable after compose-time
app_name templating (`__init__.py` files import `rcore.…`), so this
suite loads the module directly from its file path — stdlib only, runnable
right here:

    python3 agent/frappe/src/tests/brain_tests/test_assistant_rules.py
"""

import importlib.util
import os
import unittest
from datetime import date

_RULES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "brain", "assistant_rules.py")
)
_spec = importlib.util.spec_from_file_location("assistant_rules", _RULES_PATH)
assistant_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assistant_rules)


class TestValidateQuestion(unittest.TestCase):
    def test_accepts_and_strips_normal_question(self):
        self.assertEqual(
            assistant_rules.validate_question("  What is a fraction?  "),
            "What is a fraction?",
        )

    def test_rejects_none(self):
        with self.assertRaises(ValueError):
            assistant_rules.validate_question(None)

    def test_rejects_empty_and_whitespace(self):
        for bad in ("", "   ", "\n\t"):
            with self.assertRaises(ValueError):
                assistant_rules.validate_question(bad)

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            assistant_rules.validate_question(42)

    def test_rejects_over_cap(self):
        too_long = "x" * (assistant_rules.MAX_QUESTION_CHARS + 1)
        with self.assertRaises(ValueError):
            assistant_rules.validate_question(too_long)

    def test_accepts_exactly_at_cap(self):
        at_cap = "x" * assistant_rules.MAX_QUESTION_CHARS
        self.assertEqual(assistant_rules.validate_question(at_cap), at_cap)


class TestSystemInstruction(unittest.TestCase):
    def test_without_subtopic_is_base_prompt(self):
        self.assertEqual(
            assistant_rules.system_instruction(), assistant_rules.SYSTEM_PROMPT
        )
        self.assertEqual(
            assistant_rules.system_instruction("   "), assistant_rules.SYSTEM_PROMPT
        )

    def test_with_subtopic_appends_scope(self):
        prompt = assistant_rules.system_instruction("fractions-gr4-t2")
        self.assertTrue(prompt.startswith(assistant_rules.SYSTEM_PROMPT))
        self.assertIn("fractions-gr4-t2", prompt)


class TestLlmEndpoint(unittest.TestCase):
    def test_uses_given_model(self):
        self.assertEqual(
            assistant_rules.llm_endpoint("gemini-2.5-flash"),
            assistant_rules.GEMINI_BASE_URL + "/gemini-2.5-flash:generateContent",
        )

    def test_falls_back_to_default_model(self):
        self.assertEqual(
            assistant_rules.llm_endpoint(None),
            assistant_rules.GEMINI_BASE_URL
            + "/%s:generateContent" % assistant_rules.DEFAULT_MODEL,
        )


class TestBuildLlmPayload(unittest.TestCase):
    def test_payload_shape(self):
        payload = assistant_rules.build_llm_payload("What is 2 + 2?", "arith-gr1")
        self.assertEqual(
            payload["contents"],
            [{"role": "user", "parts": [{"text": "What is 2 + 2?"}]}],
        )
        system_text = payload["system_instruction"]["parts"][0]["text"]
        self.assertIn("arith-gr1", system_text)

    def test_payload_never_contains_canned_answer(self):
        # Honesty guard: the request carries the student's question, not any
        # pre-baked response text.
        payload = assistant_rules.build_llm_payload("Explain photosynthesis")
        self.assertNotIn("response", payload)


class TestExtractResponseText(unittest.TestCase):
    def _gemini_body(self, parts):
        return {"candidates": [{"content": {"parts": parts}}]}

    def test_extracts_single_part(self):
        body = self._gemini_body([{"text": "A fraction is part of a whole."}])
        self.assertEqual(
            assistant_rules.extract_response_text(body),
            "A fraction is part of a whole.",
        )

    def test_joins_multiple_parts(self):
        body = self._gemini_body([{"text": "Step 1. "}, {"text": "Step 2."}])
        self.assertEqual(
            assistant_rules.extract_response_text(body), "Step 1. Step 2."
        )

    def test_rejects_non_dict(self):
        with self.assertRaises(ValueError):
            assistant_rules.extract_response_text(["not", "a", "dict"])

    def test_rejects_no_candidates(self):
        with self.assertRaises(ValueError):
            assistant_rules.extract_response_text({"candidates": []})
        with self.assertRaises(ValueError):
            assistant_rules.extract_response_text({})

    def test_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            assistant_rules.extract_response_text(self._gemini_body([{"text": "  "}]))
        with self.assertRaises(ValueError):
            assistant_rules.extract_response_text(self._gemini_body([]))


class TestSuccessResponse(unittest.TestCase):
    def test_wire_shape_matches_dart_model(self):
        # Pins the contract AssistantQuestionResponse.fromJson parses.
        self.assertEqual(
            assistant_rules.success_response("x = 4"),
            {"status": "success", "response": "x = 4", "intent": "question"},
        )


class TestPlanChatGate(unittest.TestCase):
    """The subscription-plan gate for the chat assistant (owner's rule
    2026-08-14): explicit 0 disables; everything unresolvable fails OPEN."""

    def test_explicit_off_disables(self):
        self.assertFalse(assistant_rules.plan_allows_chat(0))
        self.assertFalse(assistant_rules.plan_allows_chat("0"))

    def test_explicit_on_allows(self):
        self.assertTrue(assistant_rules.plan_allows_chat(1))
        self.assertTrue(assistant_rules.plan_allows_chat("1"))

    def test_unresolvable_fails_open(self):
        self.assertTrue(assistant_rules.plan_allows_chat(None))
        self.assertTrue(assistant_rules.plan_allows_chat("weird"))

    def test_refusal_message_is_one_friendly_line(self):
        # Student copy only — no diagnostics, no config detail.
        self.assertEqual(
            assistant_rules.PLAN_REFUSAL_MESSAGE,
            "Chat isn't included in your plan.",
        )


class TestGoverningPlanFlag(unittest.TestCase):
    today = date(2026, 8, 14)

    def test_newest_covering_record_with_a_flag_wins(self):
        records = [
            {
                "assistant_chat": 0,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
            {
                "assistant_chat": 1,
                "period_start": date(2026, 7, 1),
                "period_end": date(2026, 12, 31),
            },
        ]
        self.assertEqual(
            assistant_rules.governing_plan_flag(records, self.today), 0
        )

    def test_expired_future_and_planless_records_do_not_govern(self):
        records = [
            {  # future
                "assistant_chat": 0,
                "period_start": date(2026, 9, 1),
                "period_end": date(2026, 9, 30),
            },
            {  # expired
                "assistant_chat": 0,
                "period_start": date(2026, 1, 1),
                "period_end": date(2026, 1, 31),
            },
            {  # legacy: covers today but has no plan info
                "assistant_chat": None,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
        ]
        self.assertIsNone(
            assistant_rules.governing_plan_flag(records, self.today)
        )

    def test_no_records_govern_nothing(self):
        self.assertIsNone(assistant_rules.governing_plan_flag([], self.today))
        self.assertIsNone(
            assistant_rules.governing_plan_flag(None, self.today)
        )


if __name__ == "__main__":
    unittest.main()
