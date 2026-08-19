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

"""Shareable per-subject Readiness Score (decision #42, gap 5): a verifiable,
WhatsApp-shareable credential generated from analytics the backend already
tracks — the productized, per-subject successor to the internal
end-of-Holiday-Programme "Grade Readiness Report" (business doc §2), and the
sponsor-report currency for the CSI channel (gap 3).

Split of responsibilities (matching partner.py + alert_rules.py):
- `rlms.readiness_rules` owns the FORMULA (frappe-free, unit-tested);
- `rlms.readiness_card` owns the shareable SVG markup (frappe-free,
  unit-tested — including its privacy allowlist);
- this module owns the querying, the token mint, and the serving.

The SERVER is the sole authority for the score: the app renders what these
endpoints answer and never computes a score itself.

PRIVACY (hard constraint): the two guest surfaces — verify + card — expose
ONLY first name, subject, score (and its derived band), and the score's
month/year. No email, phone, school, grade, full name, or user id ever
crosses them. The share row snapshots the first name at mint time, so the
guest path never reads the User table at all.
"""

import json
import secrets

import frappe
from frappe import _
from frappe.utils import now_datetime

from .. import readiness_rules
from ..readiness_card import render_card_svg

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

#: 32 url-safe chars (~192 bits) — unguessable, still short enough for a
#: WhatsApp-pasted URL.
TOKEN_BYTES = 24


def _first_name_of(user):
    """The student's FIRST name only, for the share surfaces. Falls back to
    the first word of full_name, then a neutral label — never an email."""
    row = frappe.db.get_value("User", user, ["first_name", "full_name"], as_dict=True)
    if row:
        if row.first_name:
            return row.first_name.strip().split()[0]
        if row.full_name:
            return row.full_name.strip().split()[0]
    return "Student"


def _subject_scores(user):
    """Per-subject Readiness Scores for [user], computed from the analytics
    doctypes that already exist (see readiness_rules for the formula):

    - LMS Enrollment (progress %) grouped by the course's subject → coverage;
    - LMS Lesson Quiz Result outcomes on the subject's lessons → mastery;
    - LMS Attendance Event outcomes on the subject's broadcast sessions
      (via Course Lesson.session_id) → consistency.

    Subjects with no computable component (readiness_rules answers None)
    are reported with score None so the app can show "not enough activity
    yet" rather than a fake zero.
    """
    enrollments = frappe.get_all(
        "LMS Enrollment", {"member": user}, ["course", "progress"]
    )
    if not enrollments:
        return []

    course_names = [e.course for e in enrollments]
    courses = frappe.get_all(
        "LMS Course",
        {"name": ["in", course_names], "published": 1},
        ["name", "subject"],
    )
    subject_of_course = {c.name: c.subject for c in courses if c.subject}

    by_subject = {}
    for enrollment in enrollments:
        subject = subject_of_course.get(enrollment.course)
        if not subject:
            continue
        bucket = by_subject.setdefault(subject, {"courses": [], "progress": []})
        bucket["courses"].append(enrollment.course)
        bucket["progress"].append(enrollment.progress or 0)

    results = []
    for subject in sorted(by_subject):
        bucket = by_subject[subject]
        lessons = frappe.get_all(
            "Course Lesson",
            {"course": ["in", bucket["courses"]]},
            ["name", "session_id"],
        )

        mastery = None
        if lessons:
            quiz_rows = frappe.get_all(
                "LMS Lesson Quiz Result",
                {"member": user, "lesson": ["in", [l.name for l in lessons]]},
                ["outcome"],
            )
            mastery = readiness_rules.mastery_component(
                correct=sum(1 for r in quiz_rows if r.outcome == "Correct"),
                incorrect=sum(1 for r in quiz_rows if r.outcome == "Incorrect"),
                skipped=sum(1 for r in quiz_rows if r.outcome == "Skipped"),
            )

        coverage = readiness_rules.coverage_component(bucket["progress"])

        consistency = None
        session_ids = [l.session_id for l in lessons if l.session_id]
        if session_ids:
            events = frappe.get_all(
                "LMS Attendance Event",
                {"student": user, "session_id": ["in", session_ids]},
                ["outcome"],
            )
            consistency = readiness_rules.consistency_component(
                attended=sum(1 for e in events if e.outcome == "Attended"),
                skipped_answered=sum(1 for e in events if e.outcome == "Skipped Answered"),
                skipped_unanswered=sum(
                    1 for e in events if e.outcome == "Skipped Unanswered"
                ),
            )

        verdict = readiness_rules.readiness_score(mastery, coverage, consistency)
        results.append(
            {
                "subject": subject,
                "score": verdict["score"] if verdict else None,
                "band": verdict["band"] if verdict else None,
                "components": verdict["components"] if verdict else {},
            }
        )
    return results


@frappe.whitelist()
def my_readiness():
    """The signed-in student's per-subject Readiness Scores, computed live
    from current analytics. The as_of month/year stamps what period a share
    minted now would carry."""
    now = now_datetime()
    return {
        "as_of": {"month": now.month, "year": now.year},
        "subjects": _subject_scores(frappe.session.user),
    }


def _method_url(method_name, token):
    """Absolute /api/v1/method URL for a sibling endpoint in this module, built
    from the module's own runtime dotted path — correct in any composed app
    without hardcoding the host app's name.

    Stays a DIRECT dotted URL, not a platform-gateway cmd: these are share
    links (verify page, card image) opened by a browser as plain GETs, which
    the gateway's JSON {"cmd", "payload"} POST envelope cannot serve."""
    return frappe.utils.get_url(
        "/api/v1/method/{0}.{1}?token={2}".format(__name__, method_name, token)
    )


@frappe.whitelist()
def create_share(subject):
    """Mint a shareable snapshot of the caller's CURRENT score for [subject].

    Freezes score/band/components plus the student's first name into an
    LMS Readiness Share row keyed by a cryptographically random token, and
    answers the verify link, the card image link, and a ready-to-paste
    WhatsApp message. Every call mints a fresh token (shares are cheap and
    independently revocable); a share never updates after minting — it is a
    snapshot, not a live view.
    """
    user = frappe.session.user
    subject = (subject or "").strip()
    if not subject:
        frappe.throw(_("Subject is required."))

    match = next(
        (s for s in _subject_scores(user) if s["subject"] == subject), None
    )
    if not match:
        frappe.throw(_("You are not enrolled in {0}.").format(subject))
    if match["score"] is None:
        frappe.throw(
            _(
                "Not enough activity in {0} yet to compute a Readiness Score. "
                "Attend sessions and answer exercise questions first."
            ).format(subject)
        )

    token = secrets.token_urlsafe(TOKEN_BYTES)
    now = now_datetime()
    first_name = _first_name_of(user)
    frappe.get_doc(
        {
            "doctype": "LMS Readiness Share",
            "student": user,
            "first_name": first_name,
            "subject": subject,
            "score": match["score"],
            "band": match["band"],
            "components_json": json.dumps(match["components"]),
            "period_month": now.month,
            "period_year": now.year,
            "token": token,
            "created_on": now,
            "revoked": 0,
        }
    ).insert(ignore_permissions=True)

    verify_url = _method_url("verify", token)
    card_url = _method_url("card", token)
    month_label = "{0} {1}".format(MONTH_NAMES[now.month - 1], now.year)
    return {
        "token": token,
        "subject": subject,
        "score": match["score"],
        "band": match["band"],
        "verify_url": verify_url,
        "card_url": card_url,
        # Ready-to-paste share text. First name only — the sharer may add
        # more themselves, but the server never seeds anything beyond the
        # public verify surface.
        "whatsapp_text": (
            "{0}'s Supacharge Readiness Score for {1}: {2}/100 ({3}, {4}). "
            "Verify: {5}"
        ).format(
            first_name, subject, match["score"], match["band"], month_label, verify_url
        ),
    }


def _live_share(token):
    """Resolve a token to its share row, treating revoked as absent. Guest
    path: reads ONLY the snapshot row, never the User table."""
    token = (token or "").strip()
    if not token:
        return None
    row = frappe.db.get_value(
        "LMS Readiness Share",
        {"token": token},
        ["first_name", "subject", "score", "band", "period_month", "period_year", "revoked"],
        as_dict=True,
    )
    if not row or row.revoked:
        return None
    return row


@frappe.whitelist(allow_guest=True)
def verify(token):
    """PUBLIC verify surface for a shared score. Answers ONLY: first name,
    subject, score, band, month/year (the decision #42 privacy minimum —
    no email, phone, school, grade, full name, or user id). Unknown and
    revoked tokens answer the same {"valid": false} so the endpoint leaks
    nothing about which tokens ever existed."""
    row = _live_share(token)
    if not row:
        return {"valid": False}
    return {
        "valid": True,
        "first_name": row.first_name or "Student",
        "subject": row.subject,
        "score": int(row.score),
        "band": row.band,
        "month": int(row.period_month) if row.period_month else None,
        "year": int(row.period_year) if row.period_year else None,
    }


@frappe.whitelist(allow_guest=True)
def card(token):
    """PUBLIC shareable card: the snapshot rendered as a self-contained SVG
    (readiness_card — no external assets, no scripts), served inline so chat
    apps and browsers preview it. Same privacy allowlist as verify; unknown/
    revoked tokens 404."""
    row = _live_share(token)
    if not row:
        raise frappe.DoesNotExistError(_("This Readiness Score card is not available."))

    month_label = ""
    if row.period_month and row.period_year:
        month_label = "{0} {1}".format(
            MONTH_NAMES[int(row.period_month) - 1], row.period_year
        )
    svg = render_card_svg(
        first_name=row.first_name or "Student",
        subject=row.subject,
        score=int(row.score),
        band=row.band or "",
        month_label=month_label,
    )
    frappe.local.response.filename = "readiness-score.svg"
    frappe.local.response.filecontent = svg
    frappe.local.response.type = "binary"
    frappe.local.response.display_content_as = "inline"


@frappe.whitelist()
def revoke_share(token):
    """Owner-side kill switch: revoking stops the verify link and card from
    resolving (the row stays for audit). Only the share's own student may
    revoke it; unknown tokens and other students' tokens answer the same
    error so this endpoint cannot be used to probe token existence."""
    user = frappe.session.user
    name = frappe.db.get_value(
        "LMS Readiness Share", {"token": (token or "").strip(), "student": user}, "name"
    )
    if not name:
        frappe.throw(_("No such share."))
    frappe.db.set_value("LMS Readiness Share", name, "revoked", 1)
    return {"revoked": True}
