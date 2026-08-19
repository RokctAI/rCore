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
from frappe.model.document import Document


class LMSCourseProgress(Document):
    def before_insert(self):
        if frappe.db.exists("LMS Course Progress", {"member": self.member, "lesson": self.lesson}):
            frappe.throw(
                _("Progress is already recorded for this lesson."),
                frappe.UniqueValidationError,
            )

    def on_update(self):
        recalculate_course_progress(self.course, self.member)

    def after_delete(self):
        recalculate_course_progress(self.course, self.member)


def recalculate_course_progress(course, member):
    total = frappe.db.count("Course Lesson", {"course": course})
    if not total:
        return
    completed = frappe.db.count(
        "LMS Course Progress", {"course": course, "member": member, "is_complete": 1}
    )
    progress = min(100, round((completed / total) * 100, 2))
    frappe.db.set_value(
        "LMS Enrollment", {"course": course, "member": member}, "progress", progress
    )
