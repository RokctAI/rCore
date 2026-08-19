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

"""Server-configurable subscription plans — frappe-free pure module.

The owner's instruction (2026-08-13): "sub plans should be configurable."
Plans stop being client constants and become LMS Plan records the backend
reads at catalog and checkout time. This module owns the frappe-free half:
the seed catalog (the documented rates, editable once landed as records),
the charge decision per plan kind, and the one-off programme's
upcoming-window resolution. api/billing.py executes against real records.

Three plan kinds, per the owner's clarifications:

- Recurring        — billed for a number of months (monthly, yearly).
- One-Off Programme — bought once for the UPCOMING programme window at the
                      time of purchase (the Holiday Programme: business doc
                      §2, a separate premium product). The window itself is
                      configurable data on the plan record, never a
                      hardcoded holiday.
- Per Lesson       — "you attend a lesson you are required to pay": a
                      once-off charge for ONE lesson, linked to the lesson
                      being attended. No subscription period; the paid
                      lesson itself is what the purchase grants.

Partner-rate reconciliation (business doc §Plans; decisions #23/#30/#34):
the partner rate is a PER-STUDENT MONTHLY rate distinct from the retail
catalog, charged to whoever actually pays. So it substitutes for a MONTHLY
recurring plan's price. It does not stack on the yearly plan (whose
two-months-free already buys the commitment — the R2,490 bug the tiers
proposal §2 documents came from deriving yearly off the partner rate), and
one-off/per-lesson purchases are separate products at their own price.
"""

KIND_RECURRING = "Recurring"
KIND_ONE_OFF_PROGRAMME = "One-Off Programme"
KIND_PER_LESSON = "Per Lesson"

KINDS = (KIND_RECURRING, KIND_ONE_OFF_PROGRAMME, KIND_PER_LESSON)

# rate_kind values a plan-priced charge lands under on LMS Billing Record
# (extending the existing Base/Partner pair honestly): 'Plan' = the plan's
# own catalog price; 'Lesson' = a per-lesson once-off; 'Partner' keeps its
# meaning (the per-student monthly partner rate applied).
RATE_KIND_PARTNER = "Partner"
RATE_KIND_PLAN = "Plan"
RATE_KIND_LESSON = "Lesson"


def default_plans():
    """The seed catalog, from the DOCUMENTED rates only (business doc
    §Plans + tiers proposal legend: R299 monthly, R2,990 yearly two months
    free, R449 Holiday Programme one-off). Inserted once when no LMS Plan
    records exist; after that the records are the source of truth and the
    owner edits them freely — configurability is the point.

    The per-lesson plan is seeded INACTIVE with no price: no document
    defines a per-lesson rate, and decision #47 forbids invented numbers —
    the owner sets the price on the record and activates it.

    The holiday seed ships with NO window dates — the upcoming programme
    window is the owner's data to set on the record, never a hardcoded
    holiday; checkout refuses honestly until a window is configured.
    """
    return [
        {
            "plan_key": "standard-monthly",
            "title": "Full Access",
            "description": (
                "Every live lesson, recording and skill review. "
                "Cancel anytime. R50 off with an accountability partner."
            ),
            "kind": KIND_RECURRING,
            "price": 299,
            "months": 1,
            "active": 1,
            "sort_order": 10,
            "holiday_access": "First Week",
        },
        {
            "plan_key": "standard-yearly",
            "title": "Full Access",
            "description": (
                "Every live lesson, recording and skill review — "
                "two months free, billed once a year."
            ),
            "kind": KIND_RECURRING,
            "price": 2990,
            "months": 12,
            "active": 1,
            "sort_order": 20,
        },
        {
            "plan_key": "holiday-programme",
            "title": "Holiday Programme",
            "description": (
                "The full holiday catch-up programme only — live revision "
                "sessions and their recordings for the school holidays. "
                "No year-round subscription."
            ),
            "kind": KIND_ONE_OFF_PROGRAMME,
            "price": 449,
            "months": 0,
            "active": 1,
            "sort_order": 30,
            "window_label": "School holiday programme",
        },
        {
            "plan_key": "per-lesson",
            "title": "Pay Per Lesson",
            "description": (
                "Pay once for a single lesson you attend — no subscription."
            ),
            "kind": KIND_PER_LESSON,
            "price": 0,
            "months": 0,
            "active": 0,
            "sort_order": 40,
        },
    ]


def charge_for_plan(kind, price, months, partner_rate, has_payer_capable_partner):
    """The (amount, rate_kind) one plan purchase charges per student.

    - A MONTHLY recurring plan with a payer-capable partner charges the
      per-student monthly partner rate (LMS Settings) instead of the plan
      price — the #23/#30 rule, unchanged: the discount belongs to the
      PAYER, and it is a monthly rate, not a percentage off any price.
    - Every other case charges the plan record's own price: yearly plans
      (no stacking on two-months-free), one-off programmes and per-lesson
      purchases (separate products, not subscriptions).

    Raises ValueError on an unpriced or malformed plan — the API layer
    turns that into an honest refusal, never an invented number (#47).
    """
    if kind not in KINDS:
        raise ValueError(f"unknown plan kind: {kind}")
    if kind == KIND_RECURRING:
        if months < 1:
            raise ValueError("a recurring plan needs at least one month")
        if has_payer_capable_partner and months == 1 and partner_rate:
            return float(partner_rate), RATE_KIND_PARTNER
    else:
        if months != 0:
            raise ValueError(f"a {kind} plan is one-off; months must be 0")
    if not price or price <= 0:
        raise ValueError("this plan has no price configured")
    return float(price), (
        RATE_KIND_LESSON if kind == KIND_PER_LESSON else RATE_KIND_PLAN
    )


def upcoming_window(window_start, window_end, today):
    """The programme window a one-off purchase made [today] buys into, or
    None when none is announced (owner's rule: a one-off purchase grants
    the UPCOMING programme — the next window at time of purchase, never an
    arbitrary or past one).

    A window still in the future, or currently running, is the upcoming
    one; a window that already ended is not buyable — the next programme
    hasn't been configured yet, so the purchase must be refused rather
    than granted against stale dates.
    """
    if not window_start or not window_end:
        return None
    if window_end < window_start:
        raise ValueError("programme window cannot end before it starts")
    if window_end < today:
        return None
    return (window_start, window_end)


def allows_assistant_chat(flag):
    """The plan gate for the in-lesson chat assistant (owner's rule,
    2026-08-14: "if your subscription doesnt allow you the chat will be
    disabled").

    [flag] is an LMS Plan `assistant_chat` value (0/1). None means no plan
    info was resolvable — a legacy record without a plan link, a
    pre-migration row, or no billing record at all — and ALLOWS: the flag
    defaults ON, so nothing switches off for existing students until the
    owner configures plans otherwise. Only an explicit 0 disables.
    """
    if flag is None:
        return True
    try:
        return bool(int(flag))
    except (TypeError, ValueError):
        return True


HOLIDAY_ACCESS_FULL = "Full"
HOLIDAY_ACCESS_FIRST_WEEK = "First Week"
HOLIDAY_ACCESS_NONE = "None"

HOLIDAY_ACCESS_LEVELS = (
    HOLIDAY_ACCESS_FULL,
    HOLIDAY_ACCESS_FIRST_WEEK,
    HOLIDAY_ACCESS_NONE,
)


def holiday_access_level(value):
    """Normalize an LMS Plan `holiday_access` value (owner's rule,
    2026-08-14: "other plans they give access to part of the program like
    a week while others may give it as a whole").

    Anything unresolvable — None (a legacy record without a plan link, a
    pre-migration row) or an unknown string — answers Full: the field
    defaults Full, so nothing narrows for existing students until the
    owner configures plans otherwise. Only an explicit known level
    narrows.
    """
    if value in HOLIDAY_ACCESS_LEVELS:
        return value
    return HOLIDAY_ACCESS_FULL


def holiday_access_from_records(records, today):
    """Resolve the holiday access level from a student's billing records
    (dicts with `holiday_access`/`kind`/`period_start`/`period_end`,
    NEWEST FIRST), mirroring assistant_chat_from_records: the first record
    whose coverage includes [today] and whose plan carries a resolvable
    level decides.

    A One-Off Programme purchase (the standalone R449 holiday checkout)
    is always Full for its window — buying the programme outright IS
    buying the whole programme, whatever the plan record's level says.

    No governing record — no records, none covering today, none with a
    plan link — answers Full (fail-open, same posture as the chat gate).
    """
    for record in records or []:
        start = record.get("period_start")
        end = record.get("period_end")
        if start and start > today:
            continue
        if end and end < today:
            continue
        if record.get("kind") == KIND_ONE_OFF_PROGRAMME:
            return HOLIDAY_ACCESS_FULL
        level = record.get("holiday_access")
        if level is None:
            continue
        return holiday_access_level(level)
    return HOLIDAY_ACCESS_FULL


def assistant_chat_from_records(records, today):
    """Resolve the chat-assistant flag from a student's billing records
    (dicts with `assistant_chat`/`period_start`/`period_end`, NEWEST
    FIRST): the first record whose coverage includes [today] and whose
    plan carries a resolvable flag decides. No governing record — no
    records, none covering today, none with a plan link — answers True
    (see allows_assistant_chat: availability defaults open).
    """
    for record in records or []:
        start = record.get("period_start")
        end = record.get("period_end")
        if start and start > today:
            continue
        if end and end < today:
            continue
        flag = record.get("assistant_chat")
        if flag is None:
            continue
        return allows_assistant_chat(flag)
    return True
