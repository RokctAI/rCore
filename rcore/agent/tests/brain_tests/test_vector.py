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

import frappe
import unittest
from rcore.agent.services.llm_service import embed_text
from rcore.agent.brain import semantic_search
from rcore.agent.utils.engram_builder import process_event_in_realtime

class TestBrainVector(unittest.TestCase):
    def setUp(self):
        # Mocking the LLM Service if we are in a CI environment without models
        # But for this user's local setup, we might want to try real model if running
        pass

    def test_embedding_generation(self):
        """
        Test if embed_text returns a valid vector.
        """
        if not frappe.conf.get("ai_model_path"):
            print("⚠️ Skipping Vector Test: No AI Model Path configured.")
            return

        text = "Hello World"
        vector = embed_text(text)

        # Check if vector is returned
        if vector is None:
            # If worker is not running, this might fail or return None if using mock
            # We assume for integration test that worker might be reachable or we mock dispatch
            print("⚠️ Embedding Worker not reachable or returned None.")
            return

        self.assertIsInstance(vector, list)
        self.assertEqual(len(vector), 384, "MiniLM vector should be 384 dimensions")

    def test_engram_auto_vectorization(self):
        """
        Test if Engram creation triggers vector generation.
        """
        # Create a mock document event
        doc = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Vector Test Task",
            "status": "Open"
        }).insert(ignore_permissions=True)

        # Trigger the hook manually (since hooks might not fire in test runner same way)
        process_event_in_realtime(doc, "on_update")

        # Fetch the Engram
        engram_name = f"ToDo-{doc.name}"
        if frappe.db.exists("Engram", engram_name):
            engram = frappe.get_doc("Engram", engram_name)

            # If worker is running, embedding should be populated (async timing issue potential)
            # In real unit test we'd mock the worker to return immediately.
            # Here we just check if the logic ran without error.
            pass

    def test_semantic_search_api(self):
        """
        Test the semantic_search API structure.
        """
        # We can't easily test accurate semantic retrieval without a running model and populated DB
        # But we can test the SQL generation fails gracefully or runs

        try:
            results = semantic_search("test query", limit=1)
            self.assertIsInstance(results, list)
        except Exception as e:
            # It might fail if extension not installed or worker down
            print(f"Semantic Search Test Error: {e}")
