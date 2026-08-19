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

"""Knowledge-bites index backend endpoints (decision #52 — the app-side
data plumbing for the opt-in, per-lesson past-paper worked examples).

The factory's rehoused bite content lives at
`lessons/curriculum/CAPS/{subject}/knowledge_bites/{grade}/{lesson-slug}/
{bite-slug}/question.md`; the generated index collapses that tree into one
lookup keyed by lesson-slug so the app can resolve "what bites exist for
this lesson" directly (the #52 storage-shape contract). The server is the
sole authority on that index — the app never hard-codes bite facts.

Same split as skills.py (the pattern this file mirrors line for line):
students read via a whitelisted endpoint; publishing is a server-side,
System-Manager-only write (a student who could rewrite the index could
attach arbitrary "past-paper" content to lessons).
"""

import json

import frappe
from frappe import _

from ..bite_rules import EMPTY_INDEX, count_bites, is_valid_bites_index


@frappe.whitelist()
def knowledge_bites_index():
    """The published knowledge-bites index, in the exact generated-file
    shape the client parses (KnowledgeBiteIndex.parse): `{"bites":
    {lesson_slug: [{bite_slug, subject, grade, title, question_md}, ...]}}`.

    Bites are opt-in extras offered at the end of a lesson (the explicit
    "never auto-shown, never auto-added" decision), so a missing/unpublished
    index answers the empty shape rather than erroring — the client degrades
    to no offer, never to a failure.
    """
    raw = frappe.db.get_single_value("LMS Knowledge Bites Index", "index_json")
    if not raw:
        return EMPTY_INDEX
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        frappe.log_error(frappe.get_traceback(), "Malformed LMS Knowledge Bites Index")
        return EMPTY_INDEX
    if not is_valid_bites_index(parsed):
        return EMPTY_INDEX
    return parsed


@frappe.whitelist()
def publish_knowledge_bites_index(index_json, source=None):
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
    if not is_valid_bites_index(parsed):
        frappe.throw(
            _('index_json must be an object with a "bites" map of per-lesson lists.')
        )

    doc = frappe.get_single("LMS Knowledge Bites Index")
    doc.index_json = index_json
    doc.published_on = frappe.utils.now_datetime()
    doc.source = source
    doc.save(ignore_permissions=True)
    lessons, bites = count_bites(parsed)
    return {
        "lessons": lessons,
        "bites": bites,
        "published_on": str(doc.published_on),
    }
