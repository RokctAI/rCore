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

"""Skills-index backend endpoints (the SkillLessonSource docstring's
"backend endpoint later", now built).

The factory generates `lessons/skills_index.json` — the skill_ref lookup
behind the app's NON-FORCING skill suggestions (pre-session assessment,
attendance hand-out) and the Library's skills shelf. Until now that file
only reached devices inside downloaded assets; skills_index serves the
same generated document straight from the backend so a device gets the
CURRENT index without waiting for an asset download, keeping the shipped
file as its offline fallback.

Same split as record_subscription_period: students read via a whitelisted
endpoint; publishing is a server-side, System-Manager-only write (a
student who could rewrite the index could point skill suggestions at
arbitrary content).
"""

import json

import frappe
from frappe import _

EMPTY_INDEX = {"skills": {}}


@frappe.whitelist()
def skills_index():
    """The published skills index, in the exact generated-file shape the
    client already parses (SkillLessonIndex.parse): `{"skills": {skill_ref:
    {card_id, subject, grade, topic, subtopic, lesson_name, status, ...}}}`.

    Suggestions-only data (the explicit "not forcing them" decision), so a
    missing/unpublished index answers the empty shape rather than erroring —
    the client degrades to no suggestions, never to a failure.
    """
    raw = frappe.db.get_single_value("LMS Skills Index", "index_json")
    if not raw:
        return EMPTY_INDEX
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        frappe.log_error(frappe.get_traceback(), "Malformed LMS Skills Index")
        return EMPTY_INDEX
    if not isinstance(parsed, dict) or not isinstance(parsed.get("skills"), dict):
        return EMPTY_INDEX
    return parsed


@frappe.whitelist()
def publish_skills_index(index_json, source=None):
    """Server-side publish of the generated index — called by the factory's
    publish flow / admin backfill, NEVER by a student session. System
    Manager only. Replaces the whole document (the index is generated
    atomically per factory run; there is no partial update)."""
    frappe.only_for("System Manager")

    if isinstance(index_json, (dict, list)):
        index_json = json.dumps(index_json)
    try:
        parsed = json.loads(index_json)
    except (TypeError, ValueError):
        frappe.throw(_("index_json must be valid JSON."))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("skills"), dict):
        frappe.throw(_('index_json must be an object with a "skills" map.'))

    doc = frappe.get_single("LMS Skills Index")
    doc.index_json = index_json
    doc.published_on = frappe.utils.now_datetime()
    doc.source = source
    doc.save(ignore_permissions=True)
    return {"skills": len(parsed["skills"]), "published_on": str(doc.published_on)}
