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

"""Pure shape rules for the knowledge-bites index (decision #52).

Deliberately frappe-free: `api/knowledge_bites.py` does the storage I/O,
this module does the DECIDING — what counts as a well-formed published
index. Keeping the shape gate out of the API file is what makes it
unit-testable without a bench/site (same split as alert_rules.py).

The contract (mirrors the skills-index `{"skills": {...}}` gate, one level
deeper because bites are per-lesson LISTS):

    {"bites": {"<lesson-slug>": [ {bite object}, ... ], ...}}

- `bites` must be a dict keyed by lesson-slug (the slug of the session-tree
  lesson under `session/{grade}/{term}/{topic}/` the bite is tied to —
  decision #52's join key).
- every value must be a LIST of dicts (one lesson can carry several bites;
  the client offers exactly one, deterministically).

Anything else is malformed. The read endpoint degrades a malformed document
to the empty index (bites are opt-in extras — never an error surface); the
publish endpoint refuses it outright.
"""

EMPTY_INDEX = {"bites": {}}


def is_valid_bites_index(parsed):
    """Whether `parsed` is a well-formed bites index document."""
    if not isinstance(parsed, dict):
        return False
    bites = parsed.get("bites")
    if not isinstance(bites, dict):
        return False
    for entries in bites.values():
        if not isinstance(entries, list):
            return False
        if any(not isinstance(e, dict) for e in entries):
            return False
    return True


def count_bites(parsed):
    """(lessons, bites) totals for a VALID index — the publish receipt."""
    bites = parsed["bites"]
    return len(bites), sum(len(entries) for entries in bites.values())
