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

"""Tutor-catalog publish/read rules — frappe-free pure module.

The tutor discovery deck's server-side catalog (LMS Tutor Catalog, a
published Single mirroring LMS Skills Index) is validated here at publish
time and grade-filtered here at read time. API files own the I/O and call
these for the judgement (SDK_README "Testable Backend Logic" — this module
imports no frappe and is unit-tested standalone).

The hard rule this module exists to enforce: `rating` and `enrolled_count`
are OPTIONAL. rlms has no rating doctype, so today NO real rating data
exists anywhere — a publish may omit the keys (or send null) and the server
never fabricates a value. When present, a rating must be a number in 0..5
and enrolled_count a non-negative integer, so a later real rating surface
reuses the same keys with no contract change.
"""


class CatalogError(ValueError):
    """A published catalog payload that violates the contract."""


def _is_number(value):
    """True for int/float but NOT bool (bool subclasses int in python)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _display_name(entry):
    """The entry's human name: `display_name` with `name` as the fallback,
    the same precedence TutorProfile.fromJson uses client-side."""
    return entry.get("display_name") or entry.get("name")


def validate_catalog(parsed):
    """Validates a parsed catalog payload; raises CatalogError on the first
    violation and returns the tutors list when valid.

    Shape: an object with a `"tutors"` list. Each entry is an object with a
    non-empty string `id` and a non-empty string name (`display_name`, or
    `name` — the client reads either). `rating`, when present and non-null,
    must be a number in 0..5; `enrolled_count` a non-negative integer.
    Unknown keys pass through untouched — the doctype stores the payload
    verbatim, so the catalog can grow fields without a server change.
    """
    if not isinstance(parsed, dict) or not isinstance(parsed.get("tutors"), list):
        raise CatalogError('catalog_json must be an object with a "tutors" list.')
    for i, entry in enumerate(parsed["tutors"]):
        if not isinstance(entry, dict):
            raise CatalogError("tutors[%d] must be an object." % i)
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise CatalogError("tutors[%d] must have a non-empty string id." % i)
        name = _display_name(entry)
        if not isinstance(name, str) or not name.strip():
            raise CatalogError(
                "tutors[%d] must have a non-empty display_name (or name)." % i
            )
        rating = entry.get("rating")
        if rating is not None and (not _is_number(rating) or not 0 <= rating <= 5):
            raise CatalogError(
                "tutors[%d].rating must be a number in 0..5 when present." % i
            )
        enrolled = entry.get("enrolled_count")
        if enrolled is not None and (
            not isinstance(enrolled, int)
            or isinstance(enrolled, bool)
            or enrolled < 0
        ):
            raise CatalogError(
                "tutors[%d].enrolled_count must be a non-negative integer "
                "when present." % i
            )
    return parsed["tutors"]


def filter_by_grade(tutors, grade):
    """The discovery deck's grade filter, identical to the client's
    SeededTutorCatalog.getTutors: no grade = the whole team (the parent's
    view); a grade keeps entries whose `grades` list contains it OR whose
    primary `grade` equals it (empty `grades` falls back to `grade`)."""
    if not grade:
        return list(tutors)
    kept = []
    for entry in tutors:
        grades = entry.get("grades")
        in_grades = isinstance(grades, list) and grade in grades
        if in_grades or entry.get("grade") == grade:
            kept.append(entry)
    return kept
