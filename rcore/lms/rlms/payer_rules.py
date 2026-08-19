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

"""Which partner relationships may take on payment responsibility for a
student (product log #33) — frappe-free pure module.

The owner's decision names the two poles explicitly: a TEACHER partner
cannot pay for a student; the new SPONSOR type exists specifically as a
payer-capable partner. Every other relationship (parent, guardian, sibling,
mentor) stays payer-capable — the P3.1 delegated-billing design was built
around parents paying, and the owner's rule excludes teachers rather than
enumerating payers. Tighten the allowlist here if that ever changes; the
API enforces whatever this module says.

Values are the LMS Partner Link `relationship` Select labels (stored form).
"""

# The stored relationship labels, as written by _relationship_label.
PARENT = "Parent"
GUARDIAN = "Guardian"
SIBLING = "Sibling"
TEACHER = "Teacher"
MENTOR = "Mentor"
SPONSOR = "Sponsor"

ALL_RELATIONSHIPS = (PARENT, GUARDIAN, SIBLING, TEACHER, MENTOR, SPONSOR)

# Deny-list by decision: teachers see progress, they do not hold the purse.
_NON_PAYER = frozenset({TEACHER})


def can_pay(relationship):
    """Whether a partner with [relationship] may assume billing
    responsibility for a linked student. Unknown/blank values are refused —
    payment capability is never granted by default to a value this module
    has not seen."""
    if not relationship:
        return False
    label = str(relationship).strip().title()
    if label not in ALL_RELATIONSHIPS:
        return False
    return label not in _NON_PAYER
