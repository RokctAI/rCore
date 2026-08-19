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

from rcore.api.idempotency import idempotent


@frappe.whitelist()
def save_progress(lesson, is_complete=1):
    """Record (or update) this student's completion of a lesson and refresh their
    enrollment progress percentage."""
    member = frappe.session.user
    course = frappe.db.get_value("Course Lesson", lesson, "course")
    existing = frappe.db.exists("LMS Course Progress", {"lesson": lesson, "member": member})

    if existing:
        frappe.db.set_value("LMS Course Progress", existing, "is_complete", int(is_complete))
        doc = frappe.get_doc("LMS Course Progress", existing)
        doc.run_method("on_update")
    else:
        doc = frappe.get_doc(
            {
                "doctype": "LMS Course Progress",
                "lesson": lesson,
                "course": course,
                "member": member,
                "is_complete": int(is_complete),
            }
        )
        doc.insert(ignore_permissions=True)

    if frappe.db.exists("LMS Enrollment", {"course": course, "member": member}):
        frappe.db.set_value(
            "LMS Enrollment", {"course": course, "member": member}, "current_lesson", lesson
        )

    return frappe.db.get_value(
        "LMS Enrollment", {"course": course, "member": member}, "progress"
    )


@frappe.whitelist()
@idempotent
def record_video_watch(lesson, source, watch_time):
    """Accumulate watch time for (member, lesson, source) — one row per source per lesson.
    Requests carrying X-Idempotency-Key are deduped: a retried upload replays the stored
    response (30-day window) instead of accumulating twice."""
    member = frappe.session.user
    existing = frappe.db.exists(
        "LMS Video Watch Duration", {"member": member, "lesson": lesson, "source": source}
    )
    if existing:
        current = frappe.db.get_value("LMS Video Watch Duration", existing, "watch_time") or 0
        frappe.db.set_value(
            "LMS Video Watch Duration", existing, "watch_time", current + float(watch_time)
        )
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "LMS Video Watch Duration",
            "lesson": lesson,
            "member": member,
            "source": source,
            "watch_time": float(watch_time),
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
@idempotent
def record_quiz_result(lesson, question_id, outcome, subtopic_ref=None, selected_index=None):
    """Backs McqResult — logs one MCQ answer/skip. Questions themselves are manifest-authored,
    not stored here; this only records the outcome for engagement tracking.
    Requests carrying X-Idempotency-Key are deduped: a retried upload replays the stored
    response (30-day window) instead of inserting a duplicate row."""
    doc = frappe.get_doc(
        {
            "doctype": "LMS Lesson Quiz Result",
            "lesson": lesson,
            "member": frappe.session.user,
            "question_id": question_id,
            "subtopic_ref": subtopic_ref,
            "outcome": outcome,
            "selected_index": selected_index,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name
