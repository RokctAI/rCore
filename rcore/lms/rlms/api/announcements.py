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

"""One-way operator→student announcements riding the Glance surface
(owner's call: "we have glance, we can use it for announcements too" —
schedule changes, holiday programme news; NO comments, NO stream).

Same split as skills.py / knowledge_bites.py:

- `active_announcements` — student read: the posts this student sees right
  now, filtered server-side to their stored grade/curriculum and the active
  window (`announcement_rules.visible`). Read-degrades-to-empty: any
  failure answers an empty list, never an error — announcements only ever
  ADD a glance line.
- `create_announcement` / `retire_announcement` / `list_announcements` —
  the operator side, System Manager only (the admin.py precedent: a write
  every student's glance card renders is exactly the class of write
  students must never reach). `can_manage_announcements` merely answers
  whether the operator entry point should show, so it never throws.
"""

import frappe
from frappe import _

from .. import announcement_rules

DOCTYPE = "LMS Announcement"

_FIELDS = [
    "name",
    "title",
    "body",
    "subject",
    "grade",
    "curriculum",
    "starts_at",
    "ends_at",
    "retired",
    "posted_by",
    "creation",
]


def _payload(row):
    """One announcement in the wire shape both clients parse."""
    grade = row.get("grade")
    return {
        "id": row.get("name"),
        "title": row.get("title"),
        "body": row.get("body"),
        "subject": row.get("subject") or None,
        "grade": int(grade) if grade not in (None, "", 0) else None,
        "curriculum": row.get("curriculum") or None,
        "starts_at": str(row.get("starts_at")) if row.get("starts_at") else None,
        "ends_at": str(row.get("ends_at")) if row.get("ends_at") else None,
        "retired": bool(row.get("retired")),
        "posted_by": row.get("posted_by") or None,
        "posted_at": str(row.get("creation")) if row.get("creation") else None,
    }


@frappe.whitelist()
def active_announcements():
    """The signed-in student's current announcements, newest-posted first.

    Filtering is entirely server-side (`announcement_rules`): the stored
    profile grade/curriculum narrow targeted posts, the window gates both
    sides. Degrades to an empty list on any failure — a backend hiccup must
    read as "nothing to announce", never an error on the schedule.
    """
    try:
        profile = frappe.db.get_value(
            "LMS Student Profile",
            {"user": frappe.session.user},
            ["grade", "curriculum"],
            as_dict=True,
        )
        rows = frappe.get_all(
            DOCTYPE,
            filters={"retired": 0},
            fields=_FIELDS,
            order_by="creation desc",
        )
        shown = announcement_rules.visible(
            rows,
            profile.grade if profile else None,
            profile.curriculum if profile else None,
            frappe.utils.now_datetime(),
        )
        return {"announcements": [_payload(row) for row in shown]}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "active_announcements failed")
        return {"announcements": []}


@frappe.whitelist()
def can_manage_announcements():
    """Whether the session user may use the announcements operator page.
    Drives the entry point's visibility client-side (called once and
    cached). Deliberately never throws — a failure here must read as "hide
    the entry", not surface an error to a student."""
    try:
        return {"allowed": "System Manager" in frappe.get_roles(frappe.session.user)}
    except Exception:
        return {"allowed": False}


@frappe.whitelist()
def create_announcement(
    title, body, grade=None, subject=None, curriculum=None, starts_at=None, ends_at=None
):
    """Posts one announcement. System Manager only — this lands on every
    targeted student's glance card. Audience filters and window are all
    optional: nothing set means everyone, immediately, until retired."""
    frappe.only_for("System Manager")

    problem = announcement_rules.validate_post(
        title, body, grade=grade, curriculum=curriculum, starts_at=starts_at, ends_at=ends_at
    )
    if problem:
        frappe.throw(_(problem))

    doc = frappe.get_doc(
        {
            "doctype": DOCTYPE,
            "title": title.strip(),
            "body": body.strip(),
            "subject": (subject or "").strip() or None,
            "grade": int(grade) if grade not in (None, "") else None,
            "curriculum": curriculum or None,
            "starts_at": starts_at or None,
            "ends_at": ends_at or None,
            "retired": 0,
            "posted_by": frappe.session.user,
        }
    )
    doc.insert(ignore_permissions=True)
    row = frappe.db.get_value(DOCTYPE, doc.name, _FIELDS, as_dict=True)
    return _payload(row)


@frappe.whitelist()
def retire_announcement(announcement_id):
    """Takes one announcement off every glance card immediately (the only
    way a post ends other than its own window). System Manager only.
    Retiring an already-retired post is idempotent."""
    frappe.only_for("System Manager")

    row = frappe.db.get_value(DOCTYPE, announcement_id, ["name", "retired"], as_dict=True)
    if not row:
        frappe.throw(_("Announcement not found."), frappe.DoesNotExistError)
    if not row.retired:
        frappe.db.set_value(
            DOCTYPE,
            row.name,
            {"retired": 1, "retired_at": frappe.utils.now_datetime()},
        )
    return {"id": row.name, "retired": True}


@frappe.whitelist()
def list_announcements():
    """Operator read: every announcement, newest first, retired included —
    the operator page's list (what's live, what's scheduled, what ended).
    System Manager only; students read via `active_announcements`."""
    frappe.only_for("System Manager")
    rows = frappe.get_all(
        DOCTYPE,
        fields=_FIELDS,
        order_by="creation desc",
    )
    return {"announcements": [_payload(row) for row in rows]}
