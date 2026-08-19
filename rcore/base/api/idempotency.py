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

"""Idempotency-key dedupe for write endpoints replayed by the app's sync
engine.

The Flutter SDKs' sync handlers retry queued writes after ambiguous network
failures and send an ``X-Idempotency-Key`` header (one client UUID per queued
op) on the create endpoints they call. Without server-side dedupe a retry can
re-execute the write and double-create (worst case: duplicate orders).

``@idempotent`` closes that hole: the first request carrying a given key
executes normally and its response payload is persisted in the
``Idempotency Key`` doctype; any repeat of the same key returns the stored
response (marked with ``idempotent_replay: True``) instead of re-executing.
Requests without the header are untouched. Stored keys are purged after
30 days by the daily ``purge_expired_idempotency_keys`` scheduler task.
"""

import json
from functools import wraps
from typing import Any, Callable, Optional

import frappe

IDEMPOTENCY_HEADER = "X-Idempotency-Key"

#: Client keys are UUIDs (36 chars); anything longer than this is a
#: malformed or abusive value, not a key.
MAX_KEY_LENGTH = 140

#: How long stored keys are honoured before the daily purge removes them.
KEY_RETENTION_DAYS = 30

_MISSING = object()


def get_idempotency_key() -> Optional[str]:
    """The current request's X-Idempotency-Key header value, or None.

    Returns None outside a request context (scheduler jobs, bench console)
    and for requests that do not send the header, so the guard is a no-op
    everywhere except replayed sync uploads.
    """
    request = getattr(frappe.local, "request", None)
    if request is None:
        return None
    key = (request.headers.get(IDEMPOTENCY_HEADER) or "").strip()
    if not key:
        return None
    if len(key) > MAX_KEY_LENGTH:
        frappe.throw(
            f"{IDEMPOTENCY_HEADER} must be at most "
            f"{MAX_KEY_LENGTH} characters.",
            frappe.ValidationError,
        )
    return key


def idempotent(fn: Callable) -> Callable:
    """Decorator making a whitelisted write endpoint replay-safe.

    Place it *under* ``@frappe.whitelist(...)``::

        @frappe.whitelist()
        @idempotent
        def create_order(order_data):
            ...

    Behaviour when the request carries an X-Idempotency-Key:

    - first call: the endpoint runs; its return value is stored against the
      key (same transaction as the write itself, so a rolled-back failure
      stores nothing and the client may retry).
    - repeat call with the same key, same user, same endpoint: the stored
      response is returned with ``idempotent_replay: True`` added, and the
      endpoint body is NOT re-executed.
    - same key but a different user or endpoint: rejected with a
      ValidationError — a key never replays another user's response.

    Duplicate requests racing in parallel are resolved by the unique
    constraint on the key: the first insert wins and the loser keeps its own
    (equivalent) result. The mobile sync engine retries sequentially, so in
    practice replays hit the stored-response path.
    """
    endpoint = f"{fn.__module__}.{fn.__name__}"

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        key = get_idempotency_key()
        if not key:
            return fn(*args, **kwargs)

        stored = _stored_response(key, endpoint)
        if stored is not _MISSING:
            return stored

        result = fn(*args, **kwargs)
        _store_response(key, endpoint, result)
        return result

    return wrapper


def _stored_response(key: str, endpoint: str) -> Any:
    """The response stored for `key`, or _MISSING when the key is unused."""
    row = frappe.db.get_value(
        "Idempotency Key",
        key,
        ["user", "endpoint", "response"],
        as_dict=True,
    )
    if not row:
        return _MISSING

    if row.user != frappe.session.user or row.endpoint != endpoint:
        frappe.throw(
            "This idempotency key was already used by a different "
            "user or endpoint.",
            frappe.ValidationError,
        )

    replay = json.loads(row.response) if row.response else None
    if isinstance(replay, dict):
        replay = dict(replay)
        replay["idempotent_replay"] = True
    return replay


def _store_response(key: str, endpoint: str, result: Any) -> None:
    """Persist `result` against `key` so repeats replay instead of re-run."""
    try:
        frappe.get_doc(
            {
                "doctype": "Idempotency Key",
                "idempotency_key": key,
                "user": frappe.session.user,
                "endpoint": endpoint,
                # frappe.as_json handles datetimes/Decimals in doc dicts the
                # same way the HTTP layer serializes them.
                "response": frappe.as_json(result),
            }
        ).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        # A parallel duplicate won the insert; this execution's own result
        # is equivalent, so keep it and let the stored row serve future
        # replays.
        pass
