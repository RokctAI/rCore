# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from rcore.ai_manager import _verify_name_match


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
