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

"""Announcement audience/window rules — what the student read shows and the
operator create refuses (one-way operator→student posts on the Glance
surface).

Loaded by file path rather than package import on purpose (same reason as
test_bite_rules.py): announcement_rules.py is deliberately frappe-free, so
this test runs anywhere python does — `python -m unittest` from the repo,
no bench, no site, no substitution.
"""

import importlib.util
import os
import unittest
from datetime import datetime

_MODULE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "announcement_rules.py"
)
_spec = importlib.util.spec_from_file_location(
    "rlms_announcement_rules", _MODULE_PATH
)
announcement_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(announcement_rules)

NOW = datetime(2026, 8, 14, 10, 0, 0)


def post(**overrides):
    row = {
        "name": "a1",
        "title": "Holiday programme starts Monday",
        "body": "The first live session is at 09:00 — see you there!",
        "subject": None,
        "grade": None,
        "curriculum": None,
        "starts_at": None,
        "ends_at": None,
    }
    row.update(overrides)
    return row


class TestWindow(unittest.TestCase):
    def test_no_window_is_always_active(self):
        self.assertTrue(announcement_rules.in_window(None, None, NOW))

    def test_before_start_is_hidden(self):
        self.assertFalse(
            announcement_rules.in_window(datetime(2026, 8, 14, 11, 0), None, NOW)
        )

    def test_at_start_is_active(self):
        self.assertTrue(announcement_rules.in_window(NOW, None, NOW))

    def test_after_end_is_hidden(self):
        self.assertFalse(
            announcement_rules.in_window(None, datetime(2026, 8, 14, 9, 0), NOW)
        )

    def test_end_is_exclusive(self):
        self.assertFalse(announcement_rules.in_window(None, NOW, NOW))

    def test_inside_both_bounds_is_active(self):
        self.assertTrue(
            announcement_rules.in_window(
                datetime(2026, 8, 14, 9, 0), datetime(2026, 8, 14, 11, 0), NOW
            )
        )

    def test_string_datetimes_parse(self):
        # frappe.get_all hands back strings in some paths — both the frappe
        # "YYYY-MM-DD HH:MM:SS" shape and ISO parse.
        self.assertTrue(
            announcement_rules.in_window("2026-08-14 09:00:00", None, NOW)
        )
        self.assertFalse(
            announcement_rules.in_window(None, "2026-08-14T09:59:59", NOW)
        )

    def test_unparseable_reads_as_unset(self):
        # Garbage in storage must never error a student read.
        self.assertTrue(announcement_rules.in_window("soon", "later", NOW))


class TestAudience(unittest.TestCase):
    def test_untargeted_matches_everyone(self):
        self.assertTrue(announcement_rules.matches_audience(None, None, None, None))
        self.assertTrue(
            announcement_rules.matches_audience(None, None, 11, "CAPS")
        )

    def test_grade_filter_requires_that_grade(self):
        self.assertTrue(announcement_rules.matches_audience(11, None, 11, None))
        self.assertFalse(announcement_rules.matches_audience(11, None, 10, None))

    def test_grade_filter_hides_from_unknown_grade(self):
        self.assertFalse(announcement_rules.matches_audience(11, None, None, None))

    def test_grade_filter_tolerates_string_values(self):
        self.assertTrue(announcement_rules.matches_audience("11", None, 11, None))

    def test_curriculum_filter_requires_that_curriculum(self):
        self.assertTrue(
            announcement_rules.matches_audience(None, "CAPS", None, "CAPS")
        )
        self.assertFalse(
            announcement_rules.matches_audience(None, "CAPS", None, "IEB")
        )
        self.assertFalse(
            announcement_rules.matches_audience(None, "CAPS", None, None)
        )

    def test_both_filters_must_match(self):
        self.assertTrue(announcement_rules.matches_audience(11, "CAPS", 11, "CAPS"))
        self.assertFalse(announcement_rules.matches_audience(11, "CAPS", 11, "IEB"))
        self.assertFalse(
            announcement_rules.matches_audience(11, "CAPS", 12, "CAPS")
        )


class TestVisible(unittest.TestCase):
    def test_filters_and_preserves_order(self):
        rows = [
            post(name="everyone"),
            post(name="grade11", grade=11),
            post(name="grade12", grade=12),
            post(name="future", starts_at=datetime(2026, 8, 15)),
            post(name="ended", ends_at=datetime(2026, 8, 13)),
            post(name="caps", curriculum="CAPS"),
            post(name="ieb", curriculum="IEB"),
        ]
        shown = announcement_rules.visible(rows, 11, "CAPS", NOW)
        self.assertEqual(
            [row["name"] for row in shown], ["everyone", "grade11", "caps"]
        )

    def test_unknown_student_sees_only_untargeted(self):
        rows = [post(name="everyone"), post(name="grade11", grade=11)]
        shown = announcement_rules.visible(rows, None, None, NOW)
        self.assertEqual([row["name"] for row in shown], ["everyone"])

    def test_empty_rows(self):
        self.assertEqual(announcement_rules.visible([], 11, "CAPS", NOW), [])


class TestValidatePost(unittest.TestCase):
    def test_valid_minimal_post(self):
        self.assertIsNone(announcement_rules.validate_post("Title", "Body"))

    def test_valid_full_post(self):
        self.assertIsNone(
            announcement_rules.validate_post(
                "Title",
                "Body",
                grade=11,
                curriculum="CAPS",
                starts_at="2026-08-14 09:00:00",
                ends_at="2026-08-15 09:00:00",
            )
        )

    def test_title_required(self):
        self.assertEqual(
            announcement_rules.validate_post("  ", "Body"), "title is required."
        )

    def test_body_required(self):
        self.assertEqual(
            announcement_rules.validate_post("Title", ""), "body is required."
        )

    def test_grade_bounds(self):
        self.assertIsNone(announcement_rules.validate_post("T", "B", grade=1))
        self.assertIsNone(announcement_rules.validate_post("T", "B", grade=12))
        self.assertIsNotNone(announcement_rules.validate_post("T", "B", grade=0))
        self.assertIsNotNone(announcement_rules.validate_post("T", "B", grade=13))
        self.assertIsNotNone(
            announcement_rules.validate_post("T", "B", grade="eleven")
        )

    def test_curriculum_must_be_known(self):
        self.assertIsNotNone(
            announcement_rules.validate_post("T", "B", curriculum="Montessori")
        )
        for c in announcement_rules.CURRICULA:
            self.assertIsNone(
                announcement_rules.validate_post("T", "B", curriculum=c)
            )

    def test_window_order(self):
        self.assertEqual(
            announcement_rules.validate_post(
                "T",
                "B",
                starts_at="2026-08-15 09:00:00",
                ends_at="2026-08-14 09:00:00",
            ),
            "ends_at must be after starts_at.",
        )
        # Equal bounds are an empty (never-active) window — refused too.
        self.assertIsNotNone(
            announcement_rules.validate_post(
                "T",
                "B",
                starts_at="2026-08-14 09:00:00",
                ends_at="2026-08-14 09:00:00",
            )
        )

    def test_unparseable_window_is_refused_on_create(self):
        # The read degrades garbage to "unset"; the CREATE gate refuses it —
        # an operator typo must fail loudly, not post an unbounded notice.
        self.assertEqual(
            announcement_rules.validate_post("T", "B", starts_at="soon"),
            "starts_at is not a valid date/time.",
        )
        self.assertEqual(
            announcement_rules.validate_post("T", "B", ends_at="later"),
            "ends_at is not a valid date/time.",
        )


if __name__ == "__main__":
    unittest.main()
