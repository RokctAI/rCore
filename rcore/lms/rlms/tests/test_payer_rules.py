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

"""Product log #33's payer-capability rule, pinned standalone.

Loaded by file path rather than package import, matching
test_alert_rules.py (workspace modules import through an `rcore`
placeholder; payer_rules.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "payer_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_payer_rules", _MODULE_PATH)
payer_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(payer_rules)


class TestPayerCapability(unittest.TestCase):
    def test_teacher_cannot_pay(self):
        # The owner's explicit rule: a TEACHER partner cannot pay for a
        # student.
        self.assertFalse(payer_rules.can_pay("Teacher"))

    def test_sponsor_can_pay(self):
        # The new type exists specifically as a payer-capable partner.
        self.assertTrue(payer_rules.can_pay("Sponsor"))

    def test_parent_and_guardian_stay_payer_capable(self):
        # P3.1's delegated billing was designed around parents paying.
        self.assertTrue(payer_rules.can_pay("Parent"))
        self.assertTrue(payer_rules.can_pay("Guardian"))

    def test_sibling_and_mentor_stay_payer_capable(self):
        # Documented default: the decision excludes teachers rather than
        # enumerating payers; tighten payer_rules._NON_PAYER to change.
        self.assertTrue(payer_rules.can_pay("Sibling"))
        self.assertTrue(payer_rules.can_pay("Mentor"))

    def test_stored_label_casing_is_tolerated(self):
        self.assertFalse(payer_rules.can_pay("teacher"))
        self.assertTrue(payer_rules.can_pay("sponsor"))

    def test_unknown_or_blank_never_gains_capability(self):
        self.assertFalse(payer_rules.can_pay(None))
        self.assertFalse(payer_rules.can_pay(""))
        self.assertFalse(payer_rules.can_pay("Billionaire"))


if __name__ == "__main__":
    unittest.main()
