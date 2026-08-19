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

"""Scheduled rlms tasks (the replay tasks.py pattern: manifest
``scheduler_events`` -> thin task functions; the deciding lives in the
frappe-free rules/api modules, this file is only the cron entry point).

Partner email digests — the opt-in email leg of §1's Sunday report.
Weekly (Sunday 18:00 site time; the site timezone is
Africa/Johannesburg), every partner with an Active, email_digest-flagged
LMS Partner Link gets ONE email covering all their opted-in students —
the same weekly report the partner dashboard shows, rendered as a
plain-language email via frappe.sendmail. Which week a run reports and
how the email reads live in the frappe-free digest_rules module
(SDK_README §4).

Per-partner isolation: one partner's failure (bad address, transient
mail error, missing user) is logged server-side and never aborts the
rest of the batch — and no error detail is ever emailed to anyone.
"""

from html import escape as escape_html

import frappe
from frappe.utils import get_datetime, now_datetime

from . import digest_rules
from .api.engagement import close_league_week, student_week_league
from .api.partner import build_weekly_report


def send_partner_weekly_digests():
    """Weekly scheduler task: email the week's report to every opted-in
    partner — ONE email per partner covering every Active student link
    (full sections for small rosters, compact lines at scale)."""
    links = frappe.get_all(
        "LMS Partner Link",
        {"status": "Active", "email_digest": 1},
        ["name", "student", "partner"],
    )
    week_start = get_datetime(
        digest_rules.report_week_start(now_datetime().date())
    )
    students_by_partner = {}
    for link in links:
        if not link.partner or not link.student:
            continue
        students = students_by_partner.setdefault(link.partner, [])
        if link.student not in students:
            students.append(link.student)
    sent = 0
    for partner, students in students_by_partner.items():
        try:
            # Soft cap per partner: building hundreds of reports for one
            # partner must not eat the whole scheduler run. The email
            # names the overflow — it never truncates silently.
            more_students = 0
            if len(students) > digest_rules.PARTNER_REPORT_CAP:
                more_students = len(students) - digest_rules.PARTNER_REPORT_CAP
                students = students[: digest_rules.PARTNER_REPORT_CAP]
                frappe.log_error(
                    f"Partner {partner} has {len(students) + more_students} "
                    f"digest students; capped this run's report building at "
                    f"{digest_rules.PARTNER_REPORT_CAP} and told them about "
                    f"the {more_students} more in the email.",
                    "Partner Digest Cap",
                )
            reports = []
            for student in students:
                report = build_weekly_report(student, week_start)
                # The digest week (Monday..Sunday) IS the league week, so
                # the standing rides along when the student has one —
                # read-only, never enrolling them (student_week_league).
                league = student_week_league(student, week_start.date())
                if league:
                    report["league"] = league
                reports.append(report)
            partner_name = (
                frappe.db.get_value("User", partner, "first_name") or ""
            )
            digest = digest_rules.render_partner_digest(
                reports,
                partner_name=partner_name,
                more_students=more_students,
            )
            frappe.sendmail(
                recipients=[partner],
                subject=digest["subject"],
                # The body is plain text; sendmail renders HTML, so escape
                # it and let line breaks become <br> — nothing else is markup.
                message=escape_html(digest["body"]).replace("\n", "<br>\n"),
            )
            sent += 1
        except Exception as e:
            frappe.log_error(
                f"Weekly digest for partner {partner} failed: {e}",
                "Partner Digest Error",
            )
    if sent:
        frappe.db.commit()
    return sent


def close_last_league_week():
    """Weekly league close (manifest scheduler_events cron, early Monday
    morning site time): snapshot final points + ranks for the week that
    just ended and seed the new week with promotions/demotions applied.

    Delegates entirely to the whitelisted ``close_league_week`` endpoint,
    which is idempotent per week (rows already marked closed are skipped;
    existing next-week rows are never re-seeded), so a scheduler retry or
    a manual run in the same week is harmless. The scheduler runs as
    Administrator, which satisfies the endpoint's System Manager guard.
    """
    return close_league_week()
