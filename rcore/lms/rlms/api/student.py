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

"""Student profile backend — currently the student's own grade, the shared
prerequisite two features hit independently (lms/docs/student-grade-brief.md):
Holiday Programme grade logic (next-grade preview = grade + 1, term revision
= this grade's term lessons) and course-catalog grade filtering. Grade lives
on `LMS Student Profile` (one row per user), NOT on the core User — the rlms
module stays self-contained, no host-app schema mutation.

Yearly rollover (decided: PROMPT-TO-CONFIRM, never automatic): the SA
academic year is the calendar year, so a grade confirmed in a previous year
is stale come January — but auto-incrementing would be wrong for repeating
students and meaningless past matric (grade 12 is final). my_grade therefore
reports needs_confirmation + a suggested next grade, and the client asks the
student to confirm; nothing changes until they answer set_grade.
"""

import re
from collections import Counter

import frappe
from frappe import _
from frappe.utils import nowdate, today

from .. import role_exclusivity
from .partner import enforce_role_exclusivity

# Kept in sync with lms_student_profile.py's validate() — api/ and doctype/
# code deliberately don't import each other in this module (matching every
# other rlms api file), so the range lives in both places.
MIN_GRADE = 1
MAX_GRADE = 12

# Display-stable curriculum strings (school-capture brief, curriculum
# refinement) — kept in sync with lms_sdk's kSelectableCurricula
# (known_schools.dart) and lms_student_profile.py's validate().
CURRICULA = ("CAPS", "IEB", "Cambridge", "US Common Core")


def _profile(user):
    return frappe.db.get_value(
        "LMS Student Profile",
        {"user": user},
        ["name", "grade", "grade_confirmed_on", "school", "curriculum", "maths_track"],
        as_dict=True,
    )


@frappe.whitelist()
def my_grade():
    """The current student's grade, plus rollover state.

    - grade: the stored grade, or null when never captured (the client shows
      the first-time capture prompt).
    - needs_confirmation: the grade was last confirmed in a previous calendar
      year — January rollover is due, ask the student to confirm.
    - suggested_grade: what to preselect in the confirm prompt (grade + 1,
      capped at 12 — a matric student confirms 12 again or leaves).
    """
    row = _profile(frappe.session.user)
    if not row or not row.grade:
        return {"grade": None, "needs_confirmation": False, "suggested_grade": None}

    current_year = frappe.utils.getdate(nowdate()).year
    confirmed_year = (
        frappe.utils.getdate(row.grade_confirmed_on).year
        if row.grade_confirmed_on
        else None
    )
    stale = confirmed_year is None or confirmed_year < current_year
    return {
        "grade": int(row.grade),
        "needs_confirmation": stale,
        "suggested_grade": min(int(row.grade) + 1, MAX_GRADE) if stale else None,
    }


@frappe.whitelist()
def set_grade(grade):
    """Sets (or re-confirms) the student's own grade and stamps the
    confirmation date — the single write behind first-time capture, the
    profile-settings field, and the January rollover confirmation. Signup/
    onboarding flows call this same endpoint after account creation."""
    try:
        grade = int(grade)
    except (TypeError, ValueError):
        frappe.throw(_("Grade must be a number."))
    if not (MIN_GRADE <= grade <= MAX_GRADE):
        frappe.throw(_("Grade must be between {0} and {1}.").format(MIN_GRADE, MAX_GRADE))

    user = frappe.session.user
    # Role exclusivity (decision #23): a grade profile is a student footprint,
    # so an accountability-partner account may not acquire one — this write
    # path would otherwise mint the student persona with zero enforcement.
    enforce_role_exclusivity(user, role_exclusivity.STUDENT)
    row = _profile(user)
    if row:
        frappe.db.set_value(
            "LMS Student Profile",
            row.name,
            {"grade": grade, "grade_confirmed_on": today()},
        )
    else:
        frappe.get_doc(
            {
                "doctype": "LMS Student Profile",
                "user": user,
                "grade": grade,
                "grade_confirmed_on": today(),
            }
        ).insert(ignore_permissions=True)

    return {"grade": grade}


# ---------------------------------------------------------------------------
# School capture — school + derived curriculum (school-capture brief)
# ---------------------------------------------------------------------------


def _school_key(name):
    """Normalisation for DEDUPE ONLY, never for storage or display: lowercase,
    punctuation stripped, whitespace collapsed — so "St Johns" and
    "St. John's" group as one school. Stored values stay verbatim; the most
    common original spelling represents each group in known_schools."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", name)).strip().lower()


@frappe.whitelist()
def my_school():
    """The current student's school + derived curriculum.

    - school: the stored name verbatim, or null when never captured (the
      client shows the first-time capture prompt).
    - curriculum: the curriculum derived from the school pick (matched
      suggestion pool, or the confirmed CAPS fallback), null until captured.
    """
    row = _profile(frappe.session.user)
    if not row or not row.school:
        return {"school": None, "curriculum": None}
    return {"school": row.school, "curriculum": row.curriculum or None}


@frappe.whitelist()
def set_school(school, curriculum):
    """Sets the student's school and the curriculum derived from that pick
    (matched pool's curriculum, or the confirmed CAPS fallback) — the single
    write behind first-time capture and the profile-settings field. Signup/
    onboarding flows call this same endpoint after account creation; the
    client treats it as best-effort on top of its offline-first KV cache."""
    school = (school or "").strip()
    if not school:
        frappe.throw(_("School name is required."))
    if curriculum not in CURRICULA:
        frappe.throw(
            _("Curriculum must be one of: {0}.").format(", ".join(CURRICULA))
        )

    user = frappe.session.user
    # Role exclusivity (decision #23): same student-footprint guard as
    # set_grade — a partner account can't become a student via school capture.
    enforce_role_exclusivity(user, role_exclusivity.STUDENT)
    row = _profile(user)
    if row:
        frappe.db.set_value(
            "LMS Student Profile",
            row.name,
            {"school": school, "curriculum": curriculum},
        )
    else:
        frappe.get_doc(
            {
                "doctype": "LMS Student Profile",
                "user": user,
                "school": school,
                "curriculum": curriculum,
            }
        ).insert(ignore_permissions=True)

    return {"school": school, "curriculum": curriculum}


@frappe.whitelist()
def known_schools(curriculum, limit=None):
    """Distinct school names other students have entered under a curriculum —
    the server-side accumulated pool behind the app's suggest-as-you-type
    AccumulatedSchoolSuggestionSource (seed lists stay client-side; this
    serves only what students actually typed/picked).

    Spelling variants dedupe on the normalised key (_school_key) and each
    group answers with its most common original spelling, ordered most-seen
    first then alphabetically — so "St. John's" and "St Johns" arrive as one
    suggestion, spelled the way most students spelled it.

    [limit] optionally caps the answer to the first N ranked names (the
    head is the useful part — most-seen first), so the tail never ships to
    the client. The client's AccumulatedSchoolSuggestionSource keeps its
    own identical cap as defence in depth. Omitted/invalid = uncapped,
    exactly the pre-limit behaviour.
    """
    rows = frappe.get_all(
        "LMS Student Profile",
        {"curriculum": curriculum, "school": ["!=", ""]},
        pluck="school",
    )
    groups = {}
    for name in rows:
        name = (name or "").strip()
        key = _school_key(name) if name else ""
        if not key:
            continue
        groups.setdefault(key, Counter())[name] += 1

    ranked = sorted(
        (
            (sum(spellings.values()), spellings.most_common(1)[0][0])
            for spellings in groups.values()
        ),
        key=lambda pair: (-pair[0], pair[1].lower()),
    )
    names = [name for _, name in ranked]
    try:
        limit = int(limit) if limit is not None else None
    except (TypeError, ValueError):
        limit = None
    if limit and limit > 0:
        names = names[:limit]
    return names


# ---------------------------------------------------------------------------
# Product log #27 — subscription history periods + entitlement resolution
# ---------------------------------------------------------------------------

from .. import plan_rules  # noqa: E402
from ..entitlements import entitlement_verdict, skills_entitled  # noqa: E402


def assistant_chat_allowed(user):
    """Whether [user]'s plan includes the in-lesson chat assistant: the
    newest billing record covering today whose plan carries an
    `assistant_chat` flag decides (plan_rules.assistant_chat_from_records).
    FAIL-OPEN by decision — no plan info resolvable, or any lookup failure,
    allows: availability decisions default to not breaking paying students.
    Diagnostics go to the server log, never to the student."""
    try:
        today = frappe.utils.getdate(nowdate())
        rows = frappe.get_all(
            "LMS Billing Record",
            filters={"student": user},
            fields=["plan", "period_start", "period_end"],
            order_by="charged_at desc",
            limit_page_length=50,
        )
        records = []
        for row in rows:
            flag = (
                frappe.db.get_value("LMS Plan", row.plan, "assistant_chat")
                if row.plan
                else None
            )
            records.append(
                {
                    "assistant_chat": flag,
                    "period_start": frappe.utils.getdate(row.period_start)
                    if row.period_start
                    else None,
                    "period_end": frappe.utils.getdate(row.period_end)
                    if row.period_end
                    else None,
                }
            )
        return plan_rules.assistant_chat_from_records(records, today)
    except Exception as e:
        frappe.log_error(
            f"assistant_chat plan lookup failed for {user}: {e}", "LMS Billing"
        )
        return True


def holiday_access_for(user):
    """[user]'s Holiday Programme access level (Full / First Week / None):
    the newest billing record covering today whose plan carries a
    `holiday_access` level decides (plan_rules.holiday_access_from_records);
    a One-Off Programme purchase is always Full for its window. FAIL-OPEN
    like the chat gate — no plan info resolvable, or any lookup failure,
    answers Full. Diagnostics go to the server log, never to the student."""
    try:
        today = frappe.utils.getdate(nowdate())
        rows = frappe.get_all(
            "LMS Billing Record",
            filters={"student": user},
            fields=["plan", "period_start", "period_end"],
            order_by="charged_at desc",
            limit_page_length=50,
        )
        records = []
        for row in rows:
            level = kind = None
            if row.plan:
                values = frappe.db.get_value(
                    "LMS Plan", row.plan, ["holiday_access", "kind"]
                )
                if values:
                    level, kind = values
            records.append(
                {
                    "holiday_access": level,
                    "kind": kind,
                    "period_start": frappe.utils.getdate(row.period_start)
                    if row.period_start
                    else None,
                    "period_end": frappe.utils.getdate(row.period_end)
                    if row.period_end
                    else None,
                }
            )
        return plan_rules.holiday_access_from_records(records, today)
    except Exception as e:
        frappe.log_error(
            f"holiday_access plan lookup failed for {user}: {e}", "LMS Billing"
        )
        return plan_rules.HOLIDAY_ACCESS_FULL


def get_periods(user):
    """The user's covered subscription stretches, as (start, end) date pairs
    (end None = still open), for rlms.entitlements' pure rules. Shared by
    my_entitlements below and course.get_lesson_session's serving gate."""
    rows = frappe.get_all(
        "LMS Subscription Period",
        {"student": user},
        ["start_date", "end_date"],
    )
    return [
        (frappe.utils.getdate(r.start_date), frappe.utils.getdate(r.end_date) if r.end_date else None)
        for r in rows
        if r.start_date
    ]


@frappe.whitelist()
def my_entitlements():
    """The app-queryable entitlement summary (product log #27):

    - active: an open/current period covers today — gates skills (every
      active subscriber gets ALL grades' skills, always) and live content.
    - periods: the covered date ranges, so the Library can mark which
      back-catalog lessons are entitled ("full lessons only from periods
      the subscription was active") without a per-lesson round-trip.

    Resolution itself stays server-side (course.get_lesson_session enforces
    on serving); this endpoint exists so the UI can EXPLAIN locks rather
    than discover them by being refused.
    """
    user = frappe.session.user
    periods = get_periods(user)
    server_today = frappe.utils.getdate(nowdate())
    return {
        "active": skills_entitled(periods, server_today),
        # Plan gate for the in-lesson chat assistant (fail-open — see
        # assistant_chat_allowed): the client disables the chat lane when
        # this is False; agent.api.ask_assistant enforces server-side.
        "assistant_chat": assistant_chat_allowed(user),
        # Holiday Programme scope (fail-open to Full — see
        # holiday_access_for): Full / First Week / None. The client
        # narrows or hides its holiday surface accordingly.
        "holiday_access": holiday_access_for(user),
        "periods": [
            {
                "start": start.isoformat(),
                "end": end.isoformat() if end else None,
            }
            for start, end in periods
        ],
    }


@frappe.whitelist()
def record_subscription_period(student, start_date, end_date=None, source=None):
    """Server-side write of one covered period — called by the payment
    completion flow / admin backfill, NEVER by the student's own session
    (a student who could write periods could grant themselves the whole
    back-catalog, exactly what #27 exists to prevent). System Manager only.

    Idempotent-by-range: an existing row for the same student with the same
    start_date is updated (subscription renewals extend end_date) rather
    than duplicated. Overlaps that do slip through cannot widen access —
    entitlement resolution is a containment scan.
    """
    frappe.only_for("System Manager")

    start = frappe.utils.getdate(start_date)
    end = frappe.utils.getdate(end_date) if end_date else None
    if end and end < start:
        frappe.throw(_("A subscription period cannot end before it starts."))

    existing = frappe.db.get_value(
        "LMS Subscription Period",
        {"student": student, "start_date": start},
        "name",
    )
    if existing:
        frappe.db.set_value(
            "LMS Subscription Period",
            existing,
            {"end_date": end, "source": source},
        )
        return {"name": existing, "updated": True}

    doc = frappe.get_doc(
        {
            "doctype": "LMS Subscription Period",
            "student": student,
            "start_date": start,
            "end_date": end,
            "source": source,
        }
    )
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "updated": False}


def lesson_serving_verdict(
    user,
    scheduled_at,
    now,
    door_close_seconds=None,
    already_joined=False,
    duration_seconds=None,
):
    """The one serving decision course.get_lesson_session applies (#25+#27
    together), over three windows:

    - no broadcast slot (skill/on-demand content) — the active-now rule;
    - BEFORE the live window ends — a live join or a pre-download: the
      active-now rule, and NEVER the next-day recording lock. This
      deliberately covers the whole live session including #35's opening
      five minutes ("nobody is locked out in the first five minutes"): a
      student joining three minutes late is joining normally, not
      requesting a recording. Within this window #25's DOOR gate applies
      to NEW joins: once [door_close_seconds] (the Replay Session field)
      has elapsed since start, a student with no 'Attended' event for the
      session ([already_joined] False) is refused — the door has closed.
      Re-entry by a student who already joined stays open (spec: the door
      locks "for new joiners only"), and an unset/0 field means the door
      never closes (see time_gates.door_closed_for_new_joins);
    - AFTER the live window — a recording request: #25's next-day unlock
      plus #27's period coverage.

    [duration_seconds] is the session's real length
    (Replay Session.duration_seconds, derivable per #40); when unset the
    gates fall back to time_gates' 3-hour LIVE_SESSION_WINDOW upper bound.

    Returns one of: 'allowed', 'needs_active', 'not_covered',
    'recording_locked', 'door_closed'.
    """
    from ..time_gates import (
        door_closed_for_new_joins,
        is_recording_request,
        recording_unlocked,
    )

    periods = get_periods(user)
    server_today = now.date()

    if scheduled_at is None:
        return entitlement_verdict(periods, None, server_today, is_skill=True)

    if is_recording_request(scheduled_at, now, duration_seconds):
        # #25's unlock window first, then #27's period coverage (which
        # deliberately does NOT require being active today — covered
        # content stays rewatchable after a lapse, the retention rule
        # "keep what you earned" broadened to periods).
        if not recording_unlocked(scheduled_at, now):
            return "recording_locked"
        return entitlement_verdict(
            periods, scheduled_at.date(), server_today, is_skill=False
        )

    # Live session (incl. #35's opening block) or a pre-download ahead of
    # it. Time gate first (matching the recording branch's order): past the
    # door-close window a NEW join is refused — a re-entering student
    # (already_joined) passes, and before start the door is simply not
    # closed yet, so pre-downloads are untouched.
    if not already_joined and door_closed_for_new_joins(
        scheduled_at, door_close_seconds, now
    ):
        return "door_closed"

    # Assets legitimately flow, but only for a subscribed student.
    return (
        "allowed"
        if skills_entitled(periods, server_today)
        else "needs_active"
    )


# ---------------------------------------------------------------------------
# Product log #29 — maths track (Mathematics XOR Mathematical Literacy)
# ---------------------------------------------------------------------------

from .. import maths_track as maths_track_rules  # noqa: E402


def held_maths_track(user):
    """The student's maths track: their explicit subscribe-time choice when
    set, else derived from what they are already enrolled in. Returns
    'maths', 'mathematical_literacy', or None.

    Both sources matter: the profile choice is authoritative once made, but
    a student enrolled before the picker existed still holds a track in
    practice, and exclusivity must respect that too.
    """
    row = _profile(user)
    if row and row.maths_track:
        return row.maths_track
    courses = frappe.get_all("LMS Enrollment", {"member": user}, pluck="course")
    if not courses:
        return None
    subjects = frappe.get_all(
        "LMS Course", {"name": ["in", courses], "published": 1}, pluck="subject"
    )
    for subject in subjects:
        track = maths_track_rules.track_of(subject)
        if track:
            return track
    return None


@frappe.whitelist()
def my_maths_track():
    """What track the student holds and whether it is still changeable —
    so the subscribe-time picker can preselect and explain, rather than
    offer a choice the server will refuse."""
    user = frappe.session.user
    row = _profile(user)
    chosen = row.maths_track if row else None
    return {
        "track": held_maths_track(user),
        "chosen": chosen or None,
        "locked": bool(held_maths_track(user)),
    }


@frappe.whitelist()
def set_maths_track(track):
    """Record the subscribe-time track choice (#29).

    Server-enforced exclusivity, not a UI nicety: once a track is held —
    by explicit choice OR by an existing enrolment — the opposite track is
    refused here. Choosing the same track again is idempotent, so a repeat
    subscribe never fails.
    """
    normalised = maths_track_rules.track_of(track)
    if normalised is None:
        frappe.throw(_("Choose Mathematics or Mathematical Literacy."))

    user = frappe.session.user
    # Role exclusivity (decision #23): same student-footprint guard as
    # set_grade — a partner account can't become a student via a track choice.
    enforce_role_exclusivity(user, role_exclusivity.STUDENT)
    held = held_maths_track(user)
    if held and held != normalised:
        frappe.throw(
            _(
                "You are taking {0}. A student takes Mathematics or "
                "Mathematical Literacy, never both."
            ).format(maths_track_rules.track_label(held))
        )

    row = _profile(user)
    if row:
        frappe.db.set_value("LMS Student Profile", row.name, "maths_track", normalised)
    else:
        frappe.get_doc(
            {
                "doctype": "LMS Student Profile",
                "user": user,
                "maths_track": normalised,
            }
        ).insert(ignore_permissions=True)
    return {"track": normalised}


# ---------------------------------------------------------------------------
# Decision #31 — rollover last-year comparison baseline
# ---------------------------------------------------------------------------

from .. import baseline_rules  # noqa: E402


@frappe.whitelist()
def last_year_baseline(year=None):
    """The current student's preserved last-year numbers (decision #31) —
    the comparison baseline the progress card shows a REPEATING student
    ("Last year 5% · Current 40%"). Computed entirely from existing records:
    the LMS Attendance Event ledger record_attendance_event already syncs
    (rate/attended/scheduled, per AttendanceSummary's own definitions) and
    LMS Lesson Quiz Result skips. No new doctype — the rollover gate's
    "last year's records stay intact" promise IS the storage.

    [year] defaults to the previous calendar year (the SA academic year is
    the calendar year — see the module docstring's rollover note). Returns
    null when the student has no attendance ledger for that year: no
    baseline beats a fabricated 0%, and the client keeps its own fallback.
    Repeat-vs-promoted is the CLIENT'S call (it holds the rollover answer);
    this endpoint only serves the numbers.

    Response mirrors lms_sdk's LastYearBaseline.fromJson:
    {year, attendance_rate_percent, rates_by_window: {day/week/month},
    sessions_attended, sessions_scheduled, quizzes_skipped}.
    """
    now = frappe.utils.now_datetime()
    try:
        year = int(year) if year is not None else now.year - 1
    except (TypeError, ValueError):
        frappe.throw(_("Year must be a number."))
    if year >= now.year:
        frappe.throw(_("The baseline year must be a past year."))

    user = frappe.session.user
    year_start = frappe.utils.get_datetime(f"{year}-01-01 00:00:00")
    year_end = frappe.utils.get_datetime(f"{year + 1}-01-01 00:00:00")

    rows = frappe.get_all(
        "LMS Attendance Event",
        {"student": user, "occurred_at": ["between", [year_start, year_end]]},
        ["occurred_at", "outcome"],
    )
    events = [(frappe.utils.get_datetime(r.occurred_at), r.outcome) for r in rows]

    quizzes_skipped = frappe.db.count(
        "LMS Lesson Quiz Result",
        {
            "member": user,
            "outcome": "Skipped",
            "creation": ["between", [year_start, year_end]],
        },
    )

    return baseline_rules.year_baseline(events, quizzes_skipped, year, now)
