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

"""Knowledge-bites index shape rules (decision #52) — the gate both
endpoints share: what the read endpoint degrades to empty, the publish
endpoint refuses.

Loaded by file path rather than package import on purpose (same reason as
test_alert_rules.py): bite_rules.py is deliberately frappe-free, so this
test runs anywhere python does — `python -m unittest` from the repo, no
bench, no site, no substitution.
"""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "bite_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_bite_rules", _MODULE_PATH)
bite_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bite_rules)

# The real generated shape: lesson-slug -> LIST of bite objects (one lesson
# can carry several bites; the app offers exactly one). Slugs/fields match
# the factory's rehoused tree
# (lessons/curriculum/CAPS/{subject}/knowledge_bites/{grade}/{lesson-slug}/
# {bite-slug}/question.md).
VALID = {
    "bites": {
        "lines-gradients-and-inclination": [
            {
                "bite_slug": "dbe-maths-g12-p2-2025-nov-q3-1",
                "subject": "maths",
                "grade": 11,
                "title": "Past-Paper Worked Example — Q3.1",
                "question_md": "# Past-Paper Worked Example — Q3.1\n...",
            }
        ],
        "quadratics-by-factorisation": [],
    }
}


class TestBitesIndexShape(unittest.TestCase):
    def test_generated_shape_is_valid(self):
        self.assertTrue(bite_rules.is_valid_bites_index(VALID))

    def test_empty_index_is_valid(self):
        # The degrade target itself must pass the gate, or the read endpoint
        # could answer a shape the client refuses.
        self.assertTrue(bite_rules.is_valid_bites_index(bite_rules.EMPTY_INDEX))

    def test_missing_bites_map_is_invalid(self):
        self.assertFalse(bite_rules.is_valid_bites_index({}))
        self.assertFalse(bite_rules.is_valid_bites_index({"skills": {}}))

    def test_non_dict_documents_are_invalid(self):
        self.assertFalse(bite_rules.is_valid_bites_index(None))
        self.assertFalse(bite_rules.is_valid_bites_index([]))
        self.assertFalse(bite_rules.is_valid_bites_index("bites"))

    def test_per_lesson_value_must_be_a_list(self):
        # The skills index maps ref -> object; bites map slug -> LIST. A
        # publisher accidentally sending the skills granularity must be
        # refused, not half-served.
        self.assertFalse(
            bite_rules.is_valid_bites_index(
                {"bites": {"lines-gradients-and-inclination": {"bite_slug": "x"}}}
            )
        )

    def test_list_entries_must_be_objects(self):
        self.assertFalse(
            bite_rules.is_valid_bites_index({"bites": {"a-lesson": ["not-an-object"]}})
        )

    def test_counts_back_the_publish_receipt(self):
        lessons, bites = bite_rules.count_bites(VALID)
        self.assertEqual(lessons, 2)
        self.assertEqual(bites, 1)
        self.assertEqual(bite_rules.count_bites(bite_rules.EMPTY_INDEX), (0, 0))


if __name__ == "__main__":
    unittest.main()
