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

"""The published skills index (Single) — the server-side home of the
factory-generated `lessons/skills_index.json` (skill_ref -> card/subject/
grade/topic/status lookup, factory/docs/lesson-skills-schema.md).

Retires the "backend endpoint later" note on lms_sdk's SkillLessonSource:
the app fetches this through api.skills.skills_index instead of relying
only on the copy shipped inside downloaded assets. Written ONLY by
server-side publish flows (api.skills.publish_skills_index, System Manager)
— students read, never write.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class LMSSkillsIndex(Document):
    def validate(self):
        if not self.index_json:
            return
        try:
            parsed = json.loads(self.index_json)
        except (TypeError, ValueError):
            frappe.throw(_("Index JSON must be valid JSON."))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("skills"), dict):
            frappe.throw(_('Index JSON must be an object with a "skills" map.'))
