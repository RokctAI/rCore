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

import json

class AssistantPipeline:
    def __init__(self):
        self.similarity_threshold = 0.85
        
    def classify_intent(self, text: str) -> str:
        # Mock logic representing Sentence Transformer Intent Classification
        text_lower = text.lower()
        if "hello" in text_lower or "cool" in text_lower:
            return "chatter"
        elif "audio" in text_lower or "buffering" in text_lower:
            return "support"
        else:
            return "question"

    def rewrite_prompt(self, text: str) -> str:
        # Mock logic representing Dignity Guard
        return f"Could you please elaborate on the concept relating to: {text}?"

    def check_subtopic_scope(self, text: str) -> bool:
        # Mock logic representing Subtopic Scope Check
        return True

    def process_message(self, message: str) -> dict:
        intent = self.classify_intent(message)
        
        if intent == "chatter":
            return {"status": "success", "response": "Hey there! Let's stay focused on the classroom chalkboard.", "intent": intent}
        elif intent == "support":
            return {"status": "success", "response": "I've notified support about your issue. They will assist you shortly.", "intent": intent}
        
        rewritten = self.rewrite_prompt(message)
        
        if not self.check_subtopic_scope(rewritten):
            return {"status": "success", "response": "That's an interesting question, but let's redirect back to the active lesson topic.", "intent": intent}
            
        return {"status": "success", "response": "Here is a mathematical explanation for your question based on our LLM.", "intent": intent, "rewritten": rewritten}

