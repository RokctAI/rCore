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

"""Admin-only lesson review backend (Supacharge in-app review flow).

The factory repo (RokctAI/factory) publishes a lesson review index
(`lessons/review_index.json`); the app's admin review screen plays each
generated CAPS lesson through the whiteboard player and the reviewer
approves or denies it. The decision must land back in the factory repo as
a state file (`lessons/reviews/<lesson_id>.json`) so regeneration can key
off it — written here via the GitHub Contents API, following the
`agent/frappe`'s roadmap `setup_github_workflow` precedent (PAT from
`site_config.json`'s `github_personal_access_token`).

Both endpoints are System Manager territory: `review_lesson` hard-gates
with `frappe.only_for` (the `record_subscription_period` precedent);
`can_review_lessons` merely answers whether the entry point should show,
so it never throws.
"""

import base64
import json
import re
from datetime import datetime, timezone

import frappe
import requests
from frappe import _

# The factory repo that owns lesson content and review state.
FACTORY_REPO = "RokctAI/factory"
FACTORY_BRANCH = "main"
REVIEWS_DIR = "lessons/reviews"

VALID_STATUSES = ("approved", "denied")

# Filename-safe lesson ids only — factory card ids are slug-like
# (`maths_g11_quadratic_equations_factoring_method_31d165`). No path
# separators, no dots-only names, nothing that could escape REVIEWS_DIR.
LESSON_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@frappe.whitelist()
def can_review_lessons():
    """Whether the session user may use the lesson review screen.

    Drives the entry point's visibility client-side (called once and
    cached). Deliberately never throws — a failure here must read as
    "hide the entry", not surface an error to a student.
    """
    try:
        return {"allowed": "System Manager" in frappe.get_roles(frappe.session.user)}
    except Exception:
        return {"allowed": False}


@frappe.whitelist()
def review_lesson(lesson_id, status, reason=None):
    """Records one review decision as a state file in the factory repo.

    Writes `lessons/reviews/<lesson_id>.json` on the factory repo's main
    branch (create, or update via the existing blob sha) with the agreed
    contract shape, and returns the written state:

        {"lesson_id", "status", "reason", "reviewed_by", "reviewed_at"}

    System Manager only — a review decision gates regeneration and
    publication, exactly the class of write students must never reach.
    """
    frappe.only_for("System Manager")

    lesson_id = (lesson_id or "").strip()
    if not LESSON_ID_RE.match(lesson_id) or ".." in lesson_id:
        frappe.throw(_("Invalid lesson id."))
    if status not in VALID_STATUSES:
        frappe.throw(_("status must be one of: {0}").format(", ".join(VALID_STATUSES)))
    reason = (reason or "").strip() or None

    state = {
        "lesson_id": lesson_id,
        "status": status,
        "reason": reason,
        "reviewed_by": frappe.session.user,
        "reviewed_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }

    _put_factory_file(
        path=f"{REVIEWS_DIR}/{lesson_id}.json",
        content=json.dumps(state, indent=2) + "\n",
        message=f"review: {status} {lesson_id}",
    )
    return state


def _github_headers():
    token = frappe.conf.get("github_personal_access_token")
    if not token:
        frappe.throw(
            _("GitHub Personal Access Token is not configured in site_config.json.")
        )
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _put_factory_file(path, content, message):
    """Create-or-update one file in the factory repo via the Contents API
    (the roadmap `setup_github_workflow` pattern): fetch the existing blob's
    sha first — present means update, 404 means create."""
    api_url = f"https://api.github.com/repos/{FACTORY_REPO}/contents/{path}"
    headers = _github_headers()

    sha = None
    try:
        existing = requests.get(
            api_url, headers=headers, params={"ref": FACTORY_BRANCH}, timeout=30
        )
        if existing.status_code == 200:
            sha = (existing.json() or {}).get("sha")
        elif existing.status_code != 404:
            frappe.throw(
                _(
                    "Could not read the existing review state. GitHub responded "
                    "with status {0}."
                ).format(existing.status_code)
            )
    except requests.exceptions.RequestException as e:
        frappe.throw(_("Could not connect to the GitHub API: {0}").format(e))

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": FACTORY_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    try:
        response = requests.put(api_url, headers=headers, json=payload, timeout=30)
    except requests.exceptions.RequestException as e:
        frappe.throw(_("Could not connect to the GitHub API: {0}").format(e))
    if response.status_code not in (200, 201):
        frappe.throw(
            _("Failed to write the review state. GitHub responded with status {0}: {1}").format(
                response.status_code, response.text[:500]
            )
        )
