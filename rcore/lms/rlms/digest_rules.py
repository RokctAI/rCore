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

"""Weekly partner email digest — frappe-free calendar and wording rules.

Opt-in per LMS Partner Link (email_digest flag): once a week an opted-in
partner gets the SAME weekly report the app's partner dashboard shows, as
a plain email — ONE email per partner, a section per student. This module
decides WHICH week a run reports and HOW the report reads;
tasks.send_partner_weekly_digests does the querying and the sending (the
alert_rules.py split — the wording is unit-testable without a
bench/site).

Wording rules (partner-facing, so the house style applies): plain
language, no internal identifiers, no field-name jargon — the email talks
about sessions missed and check-ins answered, never about outcome enums,
and nothing technical ever leaks into it (failures are logged server-side
by the task, not emailed).
"""

from datetime import timedelta

# Rosters up to this size get today's full per-student sections; bigger
# rosters get the compact one-line-per-student digest so a sponsor with
# 50 students doesn't get a wall of prose.
FULL_SECTIONS_MAX = 5

# At this roster size and above, the healthy group collapses to a single
# count line — the email stays readable at 100+ students.
HEALTHY_ROLLUP_FROM = 100

# Soft cap on how many weekly reports the batch task builds for one
# partner in a single run. The email never truncates silently: the task
# passes the overflow as more_students so the digest says so.
PARTNER_REPORT_CAP = 200


def report_week_start(run_date):
    """The Monday of the week [run_date] falls in — the week a digest run
    reports. The scheduler fires Sunday evening (site time), closing out
    the week that began the previous Monday; weekly_report's window is
    [week_start, week_start + 7 days), the same window the app requests."""
    return run_date - timedelta(days=run_date.weekday())


def _plural(count, singular, plural=None):
    return singular if count == 1 else (plural or singular + "s")


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


_FOOTER = (
    "You're getting this weekly digest because you switched it on in "
    "the Supacharge app. You can turn it off there anytime."
)


def _student_section(report):
    """The paragraphs for one student's week — everything between the
    greeting and the footer, starting with the student's own lead-in."""
    student = report.get("student_name") or "Your student"
    scheduled = report.get("sessions_scheduled") or 0
    attended = report.get("sessions_attended") or 0
    answered = report.get("sessions_skipped_answered") or 0
    unanswered = report.get("sessions_skipped_unanswered") or 0
    missed = answered + unanswered

    paragraphs = [f"Here's how {student}'s week on Supacharge went."]

    if not scheduled:
        paragraphs.append(
            "No live sessions were scheduled this week, so there's no "
            "attendance to report."
        )
    else:
        line = (
            f"{student} attended {attended} of the {scheduled} live "
            f"{_plural(scheduled, 'session')} scheduled this week."
        )
        if not missed and attended >= scheduled:
            line += " That's every single one — a great week."
        paragraphs.append(line)
        if missed:
            if answered and unanswered:
                paragraphs.append(
                    f"{missed} {_plural(missed, 'session was', 'sessions were')} "
                    f"missed — {student} answered the quick check-in for "
                    f"{answered} of them, and {unanswered} went by without a word."
                )
            elif answered:
                paragraphs.append(
                    f"{missed} {_plural(missed, 'session was', 'sessions were')} "
                    f"missed, but {student} answered the quick check-in each "
                    f"time — so at least you know they saw it."
                )
            else:
                paragraphs.append(
                    f"{missed} {_plural(missed, 'session was', 'sessions were')} "
                    f"missed without answering the quick check-in. It might be "
                    f"worth asking how things are going."
                )

    streak = report.get("current_streak") or 0
    if streak:
        paragraphs.append(
            f"Current streak: {streak} {_plural(streak, 'session')} attended "
            f"in a row. Worth an encouraging word!"
        )

    # Weekly league standing (one friendly sentence, only when the student
    # actually holds one this week — tasks.py attaches it read-only).
    league = report.get("league") or {}
    if league.get("tier"):
        rank = league.get("rank")
        group = league.get("cohort_size") or 0
        line = f"In this week's league, {student} is in the {league['tier']} tier"
        if rank and group:
            line += f" — {_ordinal(rank)} of {group} in their group"
        paragraphs.append(line + ".")

    scores = report.get("performance_scores") or {}
    if scores:
        lines = ["How this week's quizzes went:"]
        for title in sorted(scores):
            lines.append(f"  - {title}: {scores[title]}%")
        engagement = report.get("engagement_rate_percent") or 0
        lines.append(
            f"{student} answered {engagement}% of the quiz questions they saw."
        )
        paragraphs.append("\n".join(lines))

    data_mb = report.get("data_used_mb") or 0
    if data_mb:
        paragraphs.append(f"Data used this month: about {round(data_mb)} MB.")

    return paragraphs


def _needs_attention(report):
    """Whether a student's week deserves the partner's eye: a missed
    session, an unanswered check-in, or a streak that's gone."""
    scheduled = report.get("sessions_scheduled") or 0
    if not scheduled:
        return False
    attended = report.get("sessions_attended") or 0
    missed = (report.get("sessions_skipped_answered") or 0) + (
        report.get("sessions_skipped_unanswered") or 0
    )
    streak = report.get("current_streak") or 0
    return attended < scheduled or missed > 0 or not streak


def _compact_line(report):
    """One line for one student — name, attended x of y, and the one
    thing worth knowing (streak, or what went wrong)."""
    student = report.get("student_name") or "Your student"
    scheduled = report.get("sessions_scheduled") or 0
    attended = report.get("sessions_attended") or 0
    answered = report.get("sessions_skipped_answered") or 0
    unanswered = report.get("sessions_skipped_unanswered") or 0
    streak = report.get("current_streak") or 0

    if not scheduled:
        return f"- {student}: no live sessions scheduled this week"

    line = f"- {student}: attended {attended} of {scheduled}"
    if unanswered:
        if unanswered == 2 and not answered:
            line += " — missed both check-ins"
        else:
            line += (
                f" — {unanswered} {_plural(unanswered, 'check-in')} "
                "went unanswered"
            )
    elif answered:
        line += " — answered the check-in each time"
    elif attended < scheduled:
        short = scheduled - attended
        line += f" — missed {short} {_plural(short, 'session')}"
    elif not streak:
        line += " — their streak just ended"
    else:
        line += f" — {streak} in a row"
    return line


def render_digest(report, partner_name=""):
    """The digest email for one weekly report (partner.build_weekly_report's
    payload). Returns {"subject", "body"}; body is plain text, paragraphs
    separated by blank lines, quiz scores one per line."""
    student = report.get("student_name") or "Your student"
    paragraphs = [
        f"Hi {partner_name}," if partner_name else "Hi,",
        *_student_section(report),
        _FOOTER,
    ]
    return {
        "subject": f"{student}'s week on Supacharge",
        "body": "\n\n".join(paragraphs),
    }


def render_partner_digest(reports, partner_name="", more_students=0):
    """ONE digest email covering all of a partner's students, students in
    name order, one greeting and one footer. A single-student partner gets
    the same email render_digest produces. Up to FULL_SECTIONS_MAX
    students each get a full section; bigger rosters get one line per
    student, the students needing attention first, and from
    HEALTHY_ROLLUP_FROM students the healthy group collapses to a count.
    more_students is the overflow past the batch task's report cap — when
    set, the email says so rather than truncating silently."""
    if len(reports) == 1 and not more_students:
        return render_digest(reports[0], partner_name=partner_name)

    reports = sorted(reports, key=lambda r: r.get("student_name") or "Your student")
    paragraphs = [f"Hi {partner_name}," if partner_name else "Hi,"]

    if len(reports) <= FULL_SECTIONS_MAX:
        for report in reports:
            paragraphs.extend(_student_section(report))
    else:
        total = len(reports) + more_students
        paragraphs.append(
            f"Here's the week across your {total} students on Supacharge."
        )
        attention = [r for r in reports if _needs_attention(r)]
        healthy = [r for r in reports if not _needs_attention(r)]
        if attention:
            paragraphs.append(
                "\n".join(
                    ["Worth a closer look this week:"]
                    + [_compact_line(r) for r in attention]
                )
            )
        if healthy:
            if total >= HEALTHY_ROLLUP_FROM:
                count = len(healthy)
                lead = "Another" if attention else "All"
                paragraphs.append(
                    f"{lead} {count} {_plural(count, 'student')} had a "
                    "good week — nothing to worry about."
                )
            else:
                heading = (
                    "Everyone else had a good week:"
                    if attention
                    else "Everyone had a good week:"
                )
                paragraphs.append(
                    "\n".join([heading] + [_compact_line(r) for r in healthy])
                )

    if more_students:
        paragraphs.append(
            f"...and {more_students} more "
            f"{_plural(more_students, 'student')} — see the app for everyone."
        )
    paragraphs.append(_FOOTER)
    return {
        "subject": "Your students' week on Supacharge",
        "body": "\n\n".join(paragraphs),
    }
