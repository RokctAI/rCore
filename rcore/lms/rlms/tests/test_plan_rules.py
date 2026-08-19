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

"""Server-configurable subscription plans (owner instruction 2026-08-13),
pinned standalone: the documented seed catalog, the per-kind charge
decision, and the one-off programme's upcoming-window rule.

Loaded by file path rather than package import, matching
test_billing_rules.py (workspace modules import through an `rcore`
placeholder; plan_rules.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest
from datetime import date

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "plan_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_plan_rules", _MODULE_PATH)
plan_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_rules)


class TestDefaultPlans(unittest.TestCase):
    """The seeds are the DOCUMENTED rates and nothing else — editable
    records once landed; these tests pin what ships, not what it may be
    edited to."""

    def _by_key(self, key):
        for plan in plan_rules.default_plans():
            if plan["plan_key"] == key:
                return plan
        raise AssertionError(f"no seed plan {key}")

    def test_monthly_seed_is_the_documented_299(self):
        plan = self._by_key("standard-monthly")
        self.assertEqual(plan["price"], 299)
        self.assertEqual(plan["months"], 1)
        self.assertEqual(plan["kind"], plan_rules.KIND_RECURRING)
        self.assertEqual(plan["active"], 1)

    def test_yearly_seed_is_the_documented_2990(self):
        # 10 x standard, two months free — NOT the R2,490 partner-rate
        # derivation the tiers proposal §2 documents as a bug.
        plan = self._by_key("standard-yearly")
        self.assertEqual(plan["price"], 2990)
        self.assertEqual(plan["months"], 12)
        self.assertEqual(plan["kind"], plan_rules.KIND_RECURRING)

    def test_holiday_seed_is_the_documented_449_one_off(self):
        plan = self._by_key("holiday-programme")
        self.assertEqual(plan["price"], 449)
        self.assertEqual(plan["months"], 0)
        self.assertEqual(plan["kind"], plan_rules.KIND_ONE_OFF_PROGRAMME)

    def test_holiday_seed_hardcodes_no_window(self):
        # The upcoming programme window is the owner's data to configure on
        # the record — a seed must never bake in a specific holiday.
        plan = self._by_key("holiday-programme")
        self.assertNotIn("window_start", plan)
        self.assertNotIn("window_end", plan)

    def test_per_lesson_seed_is_inactive_with_no_invented_price(self):
        # No document defines a per-lesson rate, and #47 forbids invented
        # numbers: the owner prices and activates the record.
        plan = self._by_key("per-lesson")
        self.assertEqual(plan["active"], 0)
        self.assertEqual(plan["price"], 0)
        self.assertEqual(plan["months"], 0)
        self.assertEqual(plan["kind"], plan_rules.KIND_PER_LESSON)

    def test_all_seed_kinds_are_known(self):
        for plan in plan_rules.default_plans():
            self.assertIn(plan["kind"], plan_rules.KINDS)


class TestChargeForPlan(unittest.TestCase):
    def test_monthly_plan_with_partner_charges_the_partner_rate(self):
        # #23/#30 unchanged: the per-student MONTHLY partner rate (LMS
        # Settings) substitutes on a monthly plan for whoever pays.
        amount, kind = plan_rules.charge_for_plan(
            plan_rules.KIND_RECURRING, 299, 1, 249, True
        )
        self.assertEqual(amount, 249)
        self.assertEqual(kind, plan_rules.RATE_KIND_PARTNER)

    def test_monthly_plan_without_partner_charges_the_plan_price(self):
        amount, kind = plan_rules.charge_for_plan(
            plan_rules.KIND_RECURRING, 299, 1, 249, False
        )
        self.assertEqual(amount, 299)
        self.assertEqual(kind, plan_rules.RATE_KIND_PLAN)

    def test_partner_rate_does_not_stack_on_the_yearly_plan(self):
        # The annual two-months-free already buys the commitment; deriving
        # yearly off the partner rate is the documented R2,490 bug.
        amount, kind = plan_rules.charge_for_plan(
            plan_rules.KIND_RECURRING, 2990, 12, 249, True
        )
        self.assertEqual(amount, 2990)
        self.assertEqual(kind, plan_rules.RATE_KIND_PLAN)

    def test_repriced_monthly_plan_still_defers_to_the_partner_rate(self):
        # Config is the point: the owner reprices the record, the partner
        # mechanic stays a settings-owned monthly rate, not price minus 50.
        amount, kind = plan_rules.charge_for_plan(
            plan_rules.KIND_RECURRING, 349, 1, 249, True
        )
        self.assertEqual(amount, 249)
        self.assertEqual(kind, plan_rules.RATE_KIND_PARTNER)

    def test_one_off_programme_charges_its_own_price_partner_or_not(self):
        # The Holiday Programme is a separate premium product (business doc
        # §2) — the partner monthly rate has nothing to substitute into.
        for discounted in (True, False):
            amount, kind = plan_rules.charge_for_plan(
                plan_rules.KIND_ONE_OFF_PROGRAMME, 449, 0, 249, discounted
            )
            self.assertEqual(amount, 449)
            self.assertEqual(kind, plan_rules.RATE_KIND_PLAN)

    def test_per_lesson_charges_its_own_price_as_a_lesson_rate(self):
        amount, kind = plan_rules.charge_for_plan(
            plan_rules.KIND_PER_LESSON, 75, 0, 249, True
        )
        self.assertEqual(amount, 75)
        self.assertEqual(kind, plan_rules.RATE_KIND_LESSON)

    def test_unpriced_plan_is_refused_not_defaulted(self):
        # #47: no invented numbers — the seeded per-lesson plan has no
        # documented price, so checking it out must raise, never guess.
        with self.assertRaises(ValueError):
            plan_rules.charge_for_plan(
                plan_rules.KIND_PER_LESSON, 0, 0, 249, False
            )

    def test_recurring_plan_needs_at_least_one_month(self):
        with self.assertRaises(ValueError):
            plan_rules.charge_for_plan(plan_rules.KIND_RECURRING, 299, 0, 249, False)

    def test_one_off_kinds_must_have_zero_months(self):
        with self.assertRaises(ValueError):
            plan_rules.charge_for_plan(
                plan_rules.KIND_ONE_OFF_PROGRAMME, 449, 1, 249, False
            )

    def test_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            plan_rules.charge_for_plan("Timeshare", 100, 0, 249, False)


class TestUpcomingWindow(unittest.TestCase):
    """The owner's rule: a one-off purchase grants the UPCOMING programme
    window at time of purchase — never an arbitrary or past one."""

    today = date(2026, 8, 13)

    def test_future_window_is_the_upcoming_one(self):
        window = plan_rules.upcoming_window(
            date(2026, 12, 10), date(2027, 1, 10), self.today
        )
        self.assertEqual(window, (date(2026, 12, 10), date(2027, 1, 10)))

    def test_currently_running_window_is_still_buyable(self):
        # Buying mid-programme joins the programme under way — that IS the
        # upcoming/current window, not a past one.
        window = plan_rules.upcoming_window(
            date(2026, 8, 1), date(2026, 8, 31), self.today
        )
        self.assertEqual(window, (date(2026, 8, 1), date(2026, 8, 31)))

    def test_a_finished_window_is_not_buyable(self):
        self.assertIsNone(
            plan_rules.upcoming_window(
                date(2026, 6, 1), date(2026, 7, 15), self.today
            )
        )

    def test_unconfigured_window_means_nothing_to_buy(self):
        self.assertIsNone(plan_rules.upcoming_window(None, None, self.today))
        self.assertIsNone(
            plan_rules.upcoming_window(date(2026, 12, 10), None, self.today)
        )

    def test_inverted_window_raises_rather_than_grants(self):
        with self.assertRaises(ValueError):
            plan_rules.upcoming_window(
                date(2026, 12, 10), date(2026, 12, 1), self.today
            )


class TestAssistantChatGate(unittest.TestCase):
    """The in-lesson chat assistant's plan gate (owner's rule 2026-08-14):
    an explicit 0 on the governing plan disables; everything unresolvable
    fails OPEN so nothing breaks for existing students."""

    today = date(2026, 8, 14)

    def test_explicit_off_disables(self):
        self.assertFalse(plan_rules.allows_assistant_chat(0))
        self.assertFalse(plan_rules.allows_assistant_chat("0"))

    def test_explicit_on_allows(self):
        self.assertTrue(plan_rules.allows_assistant_chat(1))
        self.assertTrue(plan_rules.allows_assistant_chat("1"))

    def test_unresolvable_flag_fails_open(self):
        self.assertTrue(plan_rules.allows_assistant_chat(None))
        self.assertTrue(plan_rules.allows_assistant_chat("weird"))

    def test_newest_covering_record_with_a_flag_decides(self):
        records = [
            {  # newest: covers today, plan says no chat
                "assistant_chat": 0,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
            {  # older covering record would have allowed
                "assistant_chat": 1,
                "period_start": date(2026, 7, 1),
                "period_end": date(2026, 12, 31),
            },
        ]
        self.assertFalse(
            plan_rules.assistant_chat_from_records(records, self.today)
        )

    def test_expired_and_future_records_do_not_govern(self):
        records = [
            {  # future coverage — not governing today
                "assistant_chat": 0,
                "period_start": date(2026, 9, 1),
                "period_end": date(2026, 9, 30),
            },
            {  # expired coverage — not governing today
                "assistant_chat": 0,
                "period_start": date(2026, 1, 1),
                "period_end": date(2026, 1, 31),
            },
        ]
        self.assertTrue(
            plan_rules.assistant_chat_from_records(records, self.today)
        )

    def test_legacy_records_without_plan_info_fail_open(self):
        records = [
            {  # legacy months x rate checkout: no plan link, no flag
                "assistant_chat": None,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
        ]
        self.assertTrue(
            plan_rules.assistant_chat_from_records(records, self.today)
        )

    def test_no_records_fail_open(self):
        self.assertTrue(plan_rules.assistant_chat_from_records([], self.today))
        self.assertTrue(
            plan_rules.assistant_chat_from_records(None, self.today)
        )


class TestHolidayAccess(unittest.TestCase):
    """Plan-scoped Holiday Programme access (owner's rule 2026-08-14:
    "other plans they give access to part of the program like a week while
    others may give it as a whole"): the governing plan's level narrows;
    everything unresolvable fails OPEN to Full."""

    today = date(2026, 8, 14)

    def test_known_levels_pass_through(self):
        for level in plan_rules.HOLIDAY_ACCESS_LEVELS:
            self.assertEqual(plan_rules.holiday_access_level(level), level)

    def test_unresolvable_level_fails_open_to_full(self):
        for value in (None, "", "weird", 0, 1):
            self.assertEqual(
                plan_rules.holiday_access_level(value),
                plan_rules.HOLIDAY_ACCESS_FULL,
            )

    def test_newest_covering_record_with_a_level_decides(self):
        records = [
            {  # newest: covers today, plan narrows to the first week
                "holiday_access": "First Week",
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
            {  # older covering record would have granted the whole window
                "holiday_access": "Full",
                "period_start": date(2026, 7, 1),
                "period_end": date(2026, 12, 31),
            },
        ]
        self.assertEqual(
            plan_rules.holiday_access_from_records(records, self.today),
            plan_rules.HOLIDAY_ACCESS_FIRST_WEEK,
        )

    def test_explicit_none_shuts_the_programme(self):
        records = [
            {
                "holiday_access": "None",
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
        ]
        self.assertEqual(
            plan_rules.holiday_access_from_records(records, self.today),
            plan_rules.HOLIDAY_ACCESS_NONE,
        )

    def test_one_off_programme_purchase_is_always_full_for_its_window(self):
        records = [
            {  # the standalone R449 checkout: buying the programme outright
                # IS buying the whole programme, whatever the record says
                "holiday_access": "First Week",
                "kind": plan_rules.KIND_ONE_OFF_PROGRAMME,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
        ]
        self.assertEqual(
            plan_rules.holiday_access_from_records(records, self.today),
            plan_rules.HOLIDAY_ACCESS_FULL,
        )

    def test_expired_and_future_records_do_not_govern(self):
        records = [
            {  # future coverage — not governing today
                "holiday_access": "None",
                "period_start": date(2026, 9, 1),
                "period_end": date(2026, 9, 30),
            },
            {  # expired coverage — not governing today
                "holiday_access": "First Week",
                "period_start": date(2026, 1, 1),
                "period_end": date(2026, 1, 31),
            },
        ]
        self.assertEqual(
            plan_rules.holiday_access_from_records(records, self.today),
            plan_rules.HOLIDAY_ACCESS_FULL,
        )

    def test_legacy_records_without_plan_info_fail_open(self):
        records = [
            {  # legacy months x rate checkout: no plan link, no level
                "holiday_access": None,
                "period_start": date(2026, 8, 1),
                "period_end": date(2026, 8, 31),
            },
        ]
        self.assertEqual(
            plan_rules.holiday_access_from_records(records, self.today),
            plan_rules.HOLIDAY_ACCESS_FULL,
        )

    def test_no_records_fail_open(self):
        for records in ([], None):
            self.assertEqual(
                plan_rules.holiday_access_from_records(records, self.today),
                plan_rules.HOLIDAY_ACCESS_FULL,
            )


if __name__ == "__main__":
    unittest.main()
