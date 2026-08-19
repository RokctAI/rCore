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

"""Subscription-period entitlement rules (product log #27) — frappe-free
pure module.

The decided rule, verbatim from the log:
- **Skills: every paying (actively subscribed) student, all grades' skills,
  always.** The refresher is the pedagogical safety net.
- **Full lessons: only from periods the student's subscription was active.**
  Subscribing in Gr 12 does NOT retroactively unlock the Gr 11 back-catalog
  ("they will skip paying unless giving them during subscription active").
- Attendance history gates nothing — it only personalises framing.

A "period" here is a (start_date, end_date) pair of datetime.date;
end_date None means the period is still open (current subscription).
Overlapping or unordered periods are fine — every rule is a simple
containment scan, so duplicates can't widen access beyond their real range.

API files own the I/O (reading LMS Subscription Period rows, resolving a
lesson's broadcast date) and call these for the judgement.
"""

from datetime import date
from typing import Optional, Sequence, Tuple

Period = Tuple[date, Optional[date]]


def _contains(period: Period, day: date) -> bool:
    start, end = period
    if day < start:
        return False
    return end is None or day <= end


def active_on(periods: Sequence[Period], day: date) -> bool:
    """Whether any subscription period covers [day]."""
    return any(_contains(p, day) for p in periods)


def skills_entitled(periods: Sequence[Period], today: date) -> bool:
    """Skills shelf access: an ACTIVE subscription, full stop — every
    grade's skills, no history requirement."""
    return active_on(periods, today)


def lesson_entitled(
    periods: Sequence[Period], broadcast_day: date, today: date
) -> bool:
    """Full-lesson (back-catalog) access: the student's subscription must
    have been active WHEN THE LESSON AIRED. An active-today subscription
    additionally covers today's/future content (broadcast_day >= the start
    of a currently-active period is by definition contained once it airs
    inside that period) — but never reaches back before the period began.
    """
    return active_on(periods, broadcast_day)


def entitlement_verdict(
    periods: Sequence[Period],
    broadcast_day: Optional[date],
    today: date,
    is_skill: bool,
) -> str:
    """One verdict for a content request:

    - 'allowed'        — serve it.
    - 'needs_active'   — a skill (or undated on-demand content) requested
                         without an active subscription.
    - 'not_covered'    — a dated full lesson from a period the student was
                         not subscribed in (the #27 back-catalog rule).
    """
    if is_skill or broadcast_day is None:
        # Skills and undated on-demand content follow the active-now rule.
        return "allowed" if skills_entitled(periods, today) else "needs_active"
    if lesson_entitled(periods, broadcast_day, today):
        return "allowed"
    # Distinguish "just not subscribed at all" from "subscribed now but the
    # lesson predates every covered period" — both deny, one message each.
    return "needs_active" if not active_on(periods, today) else "not_covered"
