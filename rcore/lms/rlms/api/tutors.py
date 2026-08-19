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

"""Tutor-catalog backend endpoints (the TutorCatalog docstring's "backend
endpoint later", now built — same shape as api/skills.py for the skills
index).

The team rosters (`lms/team/{tutors,assistants}/CAPS/roster.json`, persona
cards, `team/founders/`) are the canonical tutor data; the app has so far
shown only a hand-copied seeded deck. `tutors` serves the published
roster-derived catalog straight from the backend so real builds show the
CURRENT team, keeping the seeded deck as the client-side fallback.

Same split as skills_index: anyone reads (tutor browsing is explicitly
free/guest-mode — the TutorCatalog contract says implementations must not
require auth); publishing is a server-side, System-Manager-only write.

Ratings: rlms has no rating doctype, so no real rating data exists. The
published catalog omits `rating`/`enrolled_count` (or sends null) and this
endpoint passes that absence through verbatim — it NEVER fabricates a
value. tutor_rules.validate_catalog enforces this at publish time.
"""

import json

import frappe
from frappe import _

from .. import tutor_rules

EMPTY_CATALOG = {"tutors": []}


@frappe.whitelist(allow_guest=True)
def tutors(grade=None):
    """The published tutor catalog, entries in the exact key shape the
    client already parses (TutorProfile.fromJson): `display_name`,
    `style_tag`, `grades`, `role`, `sample_lesson_id`, ...

    Discovery-only data, so a missing/unpublished/malformed catalog answers
    the empty shape rather than erroring — the client degrades to its
    seeded fallback deck, never to a failure (same posture as skills_index).

    `grade` (optional, e.g. 10-12) narrows to tutors teaching that grade,
    with the same semantics as the client's own filter.
    """
    grade = frappe.utils.cint(grade) or None
    raw = frappe.db.get_single_value("LMS Tutor Catalog", "catalog_json")
    if not raw:
        return EMPTY_CATALOG
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        frappe.log_error(frappe.get_traceback(), "Malformed LMS Tutor Catalog")
        return EMPTY_CATALOG
    if not isinstance(parsed, dict) or not isinstance(parsed.get("tutors"), list):
        return EMPTY_CATALOG
    entries = [e for e in parsed["tutors"] if isinstance(e, dict)]
    return {"tutors": tutor_rules.filter_by_grade(entries, grade)}


@frappe.whitelist()
def publish_tutors(catalog_json, source=None):
    """Server-side publish of the roster-derived catalog — called by the
    factory's publish flow / admin backfill, NEVER by a student session.
    System Manager only. Replaces the whole document (the catalog is
    generated atomically from the rosters; there is no partial update)."""
    frappe.only_for("System Manager")

    if isinstance(catalog_json, (dict, list)):
        catalog_json = json.dumps(catalog_json)
    try:
        parsed = json.loads(catalog_json)
    except (TypeError, ValueError):
        frappe.throw(_("catalog_json must be valid JSON."))
    try:
        tutor_rules.validate_catalog(parsed)
    except tutor_rules.CatalogError as exc:
        frappe.throw(_(str(exc)))

    doc = frappe.get_single("LMS Tutor Catalog")
    doc.catalog_json = catalog_json
    doc.published_on = frappe.utils.now_datetime()
    doc.source = source
    doc.save(ignore_permissions=True)
    return {"tutors": len(parsed["tutors"]), "published_on": str(doc.published_on)}
