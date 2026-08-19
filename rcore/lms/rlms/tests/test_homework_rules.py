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

"""Async homework help (product log #42 item 1 = #4 send-and-wait + #1
guide-don't-solve), pinned standalone (no frappe, no site —
`python -m unittest tests.test_homework_rules`).

Loaded by file path rather than package import, matching
test_time_gates.py: workspace python modules import through an `rcore`
placeholder and only resolve inside a composed app; homework_rules.py is
deliberately frappe-free so this test runs anywhere python does."""

import importlib.util
import json
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "homework_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_homework_rules", _MODULE_PATH)
homework_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(homework_rules)


VALID_MCQ = {
    "question": "Solve for x: 2x + 6 = 14",
    "options": ["x = 4", "x = 10", "x = 7", "x = -4"],
    "correct_index": 0,
    "explanation": "Subtract 6 from both sides (2x = 8), then divide by 2.",
}


class TestStatusTransitions(unittest.TestCase):
    def test_send_and_wait_happy_path(self):
        # Submitted -> In Review -> Ready -> Completed, the #4 lifecycle.
        self.assertTrue(homework_rules.can_transition("Submitted", "In Review"))
        self.assertTrue(homework_rules.can_transition("In Review", "Ready"))
        self.assertTrue(homework_rules.can_transition("Ready", "Completed"))

    def test_direct_publish_and_decline_from_submitted(self):
        # The fulfilment side may act without an explicit In Review step.
        self.assertTrue(homework_rules.can_transition("Submitted", "Ready"))
        self.assertTrue(homework_rules.can_transition("Submitted", "Declined"))
        self.assertTrue(homework_rules.can_transition("In Review", "Declined"))

    def test_terminal_states_go_nowhere(self):
        for terminal in ("Declined", "Completed"):
            for target in homework_rules.STATUSES:
                self.assertFalse(
                    homework_rules.can_transition(terminal, target),
                    "%s -> %s must be illegal" % (terminal, target),
                )

    def test_no_answering_before_ready(self):
        # Completed is only reachable FROM Ready — an attempt cannot land
        # on a question whose MCQ was never published.
        self.assertFalse(homework_rules.can_transition("Submitted", "Completed"))
        self.assertFalse(homework_rules.can_transition("In Review", "Completed"))

    def test_pending_statuses_are_the_fulfilment_queue(self):
        self.assertEqual(
            homework_rules.PENDING_STATUSES, ("Submitted", "In Review")
        )


class TestSubmissionValidation(unittest.TestCase):
    def test_normalizes_whitespace(self):
        self.assertEqual(
            homework_rules.validate_submission("  2x + 6 = 14?  "),
            "2x + 6 = 14?",
        )

    def test_empty_rejected(self):
        for bad in (None, "", "   "):
            with self.assertRaises(ValueError):
                homework_rules.validate_submission(bad)

    def test_overlong_rejected(self):
        with self.assertRaises(ValueError):
            homework_rules.validate_submission("x" * (homework_rules.MAX_QUESTION_CHARS + 1))
        # Exactly at the cap is fine.
        homework_rules.validate_submission("x" * homework_rules.MAX_QUESTION_CHARS)


class TestAttachmentValidation(unittest.TestCase):
    """Photo refs riding on a submission: server-relative upload URLs only,
    bounded count. Size is the client's job (compression); shape and count
    are the server's."""

    def test_absent_is_none(self):
        for empty in (None, "", [], "[]"):
            self.assertIsNone(
                homework_rules.validate_attachments(empty), repr(empty)
            )

    def test_valid_refs_normalized(self):
        refs = [
            "  /files/hw-page-1.jpg  ",
            "/private/files/hw-page-2.jpg",
        ]
        self.assertEqual(
            homework_rules.validate_attachments(refs),
            ["/files/hw-page-1.jpg", "/private/files/hw-page-2.jpg"],
        )

    def test_json_string_form_accepted(self):
        # Form-encoded clients send the list as a JSON string; the composed
        # endpoint must treat it identically to a real list.
        self.assertEqual(
            homework_rules.validate_attachments('["/private/files/a.jpg"]'),
            ["/private/files/a.jpg"],
        )

    def test_count_capped(self):
        at_cap = ["/files/p%d.jpg" % i for i in range(homework_rules.MAX_ATTACHMENTS)]
        self.assertEqual(len(homework_rules.validate_attachments(at_cap)),
                         homework_rules.MAX_ATTACHMENTS)
        with self.assertRaises(ValueError):
            homework_rules.validate_attachments(at_cap + ["/files/extra.jpg"])

    def test_rejects_non_upload_urls(self):
        cases = [
            ["https://evil.example/x.jpg"],
            ["//evil.example/x.jpg"],
            ["files/x.jpg"],
            ["/etc/passwd"],
            ["data:image/png;base64,AAAA"],
            ["/filesx/escape.jpg"],
        ]
        for bad in cases:
            with self.assertRaises(ValueError, msg=repr(bad)):
                homework_rules.validate_attachments(bad)

    def test_rejects_wrong_shapes(self):
        cases = [
            "not json",
            '{"file": "/files/x.jpg"}',
            {"file": "/files/x.jpg"},
            ["/files/ok.jpg", 42],
            ["/files/ok.jpg", None],
            ["  "],
            42,
        ]
        for bad in cases:
            with self.assertRaises(ValueError, msg=repr(bad)):
                homework_rules.validate_attachments(bad)


class TestAttachmentParse(unittest.TestCase):
    """Student reads of stored attachment_refs: catch-and-degrade, the
    list_homework_questions posture — bad stored data reads as no photos."""

    def test_round_trip(self):
        refs = ["/private/files/a.jpg", "/files/b.jpg"]
        stored = json.dumps(homework_rules.validate_attachments(refs))
        self.assertEqual(homework_rules.parse_attachment_refs(stored), refs)

    def test_degrades_never_raises(self):
        for raw in (None, "", "not json", '"a string"', '{"k": 1}', "[1, 2]", 7):
            self.assertEqual(
                homework_rules.parse_attachment_refs(raw), [], repr(raw)
            )

    def test_filters_non_string_entries(self):
        self.assertEqual(
            homework_rules.parse_attachment_refs('["/files/a.jpg", 3, "  "]'),
            ["/files/a.jpg"],
        )


class TestMcqPayloadValidation(unittest.TestCase):
    def test_valid_payload_normalizes(self):
        mcq = homework_rules.validate_mcq_payload(
            {**VALID_MCQ, "question": "  %s  " % VALID_MCQ["question"]}
        )
        self.assertEqual(mcq["question"], VALID_MCQ["question"])
        self.assertEqual(mcq["options"], VALID_MCQ["options"])
        self.assertEqual(mcq["correct_index"], 0)
        self.assertTrue(mcq["explanation"])

    def test_explanation_optional(self):
        payload = {k: v for k, v in VALID_MCQ.items() if k != "explanation"}
        self.assertEqual(homework_rules.validate_mcq_payload(payload)["explanation"], "")

    def test_rejects_bad_shapes(self):
        cases = [
            "not a dict",
            {**VALID_MCQ, "question": "  "},
            {**VALID_MCQ, "options": "not a list"},
            {**VALID_MCQ, "options": ["only one"]},
            {**VALID_MCQ, "options": ["a", ""]},
            {**VALID_MCQ, "options": ["dup", "dup", "other"]},
            {**VALID_MCQ, "options": [str(i) for i in range(homework_rules.MAX_OPTIONS + 1)]},
            {**VALID_MCQ, "correct_index": "0"},
            {**VALID_MCQ, "correct_index": True},
            {**VALID_MCQ, "correct_index": 4},
            {**VALID_MCQ, "correct_index": -1},
        ]
        for payload in cases:
            with self.assertRaises(ValueError, msg=repr(payload)):
                homework_rules.validate_mcq_payload(payload)


class TestGuideDontSolveReveal(unittest.TestCase):
    """#1's core mechanism: nothing revealed before the attempt, the truth
    returned only as the response to a recorded pick."""

    def test_student_view_never_leaks_the_answer(self):
        view = homework_rules.student_mcq_view(VALID_MCQ)
        self.assertEqual(
            set(view.keys()), {"question", "options"},
            "pre-attempt view must carry question + options ONLY",
        )
        self.assertNotIn("correct_index", view)
        self.assertNotIn("explanation", view)

    def test_student_view_copies_options(self):
        view = homework_rules.student_mcq_view(VALID_MCQ)
        view["options"].append("mutated")
        self.assertEqual(len(VALID_MCQ["options"]), 4)

    def test_correct_pick_confirmed(self):
        reveal = homework_rules.check_answer(VALID_MCQ, 0)
        self.assertTrue(reveal["correct"])
        self.assertEqual(reveal["correct_index"], 0)
        self.assertEqual(reveal["correct_option"], "x = 4")
        self.assertEqual(reveal["explanation"], VALID_MCQ["explanation"])

    def test_wrong_pick_corrected_after_the_attempt(self):
        # "wrong, B is correct" — the correction names the right option.
        reveal = homework_rules.check_answer(VALID_MCQ, 1)
        self.assertFalse(reveal["correct"])
        self.assertEqual(reveal["selected_index"], 1)
        self.assertEqual(reveal["correct_index"], 0)
        self.assertEqual(reveal["correct_option"], "x = 4")

    def test_out_of_range_or_non_int_pick_rejected(self):
        for bad in (-1, 4, "0", True, None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                homework_rules.check_answer(VALID_MCQ, bad)

    def test_missing_explanation_reveals_empty_string(self):
        mcq = {k: v for k, v in VALID_MCQ.items() if k != "explanation"}
        self.assertEqual(homework_rules.check_answer(mcq, 0)["explanation"], "")


class TestEssayDecline(unittest.TestCase):
    """#1's scope boundary: essay/written-argument questions are declined
    with a reason the student sees, never force-fitted into an MCQ."""

    def test_reason_required(self):
        for bad in (None, "", "   "):
            with self.assertRaises(ValueError):
                homework_rules.validate_decline(bad)

    def test_reason_normalized(self):
        self.assertEqual(
            homework_rules.validate_decline(
                "  This is an essay question — it needs your own argument, "
                "which multiple choice can't check.  "
            ),
            "This is an essay question — it needs your own argument, "
            "which multiple choice can't check.",
        )


if __name__ == "__main__":
    unittest.main()
