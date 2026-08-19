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

"""Product log #29's maths-track exclusivity, pinned standalone.

Loaded by file path rather than package import, matching
test_alert_rules.py (workspace modules import through an `rcore`
placeholder; maths_track.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "maths_track.py")
_spec = importlib.util.spec_from_file_location("rlms_maths_track", _MODULE_PATH)
maths_track = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(maths_track)

CORE = maths_track.CORE
LITERACY = maths_track.LITERACY


class TestTrackDetection(unittest.TestCase):
    def test_factory_slugs_resolve(self):
        # The real content slugs: factory/lessons/curriculum/CAPS/…
        self.assertEqual(maths_track.track_of("maths"), CORE)
        self.assertEqual(maths_track.track_of("mathematical_literacy"), LITERACY)

    def test_literacy_wins_over_the_core_token_it_contains(self):
        # "Mathematical Literacy" contains a maths token; the literacy
        # reading must win or every lit student would look like core maths.
        self.assertEqual(maths_track.track_of("Mathematical Literacy"), LITERACY)
        self.assertEqual(maths_track.track_of("Maths Literacy"), LITERACY)
        self.assertEqual(maths_track.track_of("maths-literacy"), LITERACY)

    def test_agrees_with_the_client_badge_matcher(self):
        # lms_sdk MathTrackBadge.isLiteracy is a loose contains('literacy');
        # server detection must not disagree with what the badge shows.
        for subject in ("Mathematical Literacy", "MATHS LITERACY", "lit literacy"):
            self.assertEqual(maths_track.track_of(subject), LITERACY)

    def test_core_spellings(self):
        for subject in ("Maths", "Mathematics", "mathematics"):
            self.assertEqual(maths_track.track_of(subject), CORE)

    def test_non_maths_subjects_have_no_track(self):
        for subject in ("Geography", "physical_sciences", "Economics", "Accounting"):
            self.assertIsNone(maths_track.track_of(subject))

    def test_blank_input_is_not_a_track(self):
        self.assertIsNone(maths_track.track_of(None))
        self.assertIsNone(maths_track.track_of(""))
        self.assertIsNone(maths_track.track_of("   "))


class TestExclusivity(unittest.TestCase):
    def test_core_blocks_literacy(self):
        # The rule: never both.
        self.assertEqual(
            maths_track.conflicting_track(["maths"], "mathematical_literacy"), CORE
        )

    def test_literacy_blocks_core(self):
        self.assertEqual(
            maths_track.conflicting_track(["mathematical_literacy"], "maths"), LITERACY
        )

    def test_same_track_again_is_allowed(self):
        # Re-enrolling in a track already held is idempotent, not a clash.
        self.assertIsNone(maths_track.conflicting_track(["maths"], "maths"))
        self.assertIsNone(
            maths_track.conflicting_track(
                ["mathematical_literacy"], "Mathematical Literacy"
            )
        )

    def test_non_maths_never_conflicts_either_way(self):
        self.assertIsNone(maths_track.conflicting_track(["maths"], "Geography"))
        self.assertIsNone(
            maths_track.conflicting_track(["Geography", "Economics"], "maths")
        )

    def test_conflict_found_among_several_held_subjects(self):
        self.assertEqual(
            maths_track.conflicting_track(
                ["Geography", "maths", "Economics"], "mathematical_literacy"
            ),
            CORE,
        )

    def test_no_subjects_held_means_free_choice(self):
        self.assertIsNone(maths_track.conflicting_track([], "maths"))
        self.assertIsNone(maths_track.conflicting_track(None, "mathematical_literacy"))

    def test_label_is_human_readable(self):
        self.assertEqual(maths_track.track_label(LITERACY), "Mathematical Literacy")
        self.assertEqual(maths_track.track_label(CORE), "Mathematics")


if __name__ == "__main__":
    unittest.main()
