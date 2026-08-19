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

"""Replay-safety of the two progress upload endpoints, pinned standalone
(no frappe, no site — `python -m unittest tests.test_progress_idempotency`).

record_video_watch accumulates `current + watch_time` and record_quiz_result
is a bare insert, so a client retry after an ambiguous network failure
(timeout-after-commit) used to double-count watch time / duplicate quiz rows.
Both are now wrapped in core's REAL `@idempotent` decorator
(core/base/frappe/src/api/idempotency.py, composed as
`paas.api.idempotency`) — this test loads that real decorator by file path,
not a mock of it, and exercises it end-to-end against a stubbed in-memory
`frappe`.

Loading follows the file-path pattern of test_time_gates.py /
test_alert_rules.py (workspace modules import through an `rcore`
placeholder that only resolves inside a composed app), extended with the
sys.modules pre-registration approach of
agent/frappe/src/tests/verify_interactive_api.py: a stub `frappe` module is
registered first, core's idempotency.py is loaded against it, registered as
`paas.api.idempotency`, and progress.py's source is loaded with `rcore`
resolved to `paas` — exactly what the composer does at compose time.

Core's checkout is located via ROKCT_CORE_PATH, a sibling `core/` checkout,
or /workspace/core; the module skips (not fails) when none exists, since the
agent repo cannot vendor core's source.
"""

import importlib.util
import json
import os
import sys
import types
import unittest

# --------------------------------------------------------------------------
# Locate core's real idempotency.py
# --------------------------------------------------------------------------

_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
)


def _find_core_idempotency():
    candidates = []
    env = os.environ.get("ROKCT_CORE_PATH")
    if env:
        candidates.append(env)
    candidates.append(os.path.join(_REPO_ROOT, "..", "core"))
    candidates.append("/workspace/core")
    for root in candidates:
        path = os.path.join(root, "base", "frappe", "src", "api", "idempotency.py")
        if os.path.isfile(path):
            return path
    return None


_IDEMPOTENCY_PATH = _find_core_idempotency()
if _IDEMPOTENCY_PATH is None:
    raise unittest.SkipTest(
        "RokctAI/core checkout not found (set ROKCT_CORE_PATH, or place a "
        "`core` checkout next to this repo) — cannot load the real "
        "@idempotent decorator."
    )

# --------------------------------------------------------------------------
# Stub frappe backed by an in-memory store (sys.modules pre-registration)
# --------------------------------------------------------------------------

_STORE = {}  # doctype -> {docname: row dict}
_COUNTER = {"n": 0}


class _ValidationError(Exception):
    pass


class _DuplicateEntryError(Exception):
    pass


def _rows(doctype):
    return _STORE.setdefault(doctype, {})


class _DB:
    def exists(self, doctype, filters):
        rows = _rows(doctype)
        if isinstance(filters, dict):
            for name, row in rows.items():
                if all(row.get(k) == v for k, v in filters.items()):
                    return name
            return None
        return filters if filters in rows else None

    def get_value(self, doctype, name, fieldname, as_dict=False):
        docname = self.exists(doctype, name) if isinstance(name, dict) else name
        row = _rows(doctype).get(docname)
        if row is None:
            return None
        if isinstance(fieldname, (list, tuple)):
            data = {f: row.get(f) for f in fieldname}
            if as_dict:
                return types.SimpleNamespace(**data)
            return tuple(data.values())
        return row.get(fieldname)

    def set_value(self, doctype, name, field, value):
        _rows(doctype)[name][field] = value


class _Doc:
    def __init__(self, data):
        self._data = dict(data)
        self.name = None

    def insert(self, ignore_permissions=False):
        doctype = self._data["doctype"]
        rows = _rows(doctype)
        if doctype == "Idempotency Key":
            name = self._data["idempotency_key"]
            if name in rows:
                raise _DuplicateEntryError(name)
        else:
            _COUNTER["n"] += 1
            name = f"{doctype}-{_COUNTER['n']:05d}"
        self.name = name
        rows[name] = {k: v for k, v in self._data.items() if k != "doctype"}
        return self


def _get_doc(arg, *args):
    if isinstance(arg, dict):
        return _Doc(arg)
    raise NotImplementedError("stub get_doc only supports dict input")


def _throw(msg, exc=_ValidationError):
    raise exc(msg)


def _whitelist(*args, **kwargs):
    def deco(fn):
        return fn

    return deco


_frappe = types.ModuleType("frappe")
_frappe.db = _DB()
_frappe.get_doc = _get_doc
_frappe.throw = _throw
_frappe.whitelist = _whitelist
_frappe.as_json = json.dumps
_frappe.ValidationError = _ValidationError
_frappe.DuplicateEntryError = _DuplicateEntryError
_frappe.session = types.SimpleNamespace(user="student@example.com")
_frappe.local = types.SimpleNamespace(request=None)

sys.modules["frappe"] = _frappe

# --------------------------------------------------------------------------
# Load core's REAL idempotency.py against the stub, register as paas.api.*
# --------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "paas.api.idempotency", _IDEMPOTENCY_PATH
)
idempotency = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(idempotency)

_paas_pkg = types.ModuleType("paas")
_paas_pkg.__path__ = []
_paas_api_pkg = types.ModuleType("paas.api")
_paas_api_pkg.__path__ = []
_paas_api_pkg.idempotency = idempotency
_paas_pkg.api = _paas_api_pkg
sys.modules["paas"] = _paas_pkg
sys.modules["paas.api"] = _paas_api_pkg
sys.modules["paas.api.idempotency"] = idempotency

# --------------------------------------------------------------------------
# Load progress.py with rcore resolved to paas (what the composer does)
# --------------------------------------------------------------------------

_PROGRESS_PATH = os.path.join(os.path.dirname(__file__), "..", "api", "progress.py")
with open(_PROGRESS_PATH, encoding="utf-8") as f:
    _source = f.read().replace("rcore", "paas")
progress = types.ModuleType("paas.rlms.api.progress")
progress.__file__ = _PROGRESS_PATH
exec(compile(_source, _PROGRESS_PATH, "exec"), progress.__dict__)


KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"


def _send_with_key(key):
    """Simulate a request carrying X-Idempotency-Key: [key] (None = no header)."""
    if key is None:
        _frappe.local.request = types.SimpleNamespace(headers={})
    else:
        _frappe.local.request = types.SimpleNamespace(
            headers={idempotency.IDEMPOTENCY_HEADER: key}
        )


class _IdempotencyCase(unittest.TestCase):
    def setUp(self):
        _STORE.clear()
        _COUNTER["n"] = 0
        _frappe.local.request = None
        _frappe.session.user = "student@example.com"

    def _watch_rows(self):
        return list(_rows("LMS Video Watch Duration").values())

    def _quiz_rows(self):
        return list(_rows("LMS Lesson Quiz Result").values())


class TestVideoWatchReplay(_IdempotencyCase):
    def test_same_key_accumulates_exactly_once_and_replays_response(self):
        # The timeout-after-commit retry: identical request, identical key.
        _send_with_key(KEY_A)
        first = progress.record_video_watch("L1", "youtube", 30)
        second = progress.record_video_watch("L1", "youtube", 30)

        rows = self._watch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["watch_time"], 30.0)  # not 60.0
        self.assertEqual(second, first)  # stored response replayed

        # The dedupe went through the real Idempotency Key store.
        keys = _rows("Idempotency Key")
        self.assertEqual(list(keys), [KEY_A])
        self.assertIn("record_video_watch", keys[KEY_A]["endpoint"])

    def test_retry_of_an_accumulation_applies_it_once(self):
        # Row already exists from an earlier op; a later op's retry must not
        # re-run `current + watch_time`.
        _send_with_key(KEY_A)
        progress.record_video_watch("L1", "youtube", 30)
        _send_with_key(KEY_B)
        progress.record_video_watch("L1", "youtube", 45)
        progress.record_video_watch("L1", "youtube", 45)  # retry, same key

        rows = self._watch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["watch_time"], 75.0)  # 30 + 45, not 30 + 90

    def test_no_header_executes_normally_each_call(self):
        _send_with_key(None)
        progress.record_video_watch("L1", "youtube", 30)
        progress.record_video_watch("L1", "youtube", 30)

        rows = self._watch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["watch_time"], 60.0)
        self.assertEqual(_rows("Idempotency Key"), {})

    def test_no_request_context_executes_normally(self):
        # Scheduler/console path: frappe.local has no request at all.
        _frappe.local.request = None
        progress.record_video_watch("L1", "youtube", 30)
        progress.record_video_watch("L1", "youtube", 30)
        self.assertEqual(self._watch_rows()[0]["watch_time"], 60.0)

    def test_different_keys_are_two_distinct_ops(self):
        _send_with_key(KEY_A)
        progress.record_video_watch("L1", "youtube", 30)
        _send_with_key(KEY_B)
        progress.record_video_watch("L1", "youtube", 30)

        rows = self._watch_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["watch_time"], 60.0)
        self.assertEqual(len(_rows("Idempotency Key")), 2)


class TestQuizResultReplay(_IdempotencyCase):
    def test_same_key_inserts_exactly_one_row(self):
        _send_with_key(KEY_A)
        first = progress.record_quiz_result("L1", "q1", "correct")
        second = progress.record_quiz_result("L1", "q1", "correct")

        rows = self._quiz_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["question_id"], "q1")
        self.assertEqual(second, first)

    def test_different_keys_insert_two_rows(self):
        # Two genuine answers to different questions, each with its own op id.
        _send_with_key(KEY_A)
        progress.record_quiz_result("L1", "q1", "correct")
        _send_with_key(KEY_B)
        progress.record_quiz_result("L1", "q2", "skipped")
        self.assertEqual(len(self._quiz_rows()), 2)

    def test_no_header_inserts_each_time(self):
        _send_with_key(None)
        progress.record_quiz_result("L1", "q1", "correct")
        progress.record_quiz_result("L1", "q1", "correct")
        self.assertEqual(len(self._quiz_rows()), 2)


class TestKeyScoping(unittest.TestCase):
    """The contract's cross-user guard, via the real decorator."""

    def setUp(self):
        _STORE.clear()
        _COUNTER["n"] = 0
        _frappe.session.user = "student@example.com"

    def tearDown(self):
        _frappe.session.user = "student@example.com"
        _frappe.local.request = None

    def test_another_users_key_is_rejected_not_replayed(self):
        _send_with_key(KEY_A)
        progress.record_video_watch("L1", "youtube", 30)
        _frappe.session.user = "other@example.com"
        with self.assertRaises(_ValidationError):
            progress.record_video_watch("L1", "youtube", 30)


if __name__ == "__main__":
    unittest.main()
