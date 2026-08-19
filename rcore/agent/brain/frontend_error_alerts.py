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

"""Scheduled alerting for frontend errors captured by the Brain.

Frontend errors reach the backend via telemetry's ``log_frontend_error``,
which records a "Frontend Error: ..." event against an Engram (usually the
reporting user's). Until now those events were stored but nobody was ever
notified. This task scans recently active Engrams for new frontend-error
lines and emails a digest to System Managers.

Rules:
- ``timing_report`` events are EXCLUDED — they are ~2-minute performance
  pings from every client, not errors (known pollution of the error stream).
- One digest email per run at most, errors grouped by signature with
  occurrence counts, and a signature is not re-alerted within
  ``REALERT_HOURS`` — so a repeating error cannot spam per-occurrence.
- Admin-only: the digest goes to System Managers. Students never see any
  of this detail (student-facing surfaces only ever show friendly lines).
"""

import hashlib
import json
import re
from html import escape as escape_html

import frappe
from frappe.utils import add_to_date, get_datetime, getdate, now_datetime
from frappe.utils.user import get_system_managers

# How far back the very first run (no stored marker) looks.
FIRST_RUN_LOOKBACK_HOURS = 24

# A signature already alerted within this window is not emailed again.
REALERT_HOURS = 24

# Alerted-signature bookkeeping older than this is pruned.
PRUNE_DAYS = 7

# Event types that are telemetry noise, never real errors.
EXCLUDED_TYPES = ("timing_report",)

LAST_RUN_KEY = "frontend_error_digest_last_run"
ALERTED_KEY = "frontend_error_digest_alerted"

# Engram summary lines for frontend errors look like (note: the event
# pipeline lower-cases everything after the first character):
#   "Frontend error: <message> at url: <url> by <full name> on 2026-08-14."
# optionally with "(via AI)" before the final period.
FRONTEND_ERROR_LINE = re.compile(
    r"^(?P<event>frontend error:.*?)\s+by\s+(?P<user>.+?)\s+on\s+(?P<date>\d{4}-\d{2}-\d{2})"
    r"(?:\s*\(via ai\))?\.?$",
    re.IGNORECASE,
)

URL_SPLIT = re.compile(r"\s+at url:\s+", re.IGNORECASE)


def _split_signature(event_text):
    """Splits a matched event into (signature, url). The URL suffix is kept
    out of the signature so the same error on different pages dedupes as one."""
    parts = URL_SPLIT.split(event_text, maxsplit=1)
    signature = re.sub(r"\s+", " ", parts[0]).strip().lower()
    url = parts[1].strip() if len(parts) > 1 else None
    return signature, url


def _extract_frontend_error_events(summary, since_date=None):
    """Returns a list of {signature, url, user, date} dicts for every
    frontend-error line in an Engram summary, excluding EXCLUDED_TYPES and,
    when since_date is given, lines dated before it."""
    events = []
    for line in (summary or "").splitlines():
        match = FRONTEND_ERROR_LINE.match(line.strip())
        if not match:
            continue

        signature, url = _split_signature(match.group("event"))
        if any(excluded in signature for excluded in EXCLUDED_TYPES):
            continue

        line_date = getdate(match.group("date"))
        if since_date and line_date < since_date:
            continue

        events.append({
            "signature": signature,
            "url": url,
            "user": match.group("user").strip(),
            "date": line_date,
        })
    return events


def _load_alerted():
    try:
        alerted = json.loads(frappe.db.get_default(ALERTED_KEY) or "{}")
        return alerted if isinstance(alerted, dict) else {}
    except Exception:
        return {}


def _prune_alerted(alerted, now):
    cutoff = add_to_date(now, days=-PRUNE_DAYS)
    return {
        sig: ts for sig, ts in alerted.items()
        if get_datetime(ts) and get_datetime(ts) > cutoff
    }


def _signature_hash(signature):
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]


def _build_digest_html(groups):
    rows = []
    for group in groups:
        urls = ", ".join(sorted(group["urls"])[:3]) or "-"
        users = ", ".join(sorted(group["users"])[:5]) or "-"
        rows.append(
            "<li><b>{signature}</b><br>"
            "Occurrences since last digest: {count} &middot; "
            "Affected users: {users} &middot; URLs: {urls}</li>".format(
                signature=escape_html(group["signature"]),
                count=group["count"],
                users=escape_html(users),
                urls=escape_html(urls),
            )
        )
    return (
        "<p>New frontend errors were reported by the app. "
        "Details below are admin-only — students only ever see friendly "
        "error lines.</p><ul>{rows}</ul>"
        "<p>Source: Engram frontend-error events on this site "
        "(timing_report telemetry excluded). A repeating error is "
        "re-alerted at most once every {hours} hours.</p>".format(
            rows="".join(rows), hours=REALERT_HOURS
        )
    )


def send_frontend_error_digest():
    """Hourly scheduled task: email System Managers a digest of new
    frontend errors. Safe no-op when there is nothing new to report."""
    if frappe.conf.get("app_role") != "tenant":
        return

    if not frappe.db.exists("DocType", "Engram"):
        return

    now = now_datetime()
    last_run = get_datetime(frappe.db.get_default(LAST_RUN_KEY)) if frappe.db.get_default(LAST_RUN_KEY) else None
    since = last_run or add_to_date(now, hours=-FIRST_RUN_LOOKBACK_HOURS)

    engrams = frappe.get_all(
        "Engram",
        filters={"last_activity_date": [">", since]},
        fields=["name", "reference_doctype", "reference_name", "summary"],
    )

    # Group new error events by signature.
    groups = {}
    for engram in engrams:
        for event in _extract_frontend_error_events(engram.summary, since_date=getdate(since)):
            group = groups.setdefault(event["signature"], {
                "signature": event["signature"],
                "count": 0,
                "users": set(),
                "urls": set(),
            })
            group["count"] += 1
            group["users"].add(event["user"])
            if event["url"]:
                group["urls"].add(event["url"])

    # Dedupe: drop signatures already alerted within REALERT_HOURS.
    alerted = _prune_alerted(_load_alerted(), now)
    realert_cutoff = add_to_date(now, hours=-REALERT_HOURS)
    fresh_groups = []
    for signature, group in groups.items():
        sig_hash = _signature_hash(signature)
        last_alerted = get_datetime(alerted.get(sig_hash)) if alerted.get(sig_hash) else None
        if last_alerted and last_alerted > realert_cutoff:
            continue
        fresh_groups.append(group)

    if fresh_groups:
        recipients = [
            user for user in (get_system_managers(only_name=False) or [])
            if user and user != "Administrator"
        ]
        if recipients:
            fresh_groups.sort(key=lambda g: g["count"], reverse=True)
            try:
                frappe.sendmail(
                    recipients=recipients,
                    subject="[{site}] {count} new frontend error{plural}".format(
                        site=frappe.local.site,
                        count=len(fresh_groups),
                        plural="" if len(fresh_groups) == 1 else "s",
                    ),
                    message=_build_digest_html(fresh_groups),
                )
                for group in fresh_groups:
                    alerted[_signature_hash(group["signature"])] = str(now)
            except Exception:
                frappe.log_error(
                    frappe.get_traceback(), "Frontend Error Digest Send Failed"
                )

    frappe.db.set_default(LAST_RUN_KEY, str(now))
    frappe.db.set_default(ALERTED_KEY, json.dumps(alerted))
    frappe.db.commit()
