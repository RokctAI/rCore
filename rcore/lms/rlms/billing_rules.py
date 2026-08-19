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

"""Wallet-mediated subscription billing (product log #33) — frappe-free
pure module.

Owner's chain, verbatim intent: a payer partner takes over payment for
students → the system bills the partner and records the amount as CREDIT in
the partner's wallet → each student's subscription amount is DEDUCTED from
the partner's wallet and CREDITED to that student's wallet → the student's
wallet is then DEBITED for the subscription. Every hop is a wallet ledger
entry, so payment provenance (who funded whom) is auditable per student.

This module PLANS that chain as data — an ordered list of ledger hops the
API executes one-for-one against Wallet/Wallet History rows — and computes
the rate. Planning is pure and unit-tested; execution (doc writes, balance
mutation, rollback-on-throw via frappe's transaction) lives in api/billing.py.

Rates (#23/#30's fix, applied in the right place): the partner discount is
charged to the PAYER. A sponsor checkout charges the partner rate per
student; a student self-checkout charges the base rate unless that student
has a payer-capable partner link (the §1 'cheaper subscription' promise),
in which case the partner rate applies to the student's own charge.
"""

# Hop kinds, in the exact chain order the owner specified.
SPONSOR_WALLET_DEBIT = "sponsor_wallet_debit"
STUDENT_WALLET_CREDIT = "student_wallet_credit"
STUDENT_SUBSCRIPTION_DEBIT = "student_subscription_debit"


def charge_per_student(base_rate, partner_rate, has_payer_capable_partner):
    """The per-student subscription charge for one period. The partner rate
    applies whenever a payer-capable partner is linked — and it is the
    PAYER's charge in a sponsor checkout, never a student-side display
    trick (the #23 finding this replaces)."""
    return partner_rate if has_payer_capable_partner else base_rate


def plan_sponsor_checkout(sponsor, students, per_student_amount):
    """The ordered ledger hops for one sponsor checkout covering
    [students]. Three hops per student, per the decided chain — the sponsor
    wallet is debited per student (not once in bulk) so each student's
    funding line is individually auditable.

    Returns (total, hops); hops are dicts the executor writes verbatim:
    {kind, wallet_user, amount, counterparty, student}.
    """
    if per_student_amount <= 0:
        raise ValueError("per-student amount must be positive")
    if not students:
        raise ValueError("a sponsor checkout needs at least one student")
    seen = set()
    hops = []
    for student in students:
        if student in seen:
            raise ValueError(f"duplicate student in checkout: {student}")
        if student == sponsor:
            raise ValueError("a sponsor cannot sponsor themselves")
        seen.add(student)
        hops.append(
            {
                "kind": SPONSOR_WALLET_DEBIT,
                "wallet_user": sponsor,
                "amount": -per_student_amount,
                "counterparty": student,
                "student": student,
            }
        )
        hops.append(
            {
                "kind": STUDENT_WALLET_CREDIT,
                "wallet_user": student,
                "amount": per_student_amount,
                "counterparty": sponsor,
                "student": student,
            }
        )
        hops.append(
            {
                "kind": STUDENT_SUBSCRIPTION_DEBIT,
                "wallet_user": student,
                "amount": -per_student_amount,
                "counterparty": "subscription",
                "student": student,
            }
        )
    return per_student_amount * len(students), hops


def plan_student_checkout(student, amount):
    """A self-paying student's single hop: their own wallet debited for the
    subscription. Same hop vocabulary so the executor and the audit trail
    treat both flows identically."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    return amount, [
        {
            "kind": STUDENT_SUBSCRIPTION_DEBIT,
            "wallet_user": student,
            "amount": -amount,
            "counterparty": "subscription",
            "student": student,
        }
    ]


def sufficient_balance(balance, total):
    """Funds check the executor applies BEFORE writing any hop — the chain
    is all-or-nothing per checkout."""
    return balance >= total
