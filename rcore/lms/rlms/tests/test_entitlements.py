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

"""Product log #27's entitlement rules, pinned standalone (no frappe, no
site — `python -m unittest tests.test_entitlements`).

Loaded by file path rather than package import, matching
test_alert_rules.py: workspace python modules import through an `rcore`
placeholder and only resolve inside a composed app; entitlements.py is
deliberately frappe-free so this test runs anywhere python does."""

import importlib.util
import os
import unittest
from datetime import date

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "entitlements.py")
_spec = importlib.util.spec_from_file_location("rlms_entitlements", _MODULE_PATH)
entitlements = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(entitlements)


# A student subscribed through Gr 11 (2025), lapsed, resubscribed mid-Gr 12.
GR11_PERIOD = (date(2025, 1, 15), date(2025, 12, 15))
GR12_PERIOD = (date(2026, 6, 1), None)  # open-ended: currently active
PERIODS = [GR11_PERIOD, GR12_PERIOD]

TODAY = date(2026, 7, 28)


class TestSkillsRule(unittest.TestCase):
    def test_active_subscriber_gets_all_skills(self):
        self.assertTrue(entitlements.skills_entitled(PERIODS, TODAY))

    def test_lapsed_subscriber_gets_no_skills(self):
        # Only the Gr 11 period, long over: not an active subscriber today.
        self.assertFalse(entitlements.skills_entitled([GR11_PERIOD], TODAY))

    def test_never_subscribed_gets_nothing(self):
        self.assertFalse(entitlements.skills_entitled([], TODAY))


class TestBackCatalogRule(unittest.TestCase):
    def test_lesson_aired_during_covered_period_is_entitled(self):
        # Gr 11 lesson aired while the Gr 11 subscription was active: keeps
        # rewatch access ("subscribed in Gr 11 keeps the Gr 11 lessons").
        self.assertTrue(
            entitlements.lesson_entitled(PERIODS, date(2025, 8, 10), TODAY)
        )

    def test_no_retroactive_harvest_by_subscribing_late(self):
        # The exact scenario the owner named: skip paying in Gr 11, subscribe
        # in matric, try to harvest the Gr 11 back-catalog. Denied.
        only_gr12 = [GR12_PERIOD]
        self.assertFalse(
            entitlements.lesson_entitled(only_gr12, date(2025, 8, 10), TODAY)
        )

    def test_gap_between_periods_is_not_covered(self):
        # Lapsed Jan-May 2026: lessons aired in the gap stay locked even
        # though periods exist on both sides.
        self.assertFalse(
            entitlements.lesson_entitled(PERIODS, date(2026, 3, 1), TODAY)
        )

    def test_current_period_covers_current_content(self):
        self.assertTrue(
            entitlements.lesson_entitled(PERIODS, date(2026, 7, 20), TODAY)
        )


class TestVerdict(unittest.TestCase):
    def test_skill_with_active_subscription_allowed(self):
        self.assertEqual(
            entitlements.entitlement_verdict(PERIODS, None, TODAY, is_skill=True),
            "allowed",
        )

    def test_skill_without_active_subscription_needs_active(self):
        self.assertEqual(
            entitlements.entitlement_verdict([GR11_PERIOD], None, TODAY, is_skill=True),
            "needs_active",
        )

    def test_covered_lesson_allowed(self):
        self.assertEqual(
            entitlements.entitlement_verdict(
                PERIODS, date(2025, 8, 10), TODAY, is_skill=False
            ),
            "allowed",
        )

    def test_uncovered_lesson_for_active_subscriber_is_not_covered(self):
        # Active today, but the lesson predates every covered period: the
        # deny message must say "not covered", not "subscribe".
        self.assertEqual(
            entitlements.entitlement_verdict(
                [GR12_PERIOD], date(2025, 8, 10), TODAY, is_skill=False
            ),
            "not_covered",
        )

    def test_uncovered_lesson_for_lapsed_subscriber_needs_active(self):
        self.assertEqual(
            entitlements.entitlement_verdict(
                [], date(2025, 8, 10), TODAY, is_skill=False
            ),
            "needs_active",
        )

    def test_overlapping_duplicate_periods_cannot_widen_access(self):
        doubled = [GR11_PERIOD, GR11_PERIOD, GR12_PERIOD]
        self.assertFalse(
            entitlements.lesson_entitled(doubled, date(2026, 3, 1), TODAY)
        )


if __name__ == "__main__":
    unittest.main()
