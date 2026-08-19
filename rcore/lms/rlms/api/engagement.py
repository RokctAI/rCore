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

"""Student-facing engagement surfaces (decision #42 gap 4): visible
streaks and weekly leagues.

Same split as partner.py/alert_rules.py: this module queries and
persists, the frappe-free `streak_rules` / `league_rules` modules decide.
The server is the SOLE authority on points, ranks, and tiers — the app
only reads the answers from these endpoints.

League mechanics (rules module documents the weights/ladder):
- a student joins the current week's league lazily on first read
  (_ensure_membership) — new students start in Bronze, in the first
  cohort with space;
- live standings are COMPUTED ON READ from the week's real events
  (attendance, quiz results, lesson completions), never stored mid-week;
- `close_league_week` (System Manager, cron-able) snapshots final points
  and rank onto the week's membership rows and seeds next week's rows
  with promotions/demotions applied.
"""

import frappe
from frappe.utils import add_days, get_datetime, getdate, nowdate

from .. import league_rules, streak_rules

#: How far back the streak query looks. Bounded for the same reason the
#: partner report bounds it: the counter is capped by history we fetch,
#: and 1000 sessions is years of attendance.
STREAK_WINDOW = 1000


@frappe.whitelist()
def my_streak():
    """The caller's live-session attendance streak: current consecutive
    attended sessions plus their best-ever run. Reads the same
    LMS Attendance Event history the partner weekly report reads."""
    rows = frappe.get_all(
        "LMS Attendance Event",
        {"student": frappe.session.user},
        ["outcome"],
        order_by="occurred_at desc",
        limit_page_length=STREAK_WINDOW,
    )
    streaks = streak_rules.compute_streaks([r.outcome for r in rows])
    return {"current_streak": streaks["current"], "best_streak": streaks["best"]}


def _current_week_start():
    return league_rules.week_start_of(getdate(nowdate()))


def _week_bounds(week_start):
    start = get_datetime(week_start)
    return start, add_days(start, 7)


def _weekly_points(student, week_start):
    """A student's engagement points for one week, from real synced events.
    Weights live in league_rules (attendance 10 / quiz 5 / lesson 5)."""
    start, end = _week_bounds(week_start)
    attended = frappe.db.count(
        "LMS Attendance Event",
        {
            "student": student,
            "outcome": "Attended",
            "occurred_at": ["between", [start, end]],
        },
    )
    quizzes = frappe.db.count(
        "LMS Lesson Quiz Result",
        {
            "member": student,
            "outcome": ["in", ["Correct", "Incorrect"]],
            "creation": ["between", [start, end]],
        },
    )
    # `modified` rather than `creation`: save_progress flips an existing
    # row to complete, so the completion lands in the week it happened.
    lessons = frappe.db.count(
        "LMS Course Progress",
        {
            "member": student,
            "is_complete": 1,
            "modified": ["between", [start, end]],
        },
    )
    return league_rules.weekly_points(
        attended=attended, quizzes_completed=quizzes, lessons_completed=lessons
    )


def _ensure_membership(student, week_start):
    """The student's membership row for [week_start], created lazily on
    first read. New students start in Bronze; a student whose previous
    week was never closed carries their tier forward unchanged (close
    seeds next week's rows itself, promotions/demotions applied)."""
    existing = frappe.db.get_value(
        "LMS League Membership",
        {"student": student, "week_start": week_start},
        ["name", "tier", "cohort"],
        as_dict=True,
    )
    if existing:
        return existing

    prior = frappe.get_all(
        "LMS League Membership",
        {"student": student, "week_start": ["<", week_start]},
        ["tier"],
        order_by="week_start desc",
        limit_page_length=1,
    )
    tier = prior[0].tier if prior else league_rules.TIERS[0]
    cohort = _cohort_with_space(week_start, tier)
    doc = frappe.get_doc(
        {
            "doctype": "LMS League Membership",
            "student": student,
            "week_start": week_start,
            "tier": tier,
            "cohort": cohort,
            "points": 0,
        }
    )
    doc.insert(ignore_permissions=True)
    return frappe._dict(name=doc.name, tier=tier, cohort=cohort)


def _cohort_with_space(week_start, tier):
    """First cohort id in (week, tier) with a free seat, else a new one.
    Cohort ids are per-(week, tier) ordinals ("1", "2", ...)."""
    rows = frappe.get_all(
        "LMS League Membership",
        {"week_start": week_start, "tier": tier},
        ["cohort"],
        limit_page_length=0,
    )
    counts = {}
    for row in rows:
        counts[row.cohort] = counts.get(row.cohort, 0) + 1
    for cohort in sorted(counts, key=lambda c: (len(c), c)):
        if counts[cohort] < league_rules.COHORT_SIZE:
            return cohort
    return str(len(counts) + 1)


def _cohort_standings(week_start, tier, cohort):
    """Live ranked standings for one cohort, computed on read."""
    members = frappe.get_all(
        "LMS League Membership",
        {"week_start": week_start, "tier": tier, "cohort": cohort},
        ["student"],
        limit_page_length=0,
    )
    points_by_student = {
        m.student: _weekly_points(m.student, week_start) for m in members
    }
    return league_rules.rank_standings(points_by_student)


@frappe.whitelist()
def my_league():
    """The caller's league summary for the current week: tier, cohort,
    live points and rank, plus the ladder so the client renders tier
    progress without hardcoding it."""
    student = frappe.session.user
    week_start = _current_week_start()
    membership = _ensure_membership(student, week_start)
    standings = _cohort_standings(week_start, membership.tier, membership.cohort)
    mine = next((s for s in standings if s["student"] == student), None)
    return {
        "week_start": str(week_start),
        "tier": membership.tier,
        "cohort": membership.cohort,
        "points": mine["points"] if mine else 0,
        "rank": mine["rank"] if mine else None,
        "cohort_size": len(standings),
        "tiers": league_rules.TIERS,
        "promote_top": league_rules.PROMOTE_TOP,
        "demote_bottom": league_rules.DEMOTE_BOTTOM,
    }


@frappe.whitelist()
def league_standings():
    """The caller's cohort, ranked, for the current week. Display names
    are first name + last initial only — cohort-mates see each other's
    points, never each other's identity beyond that."""
    student = frappe.session.user
    week_start = _current_week_start()
    membership = _ensure_membership(student, week_start)
    standings = _cohort_standings(week_start, membership.tier, membership.cohort)
    entries = []
    for row in standings:
        full_name = frappe.db.get_value("User", row["student"], "full_name")
        entries.append(
            {
                "display_name": league_rules.display_name(full_name),
                "points": row["points"],
                "rank": row["rank"],
                "is_me": row["student"] == student,
            }
        )
    return {
        "week_start": str(week_start),
        "tier": membership.tier,
        "cohort": membership.cohort,
        "promote_top": league_rules.PROMOTE_TOP,
        "demote_bottom": league_rules.DEMOTE_BOTTOM,
        "standings": entries,
    }


def student_week_league(student, week_start):
    """One student's league summary for [week_start], READ-ONLY: unlike
    my_league, a third-party read never creates a membership row — a
    partner looking in must not enrol the student. None when the student
    has no membership for the week; callers show nothing rather than
    inventing Bronze. Authorization is the CALLER's job (the partner
    endpoint below resolves the caller's own links; tasks.py iterates
    Active links by query — the build_weekly_report split)."""
    membership = frappe.db.get_value(
        "LMS League Membership",
        {"student": student, "week_start": week_start},
        ["tier", "cohort"],
        as_dict=True,
    )
    if not membership:
        return None
    standings = _cohort_standings(week_start, membership.tier, membership.cohort)
    mine = next((s for s in standings if s["student"] == student), None)
    return {
        "tier": membership.tier,
        "points": mine["points"] if mine else 0,
        "rank": mine["rank"] if mine else None,
        "cohort_size": len(standings),
    }


@frappe.whitelist()
def partner_students_league():
    """Partner-side: where each of the caller's OWN linked students stands
    in this week's league — tier, live points, rank, cohort size. Scope
    follows partner.py's active-link pattern (_linked_students throws a
    permission error for an unlinked account), and no cohort-mate of any
    student is ever exposed — only the linked students themselves."""
    from .partner import _linked_students

    week_start = _current_week_start()
    students = []
    for link in _linked_students():
        students.append(
            {
                "student": link.student,
                "league": student_week_league(link.student, week_start),
            }
        )
    return {"week_start": str(week_start), "students": students}


@frappe.whitelist()
def close_league_week(week_start=None):
    """Week close (System Manager only; call from a weekly cron or by
    hand): snapshot final points + rank onto [week_start]'s membership
    rows, then seed NEXT week's rows with promotions/demotions applied.
    Defaults to the most recently ended week. Idempotent per week — rows
    already marked closed are skipped."""
    frappe.only_for("System Manager")

    if week_start:
        week_start = league_rules.week_start_of(getdate(week_start))
    else:
        week_start = league_rules.week_start_of(add_days(getdate(nowdate()), -7))
    next_week = add_days(week_start, 7)

    rows = frappe.get_all(
        "LMS League Membership",
        {"week_start": week_start, "closed": 0},
        ["name", "student", "tier", "cohort"],
        limit_page_length=0,
    )
    if not rows:
        return {"week_start": str(week_start), "closed": 0, "seeded": 0}

    cohorts = {}
    for row in rows:
        cohorts.setdefault((row.tier, row.cohort), []).append(row)

    landing = {}  # next tier -> [(points, student)] for seeding order
    closed = 0
    for (tier, _cohort_id), members in cohorts.items():
        points_by_student = {
            m.student: _weekly_points(m.student, week_start) for m in members
        }
        standings = league_rules.rank_standings(points_by_student)
        outcomes = league_rules.close_cohort(standings, tier)
        by_student = {o["student"]: o for o in outcomes}
        for member in members:
            outcome = by_student[member.student]
            frappe.db.set_value(
                "LMS League Membership",
                member.name,
                {
                    "points": outcome["points"],
                    "final_rank": outcome["rank"],
                    "closed": 1,
                },
            )
            closed += 1
            landing.setdefault(outcome["next_tier"], []).append(
                (-outcome["points"], member.student)
            )

    seeded = 0
    for tier, entries in landing.items():
        students = [student for _neg, student in sorted(entries)]
        for index, cohort in enumerate(
            league_rules.assign_cohorts(students), start=1
        ):
            for student in cohort:
                if frappe.db.exists(
                    "LMS League Membership",
                    {"student": student, "week_start": next_week},
                ):
                    continue
                frappe.get_doc(
                    {
                        "doctype": "LMS League Membership",
                        "student": student,
                        "week_start": next_week,
                        "tier": tier,
                        "cohort": str(index),
                        "points": 0,
                    }
                ).insert(ignore_permissions=True)
                seeded += 1

    return {"week_start": str(week_start), "closed": closed, "seeded": seeded}
