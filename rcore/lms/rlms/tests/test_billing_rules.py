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

"""Product log #33's wallet-billing chain planner, pinned standalone.

Loaded by file path rather than package import, matching
test_alert_rules.py (workspace modules import through an `rcore`
placeholder; billing_rules.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "billing_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_billing_rules", _MODULE_PATH)
billing_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(billing_rules)


class TestChargeRate(unittest.TestCase):
    # The #23/#30 fix: the discount belongs to whoever pays, decided here.
    def test_payer_capable_partner_gets_partner_rate(self):
        self.assertEqual(billing_rules.charge_per_student(299, 249, True), 249)

    def test_no_payer_capable_partner_means_base_rate(self):
        self.assertEqual(billing_rules.charge_per_student(299, 249, False), 299)


class TestSponsorCheckoutPlan(unittest.TestCase):
    def test_chain_order_matches_the_decided_design_per_student(self):
        # sponsor debit -> student credit -> student subscription debit,
        # for EACH student, in order — every hop a ledger entry.
        total, hops = billing_rules.plan_sponsor_checkout(
            "sponsor@x.com", ["a@x.com", "b@x.com"], 249
        )
        self.assertEqual(total, 498)
        self.assertEqual(
            [h["kind"] for h in hops],
            [
                billing_rules.SPONSOR_WALLET_DEBIT,
                billing_rules.STUDENT_WALLET_CREDIT,
                billing_rules.STUDENT_SUBSCRIPTION_DEBIT,
            ]
            * 2,
        )

    def test_every_hop_carries_the_student_for_provenance(self):
        _, hops = billing_rules.plan_sponsor_checkout(
            "sponsor@x.com", ["a@x.com"], 249
        )
        self.assertTrue(all(h["student"] == "a@x.com" for h in hops))
        # The transfer hops name each other as counterparties — who funded
        # whom is readable from the ledger alone.
        self.assertEqual(hops[0]["counterparty"], "a@x.com")
        self.assertEqual(hops[1]["counterparty"], "sponsor@x.com")

    def test_amounts_balance_per_student(self):
        _, hops = billing_rules.plan_sponsor_checkout(
            "sponsor@x.com", ["a@x.com"], 249
        )
        self.assertEqual(hops[0]["amount"], -249)  # sponsor pays out
        self.assertEqual(hops[1]["amount"], 249)   # student receives
        self.assertEqual(hops[2]["amount"], -249)  # subscription consumes

    def test_self_sponsoring_refused(self):
        with self.assertRaises(ValueError):
            billing_rules.plan_sponsor_checkout("x@x.com", ["x@x.com"], 249)

    def test_duplicate_students_refused(self):
        with self.assertRaises(ValueError):
            billing_rules.plan_sponsor_checkout(
                "s@x.com", ["a@x.com", "a@x.com"], 249
            )

    def test_empty_or_free_checkouts_refused(self):
        with self.assertRaises(ValueError):
            billing_rules.plan_sponsor_checkout("s@x.com", [], 249)
        with self.assertRaises(ValueError):
            billing_rules.plan_sponsor_checkout("s@x.com", ["a@x.com"], 0)


class TestStudentCheckoutPlan(unittest.TestCase):
    def test_single_debit_hop(self):
        total, hops = billing_rules.plan_student_checkout("a@x.com", 299)
        self.assertEqual(total, 299)
        self.assertEqual(len(hops), 1)
        self.assertEqual(hops[0]["kind"], billing_rules.STUDENT_SUBSCRIPTION_DEBIT)
        self.assertEqual(hops[0]["amount"], -299)


class TestFunds(unittest.TestCase):
    def test_all_or_nothing_funds_check(self):
        self.assertTrue(billing_rules.sufficient_balance(500, 498))
        self.assertFalse(billing_rules.sufficient_balance(497.99, 498))


if __name__ == "__main__":
    unittest.main()
