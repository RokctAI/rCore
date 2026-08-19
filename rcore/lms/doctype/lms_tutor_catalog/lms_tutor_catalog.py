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

"""The published tutor catalog (Single) — the server-side home of the
roster-derived tutor deck (`lms/team/{tutors,assistants}/CAPS/roster.json`
+ persona cards + `team/founders/`, the canonical sources the app's seeded
deck was hand-copied from).

Retires the "backend endpoint later" note on lms_sdk's TutorCatalog: real
builds fetch this through api.tutors.tutors instead of relying only on the
seeded in-app deck. Written ONLY by server-side publish flows
(api.tutors.publish_tutors, System Manager) — students read, never write.

The validation here deliberately re-implements tutor_rules.validate_catalog
rather than importing it (the doctype and api trees don't import each other
— same stance as LMS Student Profile's CURRICULA). The rule that matters:
`rating`/`enrolled_count` are OPTIONAL — no rating surface exists in rlms,
so a catalog with the keys absent is the normal, honest state."""

import json

import frappe
from frappe import _
from frappe.model.document import Document


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class LMSTutorCatalog(Document):
    def validate(self):
        if not self.catalog_json:
            return
        try:
            parsed = json.loads(self.catalog_json)
        except (TypeError, ValueError):
            frappe.throw(_("Catalog JSON must be valid JSON."))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("tutors"), list):
            frappe.throw(_('Catalog JSON must be an object with a "tutors" list.'))
        for i, entry in enumerate(parsed["tutors"]):
            if not isinstance(entry, dict):
                frappe.throw(_("tutors[{0}] must be an object.").format(i))
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id.strip():
                frappe.throw(
                    _("tutors[{0}] must have a non-empty string id.").format(i)
                )
            name = entry.get("display_name") or entry.get("name")
            if not isinstance(name, str) or not name.strip():
                frappe.throw(
                    _("tutors[{0}] must have a non-empty display_name (or name).").format(i)
                )
            rating = entry.get("rating")
            if rating is not None and (not _is_number(rating) or not 0 <= rating <= 5):
                frappe.throw(
                    _("tutors[{0}].rating must be a number in 0..5 when present.").format(i)
                )
            enrolled = entry.get("enrolled_count")
            if enrolled is not None and (
                not isinstance(enrolled, int)
                or isinstance(enrolled, bool)
                or enrolled < 0
            ):
                frappe.throw(
                    _(
                        "tutors[{0}].enrolled_count must be a non-negative integer when present."
                    ).format(i)
                )
