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

"""Wallet-mediated subscription billing (product log #33).

Closes the pay-flow gap: purchase used to dead-end at
`LessonPurchaseOutcome.paymentSetupRequired` (#23/#30) because no backend
consumed the client's `beneficiary_user_id` and nothing charged a payer.
This module is that missing path, built on the wallet SDK's EXISTING
ledger doctypes (Wallet, Wallet History) rather than a parallel store —
top-ups still ride wallet_sdk's gateway APIs (PayFast/Paystack/…); what is
new here is the SUBSCRIPTION chain over those balances.

The owner's chain, per student, every hop a ledger entry:

    sponsor wallet DEBIT -> student wallet CREDIT -> student wallet DEBIT
                                                     (for the subscription)

so payment provenance (who funded whom) is auditable per student. The hop
sequence itself is planned by the frappe-free `rlms.billing_rules` and
executed here one-for-one; the rate decision (#23's fix: the partner
discount belongs to the PAYER) is `billing_rules.charge_per_student`.

On success each student's period lands via the same writer
`rlms.api.student.record_subscription_period` uses (#30's integration
point), so entitlement resolution (#27) sees paid coverage immediately.
"""

import frappe
from frappe import _
from frappe.utils import add_months, now_datetime, nowdate

from .. import billing_rules, plan_rules
from ..payer_rules import can_pay
from . import student as student_api

# Wallet History's `transaction_type` Select has no subscription-specific
# option; 'Payment' is its existing outbound-money type and 'Topup' its
# inbound one. Provenance lives in the description + the LMS Billing
# Record, not in a new option on another SDK's doctype.
_OUT = "Payment"
_IN = "Topup"


def _wallet_for(user, create=False):
    """The user's Wallet row (wallet_sdk's doctype). Created on demand for
    a student receiving sponsor funds — a student who never topped up has
    no wallet yet, and that must not block a sponsor paying for them."""
    name = frappe.db.get_value("Wallet", {"user": user}, "name")
    if name:
        return frappe.get_doc("Wallet", name)
    if not create:
        return None
    doc = frappe.get_doc({"doctype": "Wallet", "user": user, "balance": 0})
    doc.insert(ignore_permissions=True)
    return doc


def _apply_hop(hop, description):
    """Execute one planned ledger hop: move the balance and write the
    Wallet History row. Any throw aborts the enclosing request and frappe
    rolls the whole chain back — the all-or-nothing property the funds
    check assumes."""
    wallet = _wallet_for(hop["wallet_user"], create=hop["amount"] > 0)
    if wallet is None:
        frappe.throw(
            _("{0} has no wallet to pay from.").format(hop["wallet_user"])
        )
    balance = wallet.balance or 0
    new_balance = balance + hop["amount"]
    if new_balance < 0:
        frappe.throw(_("Insufficient wallet balance."))
    wallet.balance = new_balance
    wallet.save(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": wallet.name,
            "transaction_type": _OUT if hop["amount"] < 0 else _IN,
            "amount": abs(hop["amount"]),
            "status": "Processed",
            "description": description,
        }
    ).insert(ignore_permissions=True)


def _record_window(student, start, end, source):
    """Write one paid coverage window (#27/#30). Mirrors
    student.record_subscription_period's semantics — idempotent by
    (student, start_date) so a renewal extends rather than duplicates."""
    existing = frappe.db.get_value(
        "LMS Subscription Period", {"student": student, "start_date": start}, "name"
    )
    if existing:
        frappe.db.set_value(
            "LMS Subscription Period", existing, {"end_date": end, "source": source}
        )
    else:
        frappe.get_doc(
            {
                "doctype": "LMS Subscription Period",
                "student": student,
                "start_date": start,
                "end_date": end,
                "source": source,
            }
        ).insert(ignore_permissions=True)
    return start, end


def _record_period(student, months, source):
    """A months-long coverage window starting today — the recurring case."""
    start = frappe.utils.getdate(nowdate())
    end = frappe.utils.getdate(add_months(start, months))
    return _record_window(student, start, end, source)


def _plan_rates():
    """Base and partner rates. Single source: LMS Settings when the site
    defines it, else the documented launch prices (R299 / R249 — business
    doc §3, the pair #23 named)."""
    base = frappe.db.get_single_value("LMS Settings", "base_monthly_rate") or 299
    partner = frappe.db.get_single_value("LMS Settings", "partner_monthly_rate") or 249
    return float(base), float(partner)


def _billing_record(
    student, payer, amount, rate_kind, months, start, end, when, plan=None, lesson=None
):
    frappe.get_doc(
        {
            "doctype": "LMS Billing Record",
            "student": student,
            "payer": payer,
            "amount": amount,
            "rate_kind": rate_kind,
            "months": months,
            "period_start": start,
            "period_end": end,
            "charged_at": when,
            "plan": plan,
            "lesson": lesson,
        }
    ).insert(ignore_permissions=True)


def _ensure_seed_plans():
    """Land the documented launch catalog as EDITABLE records, exactly once
    — only when no LMS Plan rows exist at all (a deliberate, named launch
    seed per #47, like the tutor catalog). After that the records are the
    single source of truth: an owner's edit, deactivation or deletion of a
    specific plan is never overwritten or re-seeded."""
    if frappe.db.count("LMS Plan"):
        return
    for seed in plan_rules.default_plans():
        frappe.get_doc({"doctype": "LMS Plan", **seed}).insert(
            ignore_permissions=True
        )


def _active_plan(plan_key):
    """The LMS Plan record a checkout named, refused honestly when unknown
    or switched off — never a silent fallback to another price."""
    _ensure_seed_plans()
    row = frappe.db.get_value(
        "LMS Plan",
        {"plan_key": (plan_key or "").strip().lower()},
        [
            "name",
            "plan_key",
            "title",
            "kind",
            "price",
            "months",
            "active",
            "window_label",
            "window_start",
            "window_end",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Unknown plan: {0}").format(plan_key))
    if not row.active:
        frappe.throw(_("That plan is not available right now."))
    return row


def _plan_charge(plan, discounted):
    """Resolve one plan purchase to (per-student amount, rate_kind, months,
    coverage). Coverage is the (start, end) date pair the period writer
    records — for a one-off programme that is the UPCOMING window resolved
    AT PURCHASE TIME from the plan record's configurable dates (owner's
    rule: the purchase buys the next programme, never an arbitrary or past
    one); None for recurring (start-today) and per-lesson (no period at
    all — the paid lesson itself is the grant)."""
    _, partner_rate = _plan_rates()
    try:
        amount, rate_kind = plan_rules.charge_for_plan(
            plan.kind,
            float(plan.price or 0),
            int(plan.months or 0),
            partner_rate,
            discounted,
        )
    except ValueError:
        # An unpriced/malformed plan record: refuse, never invent (#47).
        frappe.throw(
            _("The {0} plan is not priced for checkout yet.").format(plan.title)
        )

    coverage = None
    if plan.kind == plan_rules.KIND_ONE_OFF_PROGRAMME:
        coverage = plan_rules.upcoming_window(
            frappe.utils.getdate(plan.window_start) if plan.window_start else None,
            frappe.utils.getdate(plan.window_end) if plan.window_end else None,
            frappe.utils.getdate(nowdate()),
        )
        if not coverage:
            frappe.throw(
                _("The next {0} window has not been announced yet.").format(
                    plan.window_label or plan.title
                )
            )
    return amount, rate_kind, int(plan.months or 0), coverage


def _lesson_for_purchase(student, lesson):
    """Validate a pay-per-lesson target: the lesson must exist, must not be
    a free sample (samples ARE the funnel — charging for one would be
    dishonest), and must not already be paid for by this student (a
    double-tap must not double-charge)."""
    if not lesson:
        frappe.throw(
            _("A per-lesson plan is charged per lesson — name the lesson.")
        )
    details = frappe.db.get_value(
        "Course Lesson",
        lesson,
        ["name", "title", "is_free_sample", "session_id"],
        as_dict=True,
    )
    if not details:
        frappe.throw(_("Lesson not found."))
    if details.is_free_sample:
        frappe.throw(_("That lesson is a free sample — no payment is needed."))
    if frappe.db.exists("LMS Billing Record", {"student": student, "lesson": lesson}):
        frappe.throw(_("That lesson is already paid for."))
    return details


def _lesson_day(details):
    """The day a per-lesson charge covers — the lesson's broadcast day when
    it has a Replay Session schedule, else the purchase day (on-demand)."""
    scheduled_at = frappe.db.get_value(
        "Replay Session", {"session_id": details.session_id}, "scheduled_at"
    )
    return (
        frappe.utils.getdate(scheduled_at)
        if scheduled_at
        else frappe.utils.getdate(nowdate())
    )


@frappe.whitelist()
def plans():
    """The purchasable plan catalog — active LMS Plan records, in sort
    order. This is what the app's plans surface renders (the owner's
    "sub plans should be configurable": prices come from these records,
    never client constants).

    partner_monthly_rate rides along so partner-facing surfaces can quote
    the real per-student monthly rate (#23) from the same server answer.
    """
    _ensure_seed_plans()
    rows = frappe.get_all(
        "LMS Plan",
        {"active": 1},
        [
            "plan_key",
            "title",
            "description",
            "kind",
            "price",
            "months",
            "assistant_chat",
            "window_label",
            "window_start",
            "window_end",
        ],
        order_by="sort_order asc, plan_key asc",
    )
    _, partner_rate = _plan_rates()
    return {
        "plans": [
            {
                "id": r.plan_key,
                "title": r.title,
                "description": r.description or "",
                "kind": r.kind,
                "price": float(r.price or 0),
                "months": int(r.months or 0),
                # In-lesson chat assistant inclusion (defaults ON — see
                # plan_rules.allows_assistant_chat).
                "assistant_chat": plan_rules.allows_assistant_chat(
                    r.assistant_chat
                ),
                "window_label": r.window_label,
                "window_start": str(r.window_start) if r.window_start else None,
                "window_end": str(r.window_end) if r.window_end else None,
            }
            for r in rows
        ],
        "partner_monthly_rate": partner_rate,
    }


@frappe.whitelist()
def sponsor_checkout(students, months=1, plan=None, lesson=None):
    """Partner-side: pay for one or more linked students out of the
    partner's wallet, running the decided chain per student.

    The caller must be an Active partner of every named student AND hold a
    payer-capable relationship (rlms.payer_rules — a teacher cannot pay,
    enforced here server-side, not only by a hidden toggle). Funds are
    checked for the WHOLE checkout before any hop is written.

    [plan] (an LMS Plan key) makes the checkout plan-aware: the server
    charges that record's price per its kind — recurring months, a one-off
    programme bounded to the plan's upcoming window, or a per-lesson
    once-off for [lesson]. Without [plan], the legacy months × monthly-rate
    path runs unchanged.
    """
    payer = frappe.session.user
    if isinstance(students, str):
        students = frappe.parse_json(students)
    students = [s for s in (students or []) if s]
    if not students:
        frappe.throw(_("Name at least one student to pay for."))
    try:
        months = int(months)
    except (TypeError, ValueError):
        months = 1
    if not plan and months < 1:
        frappe.throw(_("Months must be at least 1."))

    # Every student must be this partner's own Active link, and the link's
    # relationship must be payer-capable.
    for student in students:
        link = frappe.db.get_value(
            "LMS Partner Link",
            {"partner": payer, "student": student, "status": "Active"},
            ["name", "relationship"],
            as_dict=True,
        )
        if not link:
            frappe.throw(
                _("That student is not linked to this account."),
                frappe.PermissionError,
            )
        if not can_pay(link.relationship):
            frappe.throw(
                _("A {0} partner cannot pay for a student.").format(
                    (link.relationship or "").lower()
                ),
                frappe.PermissionError,
            )

    plan_row = _active_plan(plan) if plan else None
    lesson_details = None
    if plan_row and plan_row.kind == plan_rules.KIND_PER_LESSON:
        # Same duplicate/free-sample guard PER student — a lesson already
        # paid for one child must not silently charge again for them.
        for student in students:
            lesson_details = _lesson_for_purchase(student, lesson)

    if plan_row:
        # A sponsor is by definition payer-capable, so a MONTHLY recurring
        # plan charges the per-student monthly partner rate (#23's fix);
        # yearly/one-off/per-lesson plans charge the record's own price.
        per_student, rate_kind, months, coverage = _plan_charge(plan_row, True)
    else:
        base, partner_rate = _plan_rates()
        # A sponsor checkout is by definition a payer-capable partner
        # paying, so the partner rate applies — to the PAYER's charge
        # (#23's fix).
        per_student = (
            billing_rules.charge_per_student(base, partner_rate, True) * months
        )
        rate_kind, coverage = "Partner", None
    total, hops = billing_rules.plan_sponsor_checkout(payer, students, per_student)

    wallet = _wallet_for(payer)
    balance = (wallet.balance or 0) if wallet else 0
    if not billing_rules.sufficient_balance(balance, total):
        frappe.throw(
            _("Top up your wallet: this checkout needs {0}.").format(total)
        )

    when = now_datetime()
    for hop in hops:
        _apply_hop(hop, _hop_description(hop, payer))

    plan_suffix = f":plan:{plan_row.plan_key}" if plan_row else ""
    for student in students:
        if lesson_details is not None:
            # Per-lesson: no subscription period — the paid lesson itself
            # is the grant (course.get_lesson_session honours the record).
            day = _lesson_day(lesson_details)
            start, end = day, day
        elif coverage:
            # One-off programme: bounded to the UPCOMING window resolved at
            # purchase time from the plan record.
            start, end = _record_window(
                student, coverage[0], coverage[1], f"sponsor:{payer}{plan_suffix}"
            )
        else:
            start, end = _record_period(
                student, months, f"sponsor:{payer}{plan_suffix}"
            )
        _billing_record(
            student,
            payer,
            per_student,
            rate_kind,
            months,
            start,
            end,
            when,
            plan=plan_row.name if plan_row else None,
            lesson=lesson_details.name if lesson_details else None,
        )

    result = {
        "total": total,
        "students": students,
        "months": months,
        "rate_kind": rate_kind,
    }
    if plan_row:
        result["plan"] = plan_row.plan_key
    if coverage:
        result["period_start"] = str(coverage[0])
        result["period_end"] = str(coverage[1])
    if lesson_details is not None:
        result["lesson"] = lesson_details.name
    return result


def _hop_description(hop, payer):
    """Human-readable provenance on every ledger row — the audit trail
    reads without joining back to LMS Billing Record."""
    if hop["kind"] == billing_rules.SPONSOR_WALLET_DEBIT:
        return f"Subscription funding for {hop['student']}"
    if hop["kind"] == billing_rules.STUDENT_WALLET_CREDIT:
        return f"Subscription funded by {payer}"
    return "Supacharge subscription"


@frappe.whitelist()
def student_checkout(months=1, maths_track=None, plan=None, lesson=None):
    """Student-side self-payment from their own wallet — the other half of
    closing the paymentSetupRequired dead-end.

    The §1 promise still holds: a student with a payer-capable partner
    linked pays the partner rate on their OWN charge (the discount follows
    the payer, and here the student IS the payer).

    #29: subscribe is where the maths track is chosen, so an optional
    [maths_track] is recorded here through the same exclusivity-enforcing
    writer the picker uses — choosing the opposite of a track already held
    refuses the checkout rather than silently taking the money.

    [plan] (an LMS Plan key) makes the checkout plan-aware — the server
    charges the record's own price per its kind: recurring months, a
    one-off programme bounded to the plan record's UPCOMING window, or a
    per-lesson once-off for [lesson] ("you attend a lesson you are
    required to pay"). Without [plan], the legacy months × monthly-rate
    path runs unchanged.
    """
    student = frappe.session.user
    try:
        months = int(months)
    except (TypeError, ValueError):
        months = 1
    if not plan and months < 1:
        frappe.throw(_("Months must be at least 1."))

    # Track choice first: refuse BEFORE any wallet hop, so a rejected
    # choice never leaves a charge behind.
    if maths_track:
        student_api.set_maths_track(maths_track)

    plan_row = _active_plan(plan) if plan else None
    lesson_details = None
    if plan_row and plan_row.kind == plan_rules.KIND_PER_LESSON:
        lesson_details = _lesson_for_purchase(student, lesson)

    link = frappe.db.get_value(
        "LMS Partner Link",
        {"student": student, "status": "Active"},
        ["relationship"],
        as_dict=True,
    )
    discounted = bool(link and can_pay(link.relationship))

    if plan_row:
        amount, rate_kind, months, coverage = _plan_charge(plan_row, discounted)
    else:
        base, partner_rate = _plan_rates()
        amount = (
            billing_rules.charge_per_student(base, partner_rate, discounted) * months
        )
        rate_kind = "Partner" if discounted else "Base"
        coverage = None
    total, hops = billing_rules.plan_student_checkout(student, amount)

    wallet = _wallet_for(student)
    balance = (wallet.balance or 0) if wallet else 0
    if not billing_rules.sufficient_balance(balance, total):
        frappe.throw(_("Top up your wallet: this checkout needs {0}.").format(total))

    when = now_datetime()
    description = (
        f"Supacharge {plan_row.title}" if plan_row else "Supacharge subscription"
    )
    for hop in hops:
        _apply_hop(hop, description)

    plan_suffix = f":plan:{plan_row.plan_key}" if plan_row else ""
    if lesson_details is not None:
        # Per-lesson: no subscription period — the paid lesson itself is
        # the grant (course.get_lesson_session honours the record).
        day = _lesson_day(lesson_details)
        start, end = day, day
    elif coverage:
        start, end = _record_window(
            student, coverage[0], coverage[1], f"self:{student}{plan_suffix}"
        )
    else:
        start, end = _record_period(student, months, f"self:{student}{plan_suffix}")
    _billing_record(
        student,
        student,
        amount,
        rate_kind,
        months,
        start,
        end,
        when,
        plan=plan_row.name if plan_row else None,
        lesson=lesson_details.name if lesson_details else None,
    )
    result = {"total": total, "months": months, "rate_kind": rate_kind}
    if plan_row:
        result["plan"] = plan_row.plan_key
    if coverage:
        result["period_start"] = str(coverage[0])
        result["period_end"] = str(coverage[1])
    if lesson_details is not None:
        result["lesson"] = lesson_details.name
    return result


@frappe.whitelist()
def my_billing_history():
    """What the caller has funded (as payer) — the partner's own audit
    view. A student's coverage view is student.my_entitlements; this is
    the money side, scoped to the payer who spent it."""
    rows = frappe.get_all(
        "LMS Billing Record",
        {"payer": frappe.session.user},
        ["student", "amount", "rate_kind", "months", "period_start", "period_end", "charged_at"],
        order_by="charged_at desc",
        limit_page_length=100,
    )
    return {"records": rows}
