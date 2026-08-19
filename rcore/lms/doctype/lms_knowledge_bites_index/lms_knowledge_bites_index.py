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

"""The published knowledge-bites index (Single) — the server-side home of
the factory-generated `lessons/knowledge_bites_index.json` (lesson_slug ->
list of {bite_slug, subject, grade, title, question_md} lookups, decision
#52's rehoused past-paper worked examples).

The app fetches this through api.knowledge_bites.knowledge_bites_index,
with the asset-shipped copy as its offline fallback. Written ONLY by
server-side publish flows (api.knowledge_bites.publish_knowledge_bites_index,
System Manager) — students read, never write.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class LMSKnowledgeBitesIndex(Document):
    def validate(self):
        # Same shape gate as rlms.bite_rules.is_valid_bites_index — inlined
        # (not imported) because doctype controllers are installed on their
        # own path in a composed app, matching lms_skills_index.py's
        # self-contained validate.
        if not self.index_json:
            return
        try:
            parsed = json.loads(self.index_json)
        except (TypeError, ValueError):
            frappe.throw(_("Index JSON must be valid JSON."))
        bites = parsed.get("bites") if isinstance(parsed, dict) else None
        well_formed = isinstance(bites, dict) and all(
            isinstance(entries, list) and all(isinstance(e, dict) for e in entries)
            for entries in bites.values()
        )
        if not well_formed:
            frappe.throw(
                _('Index JSON must be an object with a "bites" map of per-lesson lists.')
            )
