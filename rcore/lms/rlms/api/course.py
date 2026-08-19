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

import frappe
from frappe import _
from frappe.utils import now_datetime

from .. import maths_track, role_exclusivity
from . import student as student_api
from .partner import enforce_role_exclusivity


def _lesson_paid(student, lesson):
    """Whether [student] holds a per-lesson purchase of [lesson] — the
    once-off pay-per-lesson charge rlms.api.billing writes with the lesson
    linked. The billing row doubles as the access grant: one lesson, this
    lesson, nothing wider (no subscription period is written for it)."""
    return bool(
        frappe.db.exists(
            "LMS Billing Record", {"student": student, "lesson": lesson}
        )
    )


def _throw_for_verdict(verdict):
    """The #25/#27 refusal throws, one per verdict, in the student-facing
    words every serving surface must share (get_lesson_session and replay's
    asset endpoints via enforce_session_serving). A no-op for 'allowed'."""
    if verdict == "door_closed":
        frappe.throw(
            _(
                "The door for this session has closed. "
                "The recording lands in your Library tomorrow."
            ),
            frappe.PermissionError,
        )
    elif verdict == "recording_locked":
        frappe.throw(
            _("This recording unlocks the day after its broadcast."),
            frappe.PermissionError,
        )
    elif verdict == "needs_active":
        frappe.throw(
            _("An active subscription is needed to play this lesson."),
            frappe.PermissionError,
        )
    elif verdict == "not_covered":
        frappe.throw(
            _(
                "This lesson aired outside your subscription periods. "
                "Your plan covers lessons from the periods you were subscribed."
            ),
            frappe.PermissionError,
        )


def _session_serving_verdict(user, session_id, lesson=None, is_free_sample=False):
    """The one serving decision for [session_id], exactly as
    get_lesson_session applies it: free samples bypass everything (samples
    ARE the funnel); otherwise student_api.lesson_serving_verdict over the
    session's Replay Session schedule, with the per-lesson-purchase
    override when [lesson] is known.

    #25 door policy: the door locks for NEW joiners only — a student who
    already holds an 'Attended' event for this session (synced at join time
    by the on-device ledger) is re-entering, not joining late, and must not
    be locked out of their own live lesson.

    Pay-per-lesson (LMS Plan kind "Per Lesson"): a once-off purchase of
    THIS lesson — recorded by rlms.api.billing as an LMS Billing Record
    linked to the lesson — substitutes for subscription coverage of this
    one lesson only. The time gates above it stand: a paid lesson's
    recording still unlocks the day after broadcast, and the door still
    closes for late new joins.
    """
    if is_free_sample:
        return "allowed"
    session_row = frappe.db.get_value(
        "Replay Session",
        {"session_id": session_id},
        ["scheduled_at", "door_close_seconds", "duration_seconds"],
        as_dict=True,
    )
    scheduled_at = (
        frappe.utils.get_datetime(session_row.scheduled_at)
        if session_row and session_row.scheduled_at
        else None
    )
    already_joined = bool(
        frappe.db.exists(
            "LMS Attendance Event",
            {
                "student": user,
                "session_id": session_id,
                "outcome": "Attended",
            },
        )
    )
    verdict = student_api.lesson_serving_verdict(
        user,
        scheduled_at,
        now_datetime(),
        door_close_seconds=session_row.door_close_seconds if session_row else None,
        already_joined=already_joined,
        duration_seconds=session_row.duration_seconds if session_row else None,
    )
    if verdict in ("needs_active", "not_covered") and lesson and _lesson_paid(
        user, lesson
    ):
        verdict = "allowed"
    return verdict


def session_serving_verdict(session_id, user=None):
    """Cross-app serving check for replay's asset endpoints (#25):
    the same verdict get_lesson_session throws on, keyed by session_id —
    the replay package has no entitlement concept of its own, so it asks
    rlms (via frappe.get_attr, the composed-app pattern) before handing out
    asset URLs. Deliberately NOT whitelisted: server-side callers only.

    Resolves the Course Lesson carrying [session_id] (when one exists) so
    the free-sample bypass and the per-lesson-purchase override hold here
    exactly as they do at get_lesson_session; a session no lesson points at
    gets the plain subscription + time gates.
    """
    user = user or frappe.session.user
    lesson = frappe.db.get_value(
        "Course Lesson",
        {"session_id": session_id},
        ["name", "is_free_sample"],
        as_dict=True,
    )
    return _session_serving_verdict(
        user,
        session_id,
        lesson=lesson.name if lesson else None,
        is_free_sample=bool(lesson and lesson.is_free_sample),
    )


def enforce_session_serving(session_id, user=None):
    """session_serving_verdict plus the same PermissionError throws
    get_lesson_session uses — one refusal style on every serving surface.
    Returns the verdict ('allowed') when serving may proceed. NOT
    whitelisted: server-side callers only."""
    verdict = session_serving_verdict(session_id, user=user)
    _throw_for_verdict(verdict)
    return verdict


def _get_next_lesson(course, lesson):
    lessons = frappe.get_all(
        "Course Lesson",
        {"course": course},
        ["name", "chapter", "sequence"],
        order_by="chapter, sequence, name",
    )
    for idx, entry in enumerate(lessons):
        if entry.name == lesson and idx + 1 < len(lessons):
            return lessons[idx + 1].name
    return None


@frappe.whitelist()
def list_courses(subject=None, grade=None):
    """Published courses for a catalog/browse screen, optionally filtered to one
    subject slug and/or the student's grade. Card-level fields only —
    get_course_content fetches a specific course's chapters/lessons once the
    student opens it.

    Grade filtering (student-grade brief): a course whose grade is 0/empty is
    grade-agnostic and always shown — filtering must never hide the seeded
    pre-grade-field catalog. Python-side filter, explicit over an or_filters
    dance, fine at catalog scale."""
    filters = {"published": 1}
    if subject:
        filters["subject"] = subject
    courses = frappe.get_all(
        "LMS Course",
        filters,
        ["name", "title", "subject", "grade", "short_introduction", "image", "lesson_count"],
        order_by="title",
    )
    if grade:
        grade = int(grade)
        courses = [c for c in courses if not c.grade or int(c.grade) == grade]
    return courses


@frappe.whitelist()
def get_course_content(course):
    """Nested chapter/lesson structure for the course catalog and lesson-navigation UI.

    #25 keep-the-listing/withhold-the-keys (the pattern replay's
    get_upcoming_sessions applies): the chapter/lesson listing stays visible
    to every signed-in student — it powers pre-enrolment catalog browsing
    (the catalog's inline chapter/lesson preview expands any published
    course before enroll) — but each lesson's session_id, the key every
    replay asset lookup rides on, comes back null unless the caller's
    serving verdict for that session is 'allowed' (the same
    _session_serving_verdict get_lesson_session throws on, free-sample
    bypass and per-lesson purchases included). Navigation is unaffected:
    clients open lessons by lesson name via get_lesson_session, which
    re-applies this gate and explains any refusal. Any failure to obtain a
    verdict fails CLOSED — the key is withheld, never an error, so the
    catalog keeps its listing."""
    chapters = frappe.get_all(
        "Course Chapter",
        {"course": course},
        ["name", "title", "sequence"],
        order_by="sequence, name",
    )
    user = frappe.session.user
    for chapter in chapters:
        lessons = frappe.get_all(
            "Course Lesson",
            {"chapter": chapter.name},
            ["name", "title", "sequence", "session_id", "is_free_sample"],
            order_by="sequence, name",
        )
        for lesson in lessons:
            allowed = False
            if lesson.get("session_id"):
                try:
                    allowed = (
                        _session_serving_verdict(
                            user,
                            lesson["session_id"],
                            lesson=lesson["name"],
                            is_free_sample=bool(lesson.get("is_free_sample")),
                        )
                        == "allowed"
                    )
                except Exception:
                    allowed = False
            if not allowed:
                lesson["session_id"] = None
            # Verdict input only — keep the response shape consumers pinned.
            lesson.pop("is_free_sample", None)
        chapter["lessons"] = lessons
    return chapters


@frappe.whitelist()
def get_lesson_session(lesson):
    """Resolve a lesson to the session_id LessonPlaybackEngine.prepare() expects, plus
    the next lesson in course order (for auto-advance when playback completes).

    #25/#27 serving gate: this resolution IS the app's content-access step
    (the session id keys every asset lookup), so entitlement is enforced
    HERE, server-side, against server time — not only in the client UI:

    - free-sample lessons bypass everything (samples ARE the funnel);
    - a past broadcast is a recording: refuse before its unlock time
      (midnight after broadcast — #25), and refuse when no subscription
      period covered its air date (#27's no-retroactive-harvest rule);
    - a future broadcast is a live pre-download: requires an active
      subscription;
    - a live join past the session's door-close window (#25 door policy,
      Replay Session.door_close_seconds) is refused for NEW joiners; a
      student already marked Attended is re-entering and passes, and an
      unset/0 window means the door never closes;
    - a lesson with no Replay Session schedule (on-demand/skill content):
      requires an active subscription — #27's skills rule.

    Deny is a throw with a distinct message per verdict so the client can
    explain the lock rather than show a generic failure.
    """
    details = frappe.db.get_value(
        "Course Lesson",
        lesson,
        ["session_id", "course", "is_free_sample"],
        as_dict=True,
    )
    if not details:
        frappe.throw(_("Lesson not found."))

    if not details.is_free_sample:
        # The shared #25/#27 core (door policy, recording unlock, period
        # coverage, per-lesson-purchase override) — the same verdict + throw
        # replay's asset endpoints apply via enforce_session_serving.
        verdict = _session_serving_verdict(
            frappe.session.user, details.session_id, lesson=lesson
        )
        _throw_for_verdict(verdict)

    return {
        "session_id": details.session_id,
        "next_lesson": _get_next_lesson(details.course, lesson),
    }


@frappe.whitelist()
def allowed_subjects(user=None):
    """Backs SubjectEntitlements.allowedSubjects — subject slugs the user is enrolled
    in a published course for. Empty list, not an error, when there's nothing active."""
    user = user or frappe.session.user
    courses = frappe.get_all("LMS Enrollment", {"member": user}, pluck="course")
    if not courses:
        return []
    subjects = frappe.get_all(
        "LMS Course",
        {"name": ["in", courses], "published": 1},
        pluck="subject",
        distinct=True,
    )
    return [s for s in subjects if s]


@frappe.whitelist()
def enroll(course):
    """Enrol the current user in a published course.

    #29 maths-track exclusivity, enforced HERE (where the enrolment is
    recorded) rather than only in the subject picker: a student takes
    Mathematics OR Mathematical Literacy, never both — the real CAPS rule.
    Re-enrolling in the track already held is fine; only the opposite track
    is refused, and non-maths subjects never conflict.
    """
    member = frappe.session.user
    existing = frappe.db.exists("LMS Enrollment", {"course": course, "member": member})
    if existing:
        return existing

    # Role exclusivity (decision #23): an enrolment is a student footprint,
    # so an accountability-partner account may not acquire one — enforced
    # here, where the enrolment is recorded, same posture as the maths-track
    # rule below. (After the idempotent early-return: re-reading an existing
    # enrolment mints no new persona.)
    enforce_role_exclusivity(member, role_exclusivity.STUDENT)

    new_subject = frappe.db.get_value("LMS Course", course, "subject")
    conflict = maths_track.conflicting_track(_enrolled_subjects(member), new_subject)
    if conflict:
        frappe.throw(
            _(
                "You are taking {0}. A student takes Mathematics or "
                "Mathematical Literacy, never both."
            ).format(maths_track.track_label(conflict))
        )

    doc = frappe.get_doc(
        {"doctype": "LMS Enrollment", "course": course, "member": member}
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _enrolled_subjects(member):
    """Subject slugs the member is already enrolled in (published courses
    only — an unpublished/retired course must not block a live choice)."""
    courses = frappe.get_all("LMS Enrollment", {"member": member}, pluck="course")
    if not courses:
        return []
    return frappe.get_all(
        "LMS Course",
        {"name": ["in", courses], "published": 1},
        pluck="subject",
    )


@frappe.whitelist()
def get_my_enrollment(course):
    return frappe.db.get_value(
        "LMS Enrollment",
        {"course": course, "member": frappe.session.user},
        ["name", "progress", "current_lesson"],
        as_dict=True,
    )
