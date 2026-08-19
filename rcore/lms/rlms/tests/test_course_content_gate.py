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

"""#25 keep-the-listing/withhold-the-keys on get_course_content, pinned
standalone (`python -m unittest discover` from this directory — no frappe,
no site).

api/course.py imports frappe and its rlms siblings at module level, so —
matching replay's test_airing_context.py — a minimal in-memory frappe stub
plus stub sibling packages stand in, and the module is loaded by file path
under a synthetic package so its relative imports resolve. The serving
verdict itself is pinned by test_entitlements.py/test_time_gates.py; here
_session_serving_verdict is monkeypatched per test to observe how
get_course_content applies its answer."""

import importlib.util
import os
import sys
import types
import unittest

_HERE = os.path.dirname(__file__)
_PKG = "rlms_course_gate_test_pkg"


class _Thrown(Exception):
    pass


def _make_frappe_stub():
    frappe = types.ModuleType("frappe")

    def throw(msg, exc=Exception):
        raise _Thrown(msg)

    frappe.throw = throw
    frappe.whitelist = lambda *a, **k: (lambda f: f)
    frappe.session = types.SimpleNamespace(user="student@example.com")
    frappe.PermissionError = _Thrown
    frappe._ = lambda s: s
    frappe.get_all = lambda *a, **k: []
    frappe.db = types.SimpleNamespace(
        get_value=lambda *a, **k: None, exists=lambda *a, **k: False
    )

    frappe_utils = types.ModuleType("frappe.utils")
    frappe_utils.now_datetime = __import__("datetime").datetime.now
    frappe_utils.get_datetime = lambda v: v
    frappe.utils = frappe_utils

    return {"frappe": frappe, "frappe.utils": frappe_utils}


def _load_course_module():
    """Load api/course.py as ``<pkg>.api.course`` with stubbed siblings so
    its relative imports (maths_track, role_exclusivity, student, partner)
    resolve without a composed app."""
    stubs = dict(_make_frappe_stub())

    pkg = types.ModuleType(_PKG)
    pkg.__path__ = []
    pkg.maths_track = types.ModuleType(f"{_PKG}.maths_track")
    pkg.role_exclusivity = types.ModuleType(f"{_PKG}.role_exclusivity")
    api_pkg = types.ModuleType(f"{_PKG}.api")
    api_pkg.__path__ = []
    student = types.ModuleType(f"{_PKG}.api.student")
    student.lesson_serving_verdict = lambda *a, **k: "allowed"
    partner = types.ModuleType(f"{_PKG}.api.partner")
    partner.enforce_role_exclusivity = lambda *a, **k: None

    stubs.update(
        {
            _PKG: pkg,
            f"{_PKG}.maths_track": pkg.maths_track,
            f"{_PKG}.role_exclusivity": pkg.role_exclusivity,
            f"{_PKG}.api": api_pkg,
            f"{_PKG}.api.student": student,
            f"{_PKG}.api.partner": partner,
        }
    )

    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        path = os.path.join(_HERE, "..", "api", "course.py")
        spec = importlib.util.spec_from_file_location(f"{_PKG}.api.course", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{_PKG}.api.course"] = module
        spec.loader.exec_module(module)
        return module, stubs["frappe"]
    finally:
        for name, original in saved.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original
        sys.modules.pop(f"{_PKG}.api.course", None)


course, frappe_stub = _load_course_module()


class _AttrDict(dict):
    """frappe._dict's attribute access, as get_all rows have in production."""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


def _catalog_get_all(lessons_by_chapter):
    """A frappe.get_all fake serving one course with the given chapters."""

    def get_all(doctype, filters=None, fields=None, order_by=None, **kwargs):
        if doctype == "Course Chapter":
            return [
                _AttrDict({"name": name, "title": name.title(), "sequence": i + 1})
                for i, name in enumerate(lessons_by_chapter)
            ]
        if doctype == "Course Lesson":
            chapter = (filters or {}).get("chapter")
            return [_AttrDict(row) for row in lessons_by_chapter.get(chapter, [])]
        raise AssertionError(f"unexpected get_all({doctype})")

    return get_all


class TestCourseContentKeyWithholding(unittest.TestCase):
    """The listing always comes back; session_id only rides along where the
    caller's serving verdict is 'allowed' — and any failure to obtain a
    verdict withholds the key (fail closed), never errors."""

    def setUp(self):
        self._orig_verdict = course._session_serving_verdict
        self._orig_get_all = frappe_stub.get_all

    def tearDown(self):
        course._session_serving_verdict = self._orig_verdict
        frappe_stub.get_all = self._orig_get_all

    def _serve(self, lessons, verdict):
        frappe_stub.get_all = _catalog_get_all({"ch1": lessons})
        course._session_serving_verdict = verdict
        return course.get_course_content("maths-g10")

    def test_allowed_verdict_keeps_the_session_id(self):
        chapters = self._serve(
            [{"name": "l1", "title": "Algebra", "sequence": 1,
              "session_id": "sess-1", "is_free_sample": 0}],
            lambda *a, **k: "allowed",
        )
        self.assertEqual(chapters[0]["lessons"][0]["session_id"], "sess-1")

    def test_disallowed_verdict_withholds_only_the_key(self):
        chapters = self._serve(
            [{"name": "l1", "title": "Algebra", "sequence": 1,
              "session_id": "sess-1", "is_free_sample": 0}],
            lambda *a, **k: "needs_active",
        )
        lesson = chapters[0]["lessons"][0]
        # The key is withheld…
        self.assertIsNone(lesson["session_id"])
        # …but the listing survives (name/title/sequence untouched) — the
        # catalog keeps its cards, same as get_upcoming_sessions.
        self.assertEqual(lesson["name"], "l1")
        self.assertEqual(lesson["title"], "Algebra")
        self.assertEqual(lesson["sequence"], 1)
        # And the verdict input never leaks into the response shape.
        self.assertNotIn("is_free_sample", lesson)

    def test_verdict_failure_fails_closed(self):
        def broken(*a, **k):
            raise RuntimeError("gate unavailable")

        chapters = self._serve(
            [{"name": "l1", "title": "Algebra", "sequence": 1,
              "session_id": "sess-1", "is_free_sample": 0}],
            broken,
        )
        self.assertIsNone(chapters[0]["lessons"][0]["session_id"])

    def test_lesson_without_session_asks_no_verdict(self):
        calls = []

        def recording(*a, **k):
            calls.append((a, k))
            return "allowed"

        chapters = self._serve(
            [{"name": "l1", "title": "Algebra", "sequence": 1,
              "session_id": "", "is_free_sample": 0}],
            recording,
        )
        self.assertEqual(calls, [])
        self.assertIsNone(chapters[0]["lessons"][0]["session_id"])

    def test_verdict_sees_lesson_and_free_sample_flag(self):
        # The free-sample bypass and per-lesson-purchase override live in
        # _session_serving_verdict — the endpoint must hand it the lesson
        # name and the flag exactly as get_lesson_session's path does.
        calls = []

        def recording(user, session_id, lesson=None, is_free_sample=False):
            calls.append((user, session_id, lesson, is_free_sample))
            return "allowed"

        self._serve(
            [{"name": "l1", "title": "Algebra", "sequence": 1,
              "session_id": "sess-1", "is_free_sample": 1}],
            recording,
        )
        self.assertEqual(
            calls, [("student@example.com", "sess-1", "l1", True)]
        )

    def test_mixed_lessons_are_decided_per_lesson(self):
        chapters = self._serve(
            [
                {"name": "l1", "title": "A", "sequence": 1,
                 "session_id": "sess-1", "is_free_sample": 0},
                {"name": "l2", "title": "B", "sequence": 2,
                 "session_id": "sess-2", "is_free_sample": 0},
            ],
            lambda user, session_id, **k: (
                "allowed" if session_id == "sess-2" else "not_covered"
            ),
        )
        lessons = chapters[0]["lessons"]
        self.assertIsNone(lessons[0]["session_id"])
        self.assertEqual(lessons[1]["session_id"], "sess-2")


if __name__ == "__main__":
    unittest.main()
