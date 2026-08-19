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

"""Compose-time tests for the `agent.api.ask_assistant` endpoint (the
frappe half). Follows the brain_tests convention (FrappeTestCase + mocks,
app_name-templated imports, runnable in a composed bench). The frappe-free
half has a standalone suite in test_assistant_rules.py."""

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from rcore.agent.brain.ask_assistant import ask_assistant


class TestAskAssistant(FrappeTestCase):
    @patch("rcore.agent.brain.ask_assistant.requests.post")
    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    def test_success_returns_llm_answer(self, mock_get_api_key, mock_post):
        mock_get_api_key.return_value = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "A fraction is part of a whole."}]}}
            ]
        }
        mock_post.return_value = mock_response

        result = ask_assistant(question="What is a fraction?", subtopic_ref="fractions")

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["response"], "A fraction is part of a whole.")
        self.assertEqual(result["intent"], "question")

        # The provider was actually called with the student's question and
        # the configured key — no canned answer path exists.
        _, kwargs = mock_post.call_args
        self.assertEqual(
            kwargs["json"]["contents"][0]["parts"][0]["text"], "What is a fraction?"
        )
        self.assertEqual(kwargs["headers"]["x-goog-api-key"], "test-key")

    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    def test_missing_credential_fails_honestly(self, mock_get_api_key):
        # No key configured anywhere -> structured "not configured" error via
        # the normal frappe error path. Never a fake answer.
        mock_get_api_key.return_value = None

        with self.assertRaises(frappe.ValidationError) as ctx:
            ask_assistant(question="What is a fraction?")
        self.assertIn("not configured", str(ctx.exception))

    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    def test_empty_question_rejected(self, mock_get_api_key):
        mock_get_api_key.return_value = "test-key"

        with self.assertRaises(frappe.ValidationError):
            ask_assistant(question="   ")

        # Validation fires before any credential/provider work.
        mock_get_api_key.assert_not_called()

    @patch("rcore.agent.brain.ask_assistant.requests.post")
    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    def test_provider_failure_fails_honestly(self, mock_get_api_key, mock_post):
        mock_get_api_key.return_value = "test-key"
        mock_post.side_effect = Exception("connection refused")

        with self.assertRaises(frappe.ValidationError) as ctx:
            ask_assistant(question="What is a fraction?")
        self.assertIn("unavailable", str(ctx.exception).lower())

    @patch("rcore.agent.brain.ask_assistant.requests.post")
    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    def test_empty_llm_answer_fails_honestly(self, mock_get_api_key, mock_post):
        mock_get_api_key.return_value = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {"candidates": []}
        mock_post.return_value = mock_response

        with self.assertRaises(frappe.ValidationError):
            ask_assistant(question="What is a fraction?")

    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    @patch("rcore.agent.brain.ask_assistant._plan_allows_chat")
    def test_plan_without_chat_refuses_with_friendly_line(
        self, mock_plan_gate, mock_get_api_key
    ):
        # Owner's rule: a plan that excludes the assistant disables chat.
        # The refusal is ONE friendly line and fires before any credential
        # or provider work.
        mock_plan_gate.return_value = False

        with self.assertRaises(frappe.ValidationError) as ctx:
            ask_assistant(question="What is a fraction?")
        self.assertIn("isn't included in your plan", str(ctx.exception))
        mock_get_api_key.assert_not_called()

    @patch("rcore.agent.brain.ask_assistant.requests.post")
    @patch("rcore.agent.brain.ask_assistant.get_api_key")
    @patch("rcore.agent.brain.ask_assistant.frappe.get_all")
    def test_plan_lookup_failure_fails_open(
        self, mock_get_all, mock_get_api_key, mock_post
    ):
        # Plan info unavailable (lookup blows up) -> ALLOW: availability
        # decisions default to not breaking paying students. The diagnostic
        # goes to the server log, never to the student.
        mock_get_all.side_effect = Exception("db down")
        mock_get_api_key.return_value = "test-key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Sure."}]}}]
        }
        mock_post.return_value = mock_response

        result = ask_assistant(question="What is a fraction?")
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    import unittest

    unittest.main()
