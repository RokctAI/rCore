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

"""Adaptive practice queue backend (product log #42 item 2).

Three endpoints, same split as skills.py:

- `practice_queue` — student read: the member's adaptive queue, selected
  server-side by `practice_rules` over the published item bank plus the
  member's own quiz/practice history. Read-degrades-to-empty: a missing or
  malformed bank answers an empty queue, never an error — practice is an
  optional layer and the client degrades to "nothing to practice yet".
- `record_practice_attempt` — student write of one practice answer/skip.
  Deliberately a SEPARATE doctype (`LMS Practice Attempt`), NOT a row in
  `LMS Lesson Quiz Result`: partner.weekly_report reads that table as
  lesson-quiz ground truth (engagement rate, per-lesson performance
  scores), and rehearsal must never inflate lesson stats. Separate tables
  keep the datasets separable forever with no flag-filtering to forget.
- `publish_practice_bank` — server-side, System-Manager-only publish of the
  pre-authored item bank (factory publish flow / admin backfill), mirroring
  publish_skills_index. Items are the same manifest-authored MCQ stock the
  lesson player shows — pre-authored + adaptive selection = zero live-AI
  cost (#42 item 2's constraint).

The server is the SOLE authority on queue composition: weights, decay,
mastery threshold and length bounds all live in `practice_rules`; the
client renders the returned list in order and reports outcomes back.
"""

import json

import frappe
from frappe import _

from .. import practice_rules

EMPTY_BANK = {"items": {}}

VALID_OUTCOMES = (
    practice_rules.CORRECT,
    practice_rules.INCORRECT,
    practice_rules.SKIPPED,
)

# Most recent history rows considered per source (quiz results / practice
# attempts). Recency decay makes anything older than this weightless anyway.
HISTORY_WINDOW = 500


def _bank_items():
    """The published bank's item map, degrading to empty on missing or
    malformed data (the skills_index posture: a read must never error a
    student surface)."""
    raw = frappe.db.get_single_value("LMS Practice Item Bank", "bank_json")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        frappe.log_error(frappe.get_traceback(), "Malformed LMS Practice Item Bank")
        return {}
    if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), dict):
        return {}
    return {
        item_id: item
        for item_id, item in parsed["items"].items()
        if isinstance(item, dict)
    }


def _grade_matches(item, grade):
    """A bank item without a grade is grade-agnostic and always eligible."""
    item_grade = item.get("grade")
    if grade is None or item_grade in (None, ""):
        return True
    try:
        return int(item_grade) == int(grade)
    except (TypeError, ValueError):
        return False


def _recent_rows(doctype, member, fields):
    """The member's most recent [HISTORY_WINDOW] rows, returned
    oldest→newest (the order practice_rules expects)."""
    rows = frappe.get_all(
        doctype,
        {"member": member},
        fields,
        order_by="creation desc",
        limit_page_length=HISTORY_WINDOW,
    )
    rows.reverse()
    return rows


@frappe.whitelist()
def practice_queue(subject=None, grade=None, lesson=None, limit=None):
    """The member's adaptive practice queue, in play order.

    [subject]/[lesson] narrow scope when the client asks (a per-subject
    practice entry); [grade] defaults to the student's stored profile grade
    so a student only ever practices their own grade's material. [limit] is
    clamped server-side (practice_rules.MAX_QUEUE_LENGTH cap) — the client
    cannot widen composition.

    Selection is deterministic per (member, day): the same student re-opening
    practice sees the same queue until either the day rolls over or new
    attempts change the inputs.
    """
    member = frappe.session.user

    if grade is None:
        grade = frappe.db.get_value("LMS Student Profile", {"user": member}, "grade")
    try:
        grade = int(grade) if grade not in (None, "") else None
    except (TypeError, ValueError):
        grade = None

    eligible = {}
    for item_id, item in _bank_items().items():
        if subject and item.get("subject") != subject:
            continue
        if lesson and item.get("lesson") != lesson:
            continue
        if not _grade_matches(item, grade):
            continue
        eligible[item_id] = item

    quiz_rows = _recent_rows(
        "LMS Lesson Quiz Result", member, ["subtopic_ref", "outcome", "creation"]
    )
    practice_rows = _recent_rows(
        "LMS Practice Attempt",
        member,
        ["item_id", "subtopic_ref", "outcome", "creation"],
    )
    merged = sorted(quiz_rows + practice_rows, key=lambda r: r.creation)

    seed = f"{member}:{frappe.utils.nowdate()}"
    queue_ids = practice_rules.build_queue(
        eligible, merged, practice_rows, limit=limit, seed=seed
    )

    items = []
    for item_id in queue_ids:
        payload = dict(eligible[item_id])
        payload["id"] = item_id
        items.append(payload)
    return {
        "items": items,
        "generated_at": frappe.utils.now_datetime().isoformat(),
        "bank_size": len(eligible),
    }


@frappe.whitelist()
def record_practice_attempt(item_id, outcome, subtopic_ref=None, selected_index=None):
    """Logs one practice answer/skip for the adaptive loop. See the module
    doc for why this is NOT an `LMS Lesson Quiz Result` row: lesson stats
    (partner weekly report) must never be polluted by rehearsal."""
    item_id = (item_id or "").strip()
    if not item_id:
        frappe.throw(_("item_id is required."))
    if outcome not in VALID_OUTCOMES:
        frappe.throw(_("outcome must be one of: {0}").format(", ".join(VALID_OUTCOMES)))
    if selected_index not in (None, ""):
        try:
            selected_index = int(selected_index)
        except (TypeError, ValueError):
            frappe.throw(_("selected_index must be an integer."))
    else:
        selected_index = None

    doc = frappe.get_doc(
        {
            "doctype": "LMS Practice Attempt",
            "member": frappe.session.user,
            "item_id": item_id,
            "subtopic_ref": subtopic_ref,
            "outcome": outcome,
            "selected_index": selected_index,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


@frappe.whitelist()
def publish_practice_bank(bank_json, source=None):
    """Server-side publish of the pre-authored item bank — factory publish
    flow / admin backfill, NEVER a student session. System Manager only.
    Replaces the whole document (the bank is generated atomically per
    factory run; there is no partial update)."""
    frappe.only_for("System Manager")

    if isinstance(bank_json, (dict, list)):
        bank_json = json.dumps(bank_json)
    try:
        parsed = json.loads(bank_json)
    except (TypeError, ValueError):
        frappe.throw(_("bank_json must be valid JSON."))
    if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), dict):
        frappe.throw(_('bank_json must be an object with an "items" map.'))

    doc = frappe.get_single("LMS Practice Item Bank")
    doc.bank_json = bank_json
    doc.published_on = frappe.utils.now_datetime()
    doc.source = source
    doc.save(ignore_permissions=True)
    return {"items": len(parsed["items"]), "published_on": str(doc.published_on)}
