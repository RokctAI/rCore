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

"""Accountability Partner backend (business doc §1, extended by P3.1). A
partner is a reporting-only persona: their own User + Role, linked to ONE OR
MORE students via LMS Partner Link rows (P3.1: a parent with several kids
holds one partner account with a link row per child), with zero capability
over any student's account — that boundary is enforced client-side by
AccessPolicy and never needs a Frappe permission to "let" a partner do
something a student does, because nothing here gives a partner user any
student-scoped write access.

P3.1 additions, all riding the same LMS Partner Link doctype:
- multi-student: accept_invite attaches to an existing partner account
  (password-verified) instead of failing; my_students/weekly_report(student)
  resolve per linked student.
- partner-first signup: signup mints a partner account with no links yet;
  invite_student sends the reversed invite; redeem_student_invite activates
  it from the student's side after normal student onboarding.
- partner-as-payer: assume_billing/release_billing flip the link's payer
  field — delegated billing only (the student keeps their own subscription;
  who gets charged changes). Deliberately NOT a family-plan redesign.
"""

import secrets

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.password import check_password

from .. import alert_rules, role_exclusivity
from ..alert_rules import evaluate_skip_alert
from ..payer_rules import can_pay
from ..role_exclusivity import conflicting_role
from ..time_gates import attendance_claim_permitted

PARTNER_ROLE = "Accountability Partner"

# How many trailing events the skip-alert threshold looks at.
ALERT_WINDOW = 4

# P3.2: pairing codes replace web-link tokens entirely. 48 hours is long
# enough for "I'll ask my mom tonight" and short enough that a code seen
# over someone's shoulder goes stale quickly.
CODE_VALIDITY_HOURS = 48


def _mint_pairing_code():
    """A 6-digit pairing code (smart-TV style), unique among pending invites.
    secrets.randbelow keeps it cryptographically random; the uniqueness loop
    matters because 6 digits is a small space once invites accumulate."""
    for _attempt in range(20):
        code = f"{secrets.randbelow(1000000):06d}"
        if not frappe.db.exists("LMS Partner Link", {"invite_token": code, "status": "Invited"}):
            return code
    frappe.throw(_("Could not generate a pairing code. Please try again."))


def _find_valid_invite(code, extra_filters=None):
    """Resolve a pending invite by pairing code, treating expiry as invalid.
    Expired rows are marked Revoked in passing so the unique code frees up."""
    filters = {"invite_token": (code or "").strip(), "status": "Invited"}
    filters.update(extra_filters or {})
    link_name = frappe.db.exists("LMS Partner Link", filters)
    if not link_name:
        return None
    expires_at = frappe.db.get_value("LMS Partner Link", link_name, "invite_expires_at")
    if expires_at and frappe.utils.get_datetime(expires_at) < now_datetime():
        frappe.db.set_value("LMS Partner Link", link_name, "status", "Revoked")
        return None
    return link_name


def _relationship_label(relationship):
    return {
        "parent": "Parent",
        "guardian": "Guardian",
        "sibling": "Sibling",
        "teacher": "Teacher",
        "mentor": "Mentor",
        # #33: payer-capable partner type — see rlms.payer_rules.
        "sponsor": "Sponsor",
    }.get(relationship, relationship.title() if relationship else "Parent")


def _ensure_partner_role():
    if not frappe.db.exists("Role", PARTNER_ROLE):
        frappe.get_doc({"doctype": "Role", "role_name": PARTNER_ROLE, "desk_access": 0}).insert(
            ignore_permissions=True
        )


def _has_partner_role(user):
    return bool(frappe.db.exists("Has Role", {"parent": user, "role": PARTNER_ROLE}))


def _is_student(user):
    """Whether [user] is a learner account, for the role-exclusivity guard
    (decision #23). This does the three footprint lookups; WHICH facts
    constitute the persona is the pure rule's call (role_exclusivity.
    has_student_footprint), so the definition can't drift per call site."""
    return role_exclusivity.has_student_footprint(
        has_grade_profile=frappe.db.exists("LMS Student Profile", {"user": user}),
        has_enrollment=frappe.db.exists("LMS Enrollment", {"member": user}),
        is_linked_student=frappe.db.exists(
            "LMS Partner Link", {"student": user, "status": "Active"}
        ),
    )


def enforce_role_exclusivity(user, binding):
    """Throw a clear error if binding [user] into [binding] (role_exclusivity.
    STUDENT or PARTNER) would make one account both personas. Looks up the
    roles the user already holds, then defers the decision to the frappe-free
    rule. Called for BOTH parties of a link binding so a pre-existing
    corruption on either side is caught, not propagated. Public because the
    student-side acquisition paths (api/student.py profile capture,
    api/course.py enroll) apply the same guard — one throw site, one pair of
    messages."""
    conflict = conflicting_role(
        binding, is_student=_is_student(user), is_partner=_has_partner_role(user)
    )
    if conflict == role_exclusivity.STUDENT:
        frappe.throw(
            _(
                "This account is registered as a student and can't also be an "
                "accountability partner. Partners need their own separate account."
            )
        )
    if conflict == role_exclusivity.PARTNER:
        frappe.throw(
            _(
                "This account is an accountability partner and can't also join as "
                "a student. Students need their own separate account."
            )
        )


@frappe.whitelist()
def invite(contact, channel, relationship):
    """Student-side: §1 'Setup At Signup'. Creates the pending link and sends
    the invite via SMS or email — never both, matching the student's choice."""
    student = frappe.session.user
    # Role exclusivity (decision #23) at the link CREATION step, not just at
    # accept: the caller binds as the link's student side right here, so a
    # partner account is refused before an invite is ever minted and sent.
    enforce_role_exclusivity(student, role_exclusivity.STUDENT)
    # One partner per student (§1/§3 shape, unchanged by P3.1 — the
    # multiplicity that grew is partner->students, not student->partners).
    if frappe.db.exists("LMS Partner Link", {"student": student, "status": "Active"}):
        frappe.throw(_("You already have an accountability partner."))
    code = _mint_pairing_code()
    expires_at = frappe.utils.add_to_date(now_datetime(), hours=CODE_VALIDITY_HOURS)

    doc = frappe.get_doc(
        {
            "doctype": "LMS Partner Link",
            "student": student,
            "relationship": _relationship_label(relationship),
            "contact": contact,
            "channel": channel,
            "status": "Invited",
            "initiated_by": "Student",
            "invite_token": code,
            "invite_expires_at": expires_at,
        }
    )
    doc.insert(ignore_permissions=True)

    student_name = frappe.db.get_value("User", student, "full_name") or student
    # P3.2: no web page — the message carries the pairing code the partner
    # types into their own app, and the student's app shows the same code.
    message = (
        f"{student_name} added you as their accountability partner on Supacharge. "
        f"Get the app, choose 'I'm a partner', and enter pairing code {code} "
        f"(valid for {CODE_VALIDITY_HOURS} hours) to see their weekly progress."
    )

    try:
        if channel == "sms":
            frappe.send_sms(receivers=[contact], message=message)
        else:
            frappe.sendmail(
                recipients=[contact],
                subject=f"{student_name} invited you as their accountability partner",
                message=message,
            )
    except Exception as e:
        frappe.log_error(f"Failed to send partner invite to {contact}: {e}", "Partner Invite Send Error")
        frappe.throw(_("Could not send the invite. Please try again."))

    return {"name": doc.name, "code": code, "expires_at": expires_at.isoformat()}


@frappe.whitelist(allow_guest=True)
def accept_invite(token, email, password, first_name="", last_name=""):
    """Partner-side: resolves a student's 6-digit pairing code into a partner
    login (P3.2: [token] carries the code the partner typed in their app —
    parameter name kept for wire compatibility). Single-use, 48h expiry.

    P3.1 multi-student: if [email] is already an Accountability Partner
    account, the invite attaches a NEW link to that same account (a parent
    accepting a second kid's invite) — the supplied password is verified
    against the existing account first, since the caller is claiming to own
    it. Otherwise the reporting-only login is minted fresh, exactly as in P3.
    Any other pre-existing account (a student's, say) still refuses: one
    User is never both personas."""
    link_name = _find_valid_invite(token, {"initiated_by": "Student"})
    if not link_name:
        frappe.throw(_("This pairing code is invalid, expired, or already used."))

    link = frappe.get_doc("LMS Partner Link", link_name)

    # Role exclusivity (decision #23), both directions: the invitee is about
    # to become a partner (must not already be a student), and the student on
    # the link must not itself hold a partner role.
    enforce_role_exclusivity(email, role_exclusivity.PARTNER)
    enforce_role_exclusivity(link.student, role_exclusivity.STUDENT)

    if frappe.db.exists("User", email):
        if not _has_partner_role(email):
            frappe.throw(_("An account with this email already exists."))
        try:
            check_password(email, password)
        except frappe.AuthenticationError:
            frappe.throw(_("Wrong password for the existing partner account."))
        if frappe.db.exists(
            "LMS Partner Link", {"student": link.student, "partner": email, "status": "Active"}
        ):
            frappe.throw(_("This partner is already linked to this student."))
    else:
        if not first_name:
            frappe.throw(_("First name is required to create a new partner account."))
        _ensure_partner_role()
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "send_welcome_email": 0,
                "roles": [{"role": PARTNER_ROLE}],
            }
        )
        user.insert(ignore_permissions=True)
        user.new_password = password
        user.save(ignore_permissions=True)

    link.partner = email
    link.status = "Active"
    link.invite_token = None
    link.invite_expires_at = None
    link.save(ignore_permissions=True)

    return {"email": email}


@frappe.whitelist()
def my_status():
    """Student-side: backs SubjectEntitlements-adjacent 'hasPartner' — whether
    the current student has an active accountability partner (drives the
    discounted-rate capability and the partner-linkage UI state). P3.1 adds
    paid_by_partner: whether that partner has assumed billing responsibility
    for this student's subscription."""
    link = frappe.db.get_value(
        "LMS Partner Link",
        {"student": frappe.session.user, "status": "Active"},
        ["payer"],
        as_dict=True,
    )
    return {
        "has_partner": bool(link),
        "paid_by_partner": bool(link and link.payer == "Partner"),
    }


def _linked_students():
    """Every Active link for the authenticated partner (P3.1: one partner,
    many students). A partner can only ever see their own linked students."""
    links = frappe.get_all(
        "LMS Partner Link",
        {"partner": frappe.session.user, "status": "Active"},
        ["name", "student", "relationship", "payer", "email_digest"],
    )
    if not links:
        frappe.throw(_("No linked student found for this account."), frappe.PermissionError)
    return links


def _resolve_student(student=None):
    """Which linked student a partner-side call is about. With one link the
    argument is optional; with several it must name one of THIS partner's
    students — anything else is a permission error, not a fallback."""
    links = _linked_students()
    if student:
        for link in links:
            if link.student == student:
                return link
        frappe.throw(_("That student is not linked to this account."), frappe.PermissionError)
    if len(links) > 1:
        frappe.throw(_("This account has several students — say which one."))
    return links[0]


@frappe.whitelist()
def my_students():
    """Partner-side: the students linked to this account, for the dashboard's
    per-student switcher (P3.1). Includes billing responsibility per link."""
    students = []
    for link in _linked_students():
        full_name = frappe.db.get_value("User", link.student, "full_name") or link.student
        students.append(
            {
                "student": link.student,
                "student_name": full_name,
                "relationship": link.relationship,
                "paid_by_partner": link.payer == "Partner",
                # #33: whether this link's relationship MAY pay at all, so
                # the UI can explain a disabled toggle instead of letting
                # the partner discover the refusal by being denied.
                "can_pay": can_pay(link.relationship),
                # Whether this link's weekly email digest is on, so the
                # settings toggle can render its real state.
                "email_digest": bool(link.email_digest),
            }
        )
    return {"students": students}


@frappe.whitelist()
def weekly_report(week_start, student=None):
    """Partner-side: the §1 Sunday report, computed from data the backend
    already tracks (LMS Course Progress, LMS Lesson Quiz Result, Replay
    Session schedule, and — P3.2 — LMS Attendance Event, the sync point
    record_attendance_event feeds from the on-device §5 ledger). The
    answered/unanswered skip split, study streak, and data usage all come
    from real synced events now; no approximated fields remain.

    P3.1: [student] selects which linked student the report is about; it must
    be one of the caller's own Active links (permission error otherwise).
    """
    student = _resolve_student(student).student
    return build_weekly_report(student, frappe.utils.get_datetime(week_start))


def build_weekly_report(student, week_start_dt):
    """The weekly report payload for [student], week [week_start_dt, +7d).
    Split out of weekly_report so the digest scheduler task can build the
    same report without a partner session — CALLERS do the authorization
    (weekly_report resolves the caller's own link; tasks.py iterates links
    that are Active by query)."""
    week_end_dt = frappe.utils.add_to_date(week_start_dt, days=7)

    student_name = frappe.db.get_value("User", student, "full_name") or student

    lesson_rows = frappe.get_all(
        "Course Lesson", {"session_id": ["is", "set"]}, ["name", "title", "session_id", "course"]
    )
    session_ids = [r.session_id for r in lesson_rows]
    lesson_by_session = {r.session_id: r for r in lesson_rows}

    scheduled_this_week = []
    if session_ids:
        scheduled_this_week = frappe.get_all(
            "Replay Session",
            {
                "session_id": ["in", session_ids],
                "scheduled_at": ["between", [week_start_dt, week_end_dt]],
            },
            ["session_id", "scheduled_at"],
        )

    scheduled_lesson_names = [
        lesson_by_session[s.session_id].name
        for s in scheduled_this_week
        if s.session_id in lesson_by_session
    ]

    sessions_scheduled = len(scheduled_lesson_names)

    # P3.2: attendance/skip outcomes come from real synced events. The
    # answered/unanswered split is exactly what the skip-gate recorded on
    # device (record_attendance_event mirrors AttendanceOutcome), not an
    # everything-is-unanswered approximation.
    week_events = frappe.get_all(
        "LMS Attendance Event",
        {"student": student, "occurred_at": ["between", [week_start_dt, week_end_dt]]},
        ["session_id", "outcome", "data_used_mb"],
    )
    sessions_attended = sum(1 for e in week_events if e.outcome == "Attended")
    skipped_answered = sum(1 for e in week_events if e.outcome == "Skipped Answered")
    skipped_unanswered = sum(1 for e in week_events if e.outcome == "Skipped Unanswered")

    # Data used this month: sum of the month's synced per-session estimates
    # (the on-device §5 ledger's own numbers, not a server guess).
    month_start = week_start_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_rows = frappe.get_all(
        "LMS Attendance Event",
        {"student": student, "occurred_at": [">=", month_start]},
        ["data_used_mb"],
    )
    data_used_mb = sum(r.data_used_mb or 0 for r in month_rows)

    # Study streak: consecutive Attended events counting back from the most
    # recent one — the same "consecutive sessions attended without skipping"
    # definition the ADR mapped onto the recovery module, now server-side.
    streak_rows = frappe.get_all(
        "LMS Attendance Event",
        {"student": student},
        ["outcome"],
        order_by="occurred_at desc",
        limit_page_length=200,
    )
    current_streak = 0
    for row in streak_rows:
        if row.outcome != "Attended":
            break
        current_streak += 1

    quiz_results = frappe.get_all(
        "LMS Lesson Quiz Result",
        {
            "lesson": ["in", [r.name for r in lesson_rows]] if lesson_rows else ["in", []],
            "member": student,
            "creation": ["between", [week_start_dt, week_end_dt]],
        },
        ["lesson", "outcome"],
    )
    answered = sum(1 for q in quiz_results if q.outcome in ("Correct", "Incorrect"))
    skipped_questions = sum(1 for q in quiz_results if q.outcome == "Skipped")
    engagement_rate = (
        round(answered * 100 / (answered + skipped_questions))
        if (answered + skipped_questions) > 0
        else 0
    )

    scores_by_lesson = {}
    for q in quiz_results:
        if q.outcome not in ("Correct", "Incorrect"):
            continue
        scores_by_lesson.setdefault(q.lesson, []).append(1 if q.outcome == "Correct" else 0)
    lesson_titles = {r.name: r.title for r in lesson_rows}
    performance_scores = {
        lesson_titles.get(lesson, lesson): round(sum(vals) * 100 / len(vals))
        for lesson, vals in scores_by_lesson.items()
        if vals
    }

    return {
        "student_name": student_name,
        "week_start": week_start_dt.isoformat(),
        "sessions_scheduled": sessions_scheduled,
        "sessions_attended": sessions_attended,
        "sessions_skipped_answered": skipped_answered,
        "sessions_skipped_unanswered": skipped_unanswered,
        "performance_scores": performance_scores,
        "engagement_rate_percent": engagement_rate,
        "data_used_mb": data_used_mb,
        "current_streak": current_streak,
    }


# ---------------------------------------------------------------------------
# P3.1 — partner-first signup (the reversed invite direction)
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True)
def signup(email, password, first_name, last_name=""):
    """Partner-first signup: a partner account with NO student links yet (the
    reverse of P3's invite-then-accept). Mints the same reporting-only login
    accept_invite does — same role, same zero capability over any student —
    just without a link row, which invite_student creates afterwards."""
    if frappe.db.exists("User", email):
        frappe.throw(_("An account with this email already exists."))

    _ensure_partner_role()
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "send_welcome_email": 0,
            "roles": [{"role": PARTNER_ROLE}],
        }
    )
    user.insert(ignore_permissions=True)
    user.new_password = password
    user.save(ignore_permissions=True)

    return {"email": email}


@frappe.whitelist()
def invite_student(contact, channel, relationship):
    """Partner-side: invite a student under this partner account (P3.1). The
    student gets a join link whose code they redeem after normal student
    signup. Adding a student grants the partner NOTHING beyond the same
    reporting surfaces — AccessPolicy is role-based and direction-blind."""
    partner = frappe.session.user
    if not _has_partner_role(partner):
        frappe.throw(
            _("Only an accountability partner account can invite a student."),
            frappe.PermissionError,
        )
    # Role exclusivity (decision #23) at the link CREATION step: a corrupt
    # account holding BOTH personas may not extend its partner side either
    # (same defensive posture as the dual-role cases in the pure rule's tests).
    enforce_role_exclusivity(partner, role_exclusivity.PARTNER)

    code = _mint_pairing_code()
    expires_at = frappe.utils.add_to_date(now_datetime(), hours=CODE_VALIDITY_HOURS)
    doc = frappe.get_doc(
        {
            "doctype": "LMS Partner Link",
            "partner": partner,
            "relationship": _relationship_label(relationship),
            "contact": contact,
            "channel": channel,
            "status": "Invited",
            "initiated_by": "Partner",
            "invite_token": code,
            "invite_expires_at": expires_at,
        }
    )
    doc.insert(ignore_permissions=True)

    partner_name = frappe.db.get_value("User", partner, "full_name") or partner
    # P3.2: pairing code, no web page — the student signs up normally in the
    # app, then enters the code there; the partner's app shows the same code.
    message = (
        f"{partner_name} invited you to learn on Supacharge with them as your "
        f"accountability partner. Get the app, sign up, and enter pairing code "
        f"{code} (valid for {CODE_VALIDITY_HOURS} hours) to link up."
    )

    try:
        if channel == "sms":
            frappe.send_sms(receivers=[contact], message=message)
        else:
            frappe.sendmail(
                recipients=[contact],
                subject=f"{partner_name} invited you to Supacharge",
                message=message,
            )
    except Exception as e:
        frappe.log_error(
            f"Failed to send student invite to {contact}: {e}", "Student Invite Send Error"
        )
        frappe.throw(_("Could not send the invite. Please try again."))

    return {"name": doc.name, "code": code, "expires_at": expires_at.isoformat()}


@frappe.whitelist()
def redeem_student_invite(token):
    """Student-side: activate a partner-initiated invite by pairing code
    (P3.2: [token] carries the 6-digit code, single-use, 48h expiry). The
    student signed up through normal onboarding first; redeeming makes them
    the link's student — after which everything behaves exactly as if the
    student had initiated (reports, alerts, discounted rate)."""
    student = frappe.session.user
    link_name = _find_valid_invite(token, {"initiated_by": "Partner"})
    if not link_name:
        frappe.throw(_("This pairing code is invalid, expired, or already used."))

    link = frappe.get_doc("LMS Partner Link", link_name)
    if link.partner == student:
        frappe.throw(_("You cannot redeem your own invite."))
    # Role exclusivity (decision #23), both directions: the redeemer is about
    # to become a student (must not already be a partner), and the partner who
    # sent the invite must not itself be a student.
    enforce_role_exclusivity(student, role_exclusivity.STUDENT)
    enforce_role_exclusivity(link.partner, role_exclusivity.PARTNER)
    # One partner per student, same rule as the student-initiated path.
    if frappe.db.exists("LMS Partner Link", {"student": student, "status": "Active"}):
        frappe.throw(_("You already have an accountability partner."))

    link.student = student
    link.status = "Active"
    link.invite_token = None
    link.invite_expires_at = None
    link.save(ignore_permissions=True)

    return {"partner": link.partner}


# ---------------------------------------------------------------------------
# P3.1 — partner-as-payer (delegated billing)
# ---------------------------------------------------------------------------


def _set_payer(student, payer):
    """Billing responsibility flips only on the caller's own Active link —
    _resolve_student throws a permission error for anything else. This acts
    on the PARTNER'S OWN billing; it grants no capability over the student's
    account (the subscription stays the student's).

    #33: payer capability is enforced HERE, server-side, not merely by
    hiding a toggle — a teacher partner cannot take over payment however
    the call arrives (see rlms.payer_rules). Releasing back to the student
    is always allowed: a link whose relationship changed must never strand
    a student with an unpayable subscription.
    """
    link = _resolve_student(student)
    if payer == "Partner" and not can_pay(link.relationship):
        frappe.throw(
            _("A {0} partner cannot take over payment for a student.").format(
                (link.relationship or "").lower() or _("partner")
            ),
            frappe.PermissionError,
        )
    frappe.db.set_value("LMS Partner Link", link.name, "payer", payer)
    return {"student": link.student, "paid_by_partner": payer == "Partner"}


@frappe.whitelist()
def assume_billing(student=None):
    """Partner-side: take on payment responsibility for a linked student's
    subscription (P3.1 partner-as-payer, delegated billing)."""
    return _set_payer(student, "Partner")


@frappe.whitelist()
def release_billing(student=None):
    """Partner-side: hand payment responsibility back to the student."""
    return _set_payer(student, "Student")


@frappe.whitelist()
def unlink_student(student=None):
    """Partner-side: sever the partner↔student link (P3.1 remove-a-student).

    Only the link goes — the student's own account, history and progress
    are untouched. Billing responsibility returns to the student BEFORE the
    link is revoked, so a revoked link can never leave the partner silently
    billed for a student they no longer see. Scope mirrors the other
    partner-side calls: _resolve_student only ever answers with the
    caller's OWN Active link (permission error otherwise)."""
    link = _resolve_student(student)
    frappe.db.set_value(
        "LMS Partner Link",
        link.name,
        {"payer": "Student", "status": "Revoked"},
    )
    return {"ok": True, "student": link.student}


# ---------------------------------------------------------------------------
# Weekly email digest (opt-in per link)
# ---------------------------------------------------------------------------


def _set_email_digest(student, enabled):
    """The digest flag flips only on the caller's own Active link —
    _resolve_student throws a permission error for anything else. Off by
    default (doctype); the flag gates nothing but an EMAIL of the same
    weekly report the partner dashboard already shows (see rlms.tasks.
    send_partner_weekly_digests), so toggling exposes no new data."""
    link = _resolve_student(student)
    frappe.db.set_value("LMS Partner Link", link.name, "email_digest", 1 if enabled else 0)
    return {"student": link.student, "email_digest": bool(enabled)}


@frappe.whitelist()
def enable_email_digest(student=None):
    """Partner-side: opt in to the weekly progress email for a linked
    student. Sent Sunday evenings by the digest scheduler task."""
    return _set_email_digest(student, True)


@frappe.whitelist()
def disable_email_digest(student=None):
    """Partner-side: stop the weekly progress email for a linked student."""
    return _set_email_digest(student, False)


# ---------------------------------------------------------------------------
# P3.2 — attendance-event sync + threshold-based cross-device alerts
# ---------------------------------------------------------------------------


def _send_push(user, title, body, data=None):
    """Cross-module call into comms' FCM sender (Device Token + Push
    Notification Settings — real infra, confirmed). The composed app name is
    derived from this module's own import path, so the call works under any
    rcore the composer substituted. Push failure never fails the caller:
    the alert row is the durable record; the push is best-effort delivery."""
    app = __name__.split(".")[0]
    try:
        fn = frappe.get_attr(f"{app}.comms.api.notification.send_push_notification")
        fn(user=user, title=title, body=body, data=data or {})
    except Exception as e:
        frappe.log_error(f"Partner alert push to {user} failed: {e}", "Partner Alert Push Error")


def _record_alert(student, alert_type, message, when):
    """One alert row per Active partner of [student], plus an FCM push to
    each. The row is what the partner dashboard lists (cross-device); the
    push is the 'instant' part of §1's instant alerts."""
    partners = frappe.get_all(
        "LMS Partner Link", {"student": student, "status": "Active"}, pluck="partner"
    )
    for partner in partners:
        if not partner:
            continue
        frappe.get_doc(
            {
                "doctype": "LMS Partner Alert",
                "partner": partner,
                "student": student,
                "alert_type": alert_type,
                "message": message,
                "occurred_at": when,
            }
        ).insert(ignore_permissions=True)
        _send_push(partner, "Supacharge", message, {"type": alert_type, "student": student})


@frappe.whitelist()
def record_attendance_event(
    session_id, outcome, data_used_mb=0, seconds_watched=None
):
    """Student-side: syncs one session outcome (the on-device §5 ledger's
    row) to the backend. This is the single sync point that makes the weekly
    report's split/streak/data-usage real AND powers threshold-based partner
    alerts:

    [seconds_watched] is OPTIONAL (presence-with-gaps attendance, #15): how
    many seconds of the session the student actually watched. Absent/None
    means unknown (gap-tolerant — never treated as zero), so existing callers
    that omit it keep working unchanged. Like data_used_mb it merges into the
    per-session row and never downgrades a known value to a smaller one.

    - Alert fires on STREAK BREAK only — the second consecutive skip — never
      on every skip (one skip is normal life; two in a row is the signal).
    - If the trailing window keeps accumulating skips (3 of the last 4
      events), the alert adds a remediation suggestion. Broadcast times are
      fixed per session (Replay Session.scheduled_at; no reschedule mechanism
      exists), so the honest suggestion is the P5 Library recording, which
      unlocks the day after broadcast — not a time-slot picker that doesn't
      exist.
    """
    student = frappe.session.user
    when = now_datetime()
    valid_outcomes = ("Attended", "Skipped Answered", "Skipped Unanswered")
    if outcome not in valid_outcomes:
        frappe.throw(_("Unknown outcome."))

    # #25 server-side guard: an 'Attended' claim is validated against the
    # session's real broadcast time in SERVER time — you cannot have
    # attended a session that hasn't started (forged streaks would steer
    # partner alerts), and a claim far beyond the offline-sync window is a
    # backdate, not a sync. Skips are not time-gated (pre-session skips are
    # legitimate; see time_gates.attendance_claim_permitted's doc).
    # Sessions with no Replay Session row (on-demand content) have no
    # broadcast time to validate against and pass through unchanged.
    if outcome == "Attended":
        scheduled_at = frappe.db.get_value(
            "Replay Session", {"session_id": session_id}, "scheduled_at"
        )
        if scheduled_at and not attendance_claim_permitted(
            frappe.utils.get_datetime(scheduled_at), when
        ):
            frappe.throw(
                _("Attendance for this session cannot be recorded at this time."),
                frappe.PermissionError,
            )

    # Upsert per (student, session): a later, better outcome replaces a skip
    # (matching the on-device ledger's never-downgrade rule), re-syncs of
    # the same outcome don't double-count, and a late data-usage estimate
    # (usage accrues during playback, after the join event synced) merges in.
    existing = frappe.db.get_value(
        "LMS Attendance Event",
        {"student": student, "session_id": session_id},
        ["name", "outcome"],
        as_dict=True,
    )
    if existing:
        rank = {"Skipped Unanswered": 0, "Skipped Answered": 1, "Attended": 2}
        updates = {}
        if rank[outcome] > rank[existing.outcome]:
            updates["outcome"] = outcome
        if data_used_mb:
            updates["data_used_mb"] = data_used_mb
        # Watch time merges like the usage estimate and never downgrades: a
        # fragmented resync reports the fuller total, never a smaller one.
        if seconds_watched:
            prior = (
                frappe.db.get_value(
                    "LMS Attendance Event", existing.name, "seconds_watched"
                )
                or 0
            )
            if seconds_watched > prior:
                updates["seconds_watched"] = seconds_watched
        if updates:
            frappe.db.set_value("LMS Attendance Event", existing.name, updates)
        return {"name": existing.name}

    doc = frappe.get_doc(
        {
            "doctype": "LMS Attendance Event",
            "student": student,
            "session_id": session_id,
            "outcome": outcome,
            "occurred_at": when,
            "data_used_mb": data_used_mb,
            # Optional — omit rather than store 0 so "unknown" stays distinct
            # from "watched zero seconds".
            "seconds_watched": seconds_watched or None,
        }
    )
    doc.insert(ignore_permissions=True)

    if outcome != "Attended":
        _maybe_alert_on_skip(student, session_id, when)

    return {"name": doc.name}


def _maybe_alert_on_skip(student, session_id, when):
    """Query the trailing window, then let the frappe-free threshold rules
    decide (see rlms.alert_rules — that split is what makes the threshold
    unit-testable without a bench). Alert on the 2nd consecutive skip;
    escalate with the Library suggestion when skips keep accumulating."""
    recent = frappe.get_all(
        "LMS Attendance Event",
        {"student": student},
        ["outcome"],
        order_by="occurred_at desc",
        limit_page_length=ALERT_WINDOW,
    )
    # recent[0] is the skip that was just recorded.
    outcomes = [e.outcome for e in recent]
    verdict = evaluate_skip_alert(outcomes)
    if verdict is alert_rules.NONE:
        return

    student_name = frappe.db.get_value("User", student, "full_name") or student
    if verdict == alert_rules.REPEATED:
        skips_in_window = sum(1 for o in outcomes if o != alert_rules.ATTENDED)
        message = (
            f"{student_name} has skipped {skips_in_window} of their last {len(outcomes)} "
            f"sessions. This time slot doesn't seem to be working — session times are "
            f"fixed, but every session's recording is in the Library the next day; "
            f"catching up there might fit better."
        )
    else:
        message = (
            f"{student_name} skipped a second session in a row — their attendance "
            f"streak just broke."
        )
    _record_alert(student, "sessionSkipped", message, when)


@frappe.whitelist()
def alerts(student=None):
    """Partner-side: the cross-device alert feed for the dashboard. Scoped to
    the caller's own linked students, newest first."""
    links = _linked_students()
    students = [link.student for link in links]
    if student:
        if student not in students:
            frappe.throw(_("That student is not linked to this account."), frappe.PermissionError)
        students = [student]
    rows = frappe.get_all(
        "LMS Partner Alert",
        {"partner": frappe.session.user, "student": ["in", students]},
        ["alert_type", "message", "occurred_at", "student"],
        order_by="occurred_at desc",
        limit_page_length=50,
    )
    return {
        "alerts": [
            {
                "type": r.alert_type,
                "message": r.message,
                "at": frappe.utils.get_datetime(r.occurred_at).isoformat(),
                "student_id": r.student,
            }
            for r in rows
        ]
    }
