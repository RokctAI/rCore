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

"""Tutor-catalog publish/read rules, pinned standalone (no frappe, no site —
`python -m unittest tests.test_tutor_rules`).

Loaded by file path rather than package import, matching test_time_gates.py:
workspace python modules import through an `rcore` placeholder and only
resolve inside a composed app; tutor_rules.py is deliberately frappe-free so
this test runs anywhere python does."""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "tutor_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_tutor_rules", _MODULE_PATH)
tutor_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tutor_rules)


def _entry(**overrides):
    base = {
        "id": "tutor_001",
        "display_name": "Sifiso Zulu",
        "subject": "Mathematics",
        "grade": 12,
        "grades": [10, 11, 12],
        "role": "tutor",
        "style_tag": "Strict, fast paced",
    }
    base.update(overrides)
    return base


class TestValidateCatalog(unittest.TestCase):
    def test_valid_catalog_accepted(self):
        tutors = tutor_rules.validate_catalog({"tutors": [_entry()]})
        self.assertEqual(len(tutors), 1)

    def test_absent_rating_and_enrolled_count_accepted(self):
        # The "no fabricated data" rule: today rlms has no rating surface,
        # so the honest catalog omits both keys entirely — and null is
        # equivalent to omitted.
        tutor_rules.validate_catalog({"tutors": [_entry()]})
        tutor_rules.validate_catalog(
            {"tutors": [_entry(rating=None, enrolled_count=None)]}
        )

    def test_real_rating_and_enrolled_count_accepted(self):
        tutor_rules.validate_catalog(
            {"tutors": [_entry(rating=4.5, enrolled_count=120)]}
        )
        tutor_rules.validate_catalog({"tutors": [_entry(rating=0)]})
        tutor_rules.validate_catalog({"tutors": [_entry(rating=5)]})
        tutor_rules.validate_catalog({"tutors": [_entry(enrolled_count=0)]})

    def test_non_dict_rejected(self):
        for bad in (None, [], "tutors", 7):
            with self.assertRaises(tutor_rules.CatalogError):
                tutor_rules.validate_catalog(bad)

    def test_missing_tutors_list_rejected(self):
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({})
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({"tutors": {"tutor_001": {}}})

    def test_entry_missing_id_rejected(self):
        entry = _entry()
        del entry["id"]
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({"tutors": [entry]})
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({"tutors": [_entry(id="  ")]})

    def test_entry_missing_name_rejected(self):
        entry = _entry()
        del entry["display_name"]
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({"tutors": [entry]})

    def test_name_key_accepted_as_display_name_fallback(self):
        # TutorProfile.fromJson reads display_name ?? name — the validator
        # accepts the same fallback.
        entry = _entry()
        del entry["display_name"]
        entry["name"] = "Sifiso Zulu"
        tutor_rules.validate_catalog({"tutors": [entry]})

    def test_non_dict_entry_rejected(self):
        with self.assertRaises(tutor_rules.CatalogError):
            tutor_rules.validate_catalog({"tutors": ["tutor_001"]})

    def test_out_of_range_rating_rejected(self):
        for bad in (-0.1, 5.1, 6, "4.5", True):
            with self.assertRaises(tutor_rules.CatalogError):
                tutor_rules.validate_catalog({"tutors": [_entry(rating=bad)]})

    def test_bad_enrolled_count_rejected(self):
        for bad in (-1, 2.5, "120", True):
            with self.assertRaises(tutor_rules.CatalogError):
                tutor_rules.validate_catalog(
                    {"tutors": [_entry(enrolled_count=bad)]}
                )

    def test_unknown_keys_pass_through(self):
        tutors = tutor_rules.validate_catalog(
            {"tutors": [_entry(intro_video_ref=None, future_field="kept")]}
        )
        self.assertEqual(tutors[0]["future_field"], "kept")


class TestFilterByGrade(unittest.TestCase):
    # Mirrors SeededTutorCatalog.getTutors: match on `grades` membership OR
    # the primary `grade`; grade None returns the whole team.
    team = [
        _entry(id="tutor_001", grades=[10, 11, 12], grade=12),
        _entry(id="assist_010", display_name="Amahle", grades=[], grade=10),
        _entry(id="assist_011", display_name="Karabo", grades=[11], grade=11),
    ]

    def test_none_returns_all(self):
        self.assertEqual(len(tutor_rules.filter_by_grade(self.team, None)), 3)

    def test_zero_treated_as_unfiltered(self):
        # frappe.utils.cint turns absent/invalid grade params into 0.
        self.assertEqual(len(tutor_rules.filter_by_grade(self.team, 0)), 3)

    def test_grades_membership_matches(self):
        kept = tutor_rules.filter_by_grade(self.team, 11)
        self.assertEqual([e["id"] for e in kept], ["tutor_001", "assist_011"])

    def test_primary_grade_matches_when_grades_empty(self):
        kept = tutor_rules.filter_by_grade(self.team, 10)
        self.assertEqual([e["id"] for e in kept], ["tutor_001", "assist_010"])

    def test_unmatched_grade_returns_empty(self):
        self.assertEqual(tutor_rules.filter_by_grade(self.team, 8), [])


if __name__ == "__main__":
    unittest.main()
