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

"""Maths-track exclusivity (product log #29) — frappe-free pure module.

Real CAPS rule: a student takes Mathematics OR Mathematical Literacy,
NEVER both. The track is chosen at subscribe time; the app must refuse a
second-track enrolment. Same class of rule as the teacher-cannot-pay check
(#33) — enforced where enrolments/subscriptions are RECORDED, not merely
hidden in the picker.

Vocabulary this must agree with, deliberately checked against both sides:
- factory content slugs: `maths` and `mathematical_literacy`
  (factory/lessons/curriculum/CAPS/…),
- the client badge's matcher, which is a loose
  `subject.toLowerCase().contains('literacy')`
  (lms_sdk MathTrackBadge.isLiteracy).
So literacy detection here is the same loose substring test, and core-maths
detection accepts the maths spellings the catalog actually uses. Anything
that is neither is not a maths subject at all and never constrains a
student (history, geography, …).
"""

CORE = "maths"
LITERACY = "mathematical_literacy"

# Spellings the catalog/manifests use for the CORE track. Literacy is
# matched by substring instead (see module doc), so it needs no list.
_CORE_TOKENS = ("maths", "mathematics", "mathematic", "math")


def track_of(subject):
    """Which maths track [subject] belongs to: [CORE], [LITERACY], or None
    for a non-maths subject. Literacy is tested FIRST — 'Mathematical
    Literacy' contains a core token too, and the literacy reading wins."""
    if not subject:
        return None
    text = str(subject).strip().lower()
    if not text:
        return None
    if "literacy" in text:
        return LITERACY
    normalised = text.replace("-", " ").replace("_", " ")
    words = normalised.split()
    if any(w.startswith(t) for w in words for t in ("math",)):
        return CORE
    if normalised in _CORE_TOKENS:
        return CORE
    return None


def conflicting_track(existing_subjects, new_subject):
    """The track already held that BLOCKS taking [new_subject], or None
    when the enrolment is allowed.

    Only the opposite maths track blocks: re-enrolling in the same track is
    fine (idempotent), and non-maths subjects never conflict in either
    direction.
    """
    new_track = track_of(new_subject)
    if new_track is None:
        return None
    for subject in existing_subjects or ():
        held = track_of(subject)
        if held is not None and held != new_track:
            return held
    return None


def track_label(track):
    """Human-readable track name for an error message."""
    if track == LITERACY:
        return "Mathematical Literacy"
    if track == CORE:
        return "Mathematics"
    return str(track)
