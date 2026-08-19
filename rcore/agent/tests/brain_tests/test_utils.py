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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from rcore.agent.brain.ai_manager import _verify_name_match

class TestBrainUtils(unittest.TestCase):
    def test_verify_name_match_exact(self):
        self.assertTrue(_verify_name_match("John Smith", "John Smith"))
        self.assertTrue(_verify_name_match("JOHN SMITH", "john smith"))

    def test_verify_name_match_with_titles(self):
        self.assertTrue(_verify_name_match("John Smith", "Mr John Smith"))
        self.assertTrue(_verify_name_match("DR JOHN SMITH", "John Smith"))
        self.assertTrue(_verify_name_match("Prof Jane Doe", "Jane Doe"))

    def test_verify_name_match_partial(self):
        # E.g. "John Smith" should match "MR JOHN SIMON SMITH"
        self.assertTrue(_verify_name_match("John Smith", "MR JOHN SIMON SMITH"))
        self.assertTrue(_verify_name_match("Jane Doe", "Jane Mary Doe"))

    def test_verify_name_match_short_names(self):
        self.assertTrue(_verify_name_match("John", "John Smith"))
        self.assertFalse(_verify_name_match("John", "Jane Doe"))

    def test_verify_name_match_mismatch(self):
        self.assertFalse(_verify_name_match("John Smith", "Jane Doe"))
        self.assertFalse(_verify_name_match("Bob", "Alice"))

    def test_verify_name_match_special_chars(self):
        self.assertTrue(_verify_name_match("O'Connor", "O Connor"))
        self.assertTrue(_verify_name_match("Mary-Jane", "Mary Jane"))

if __name__ == "__main__":
    unittest.main()
