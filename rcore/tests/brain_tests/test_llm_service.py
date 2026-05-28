# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from rcore.services.llm_service import dispatch_ai_task, ask_brain, BRAIN_QUEUE, VISION_QUEUE
import json

class TestLLMService(FrappeTestCase):
    @patch("rcore.services.llm_service.redis.from_url")
    def test_dispatch_ai_task_success(self, mock_redis_url):
        mock_r = MagicMock()
        mock_redis_url.return_value = mock_r
        
        # Simulate worker response in Redis
        job_id = None
        def mock_get(key):
            nonlocal job_id
            if key.startswith("rokct:result:"):
                # Extract job_id from key
                job_id = key.split(":")[-1]
                return json.dumps({"status": "success", "text": "AI Response"})
            return None
            
        mock_r.get.side_effect = mock_get
        
        result = dispatch_ai_task(BRAIN_QUEUE, {"prompt": "hello"})
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "AI Response")
        self.assertTrue(mock_r.rpush.called)
        self.assertTrue(mock_r.delete.called)

    @patch("rcore.services.llm_service.redis.from_url")
    @patch("rcore.services.llm_service.time.time")
    def test_dispatch_ai_task_timeout(self, mock_time, mock_redis_url):
        mock_r = MagicMock()
        mock_redis_url.return_value = mock_r
        mock_r.get.return_value = None # Never returns result
        
        # Mock time to simulate timeout
        # We need enough values for the loop.
        # Initial call + several loop calls + final check
        # Let's use a generator or a large list to be safe.
        mock_time.side_effect = [0, 0, 10, 20, 30, 70, 80, 90] 
        
        result = dispatch_ai_task(BRAIN_QUEUE, {"prompt": "timeout test"}, timeout=50)
        
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["message"])

    @patch("rcore.services.llm_service._should_route_extensions")
    @patch("rcore.services.llm_service._call_jina_vision")
    def test_hybrid_routing_vision(self, mock_jina, mock_should_route):
        mock_should_route.return_value = True
        mock_jina.return_value = {"status": "success", "message": "Jina Response"}
        
        result = dispatch_ai_task(VISION_QUEUE, {"file_url": "http://example.com/img.jpg"})
        
        self.assertEqual(result["message"], "Jina Response")
        mock_jina.assert_called_once()

    @patch("rcore.services.llm_service.requests.post")
    def test_ask_brain_wrapper(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "Juvo here"}}]}
        mock_post.return_value = mock_response
        
        result = ask_brain("Who are you?")
        
        self.assertEqual(result["text"], "Juvo here")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://127.0.0.1:8642/v1/chat/completions")
        self.assertEqual(kwargs["json"]["messages"][-1]["content"], "Who are you?")

    @patch("rcore.services.llm_service.dispatch_ai_task")
    def test_embed_text_list(self, mock_dispatch):
        """test that list inputs are accepted and dispatched correctly"""
        mock_dispatch.return_value = {"status": "success", "embedding": [[0.1, 0.2], [0.3, 0.4]]}
        
        from rcore.services.llm_service import embed_text
        
        inputs = ["Hello", "World"]
        result = embed_text(inputs)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [0.1, 0.2])
        
        args, _ = mock_dispatch.call_args
        self.assertEqual(args[1]["text"], inputs)

if __name__ == "__main__":
    import unittest
    unittest.main()
