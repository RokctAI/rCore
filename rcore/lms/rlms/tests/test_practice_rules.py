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

"""Product log #42 item 2's adaptive practice-queue selection, pinned
standalone.

Loaded by file path rather than package import, matching
test_maths_track.py (workspace modules import through an `rcore`
placeholder; practice_rules.py is deliberately frappe-free)."""

import importlib.util
import os
import unittest

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "practice_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_practice_rules", _MODULE_PATH)
practice_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(practice_rules)

CORRECT = practice_rules.CORRECT
INCORRECT = practice_rules.INCORRECT
SKIPPED = practice_rules.SKIPPED


def _bank(spec):
    """{item_id: subtopic_ref} -> the build_queue items shape."""
    return {item_id: {"subtopic_ref": subtopic} for item_id, subtopic in spec.items()}


class TestClampLimit(unittest.TestCase):
    def test_default_when_absent_or_junk(self):
        self.assertEqual(
            practice_rules.clamp_limit(None), practice_rules.DEFAULT_QUEUE_LENGTH
        )
        self.assertEqual(
            practice_rules.clamp_limit("junk"), practice_rules.DEFAULT_QUEUE_LENGTH
        )

    def test_server_cap_cannot_be_widened(self):
        # The client asking for 1000 items still gets the server's cap —
        # composition is server-owned.
        self.assertEqual(
            practice_rules.clamp_limit(1000), practice_rules.MAX_QUEUE_LENGTH
        )
        self.assertEqual(practice_rules.clamp_limit(0), 1)
        self.assertEqual(practice_rules.clamp_limit(-5), 1)

    def test_string_numbers_accepted(self):
        # Frappe delivers query params as strings.
        self.assertEqual(practice_rules.clamp_limit("5"), 5)


class TestSubtopicNeeds(unittest.TestCase):
    def test_outcome_ordering(self):
        # A wrong answer signals more need than a skip; a correct one, none.
        needs = practice_rules.subtopic_needs(
            [("a", INCORRECT), ("b", SKIPPED), ("c", CORRECT)]
        )
        self.assertEqual(needs["a"], 1.0)
        self.assertEqual(needs["b"], 0.75)
        self.assertEqual(needs["c"], 0.0)
        self.assertGreater(needs["a"], needs["b"])

    def test_recent_outcomes_dominate(self):
        # Same mix, opposite order: the subtopic whose RECENT answers are
        # wrong must look needier — the mastery loop runs on recency.
        improving = practice_rules.subtopic_needs(
            [("s", INCORRECT), ("s", INCORRECT), ("s", CORRECT), ("s", CORRECT)]
        )["s"]
        regressing = practice_rules.subtopic_needs(
            [("s", CORRECT), ("s", CORRECT), ("s", INCORRECT), ("s", INCORRECT)]
        )["s"]
        self.assertLess(improving, regressing)

    def test_recovery_drops_below_mastery_threshold(self):
        # One old miss followed by a run of correct answers: the decayed
        # need must fall under the mastery cutoff, so the subtopic leaves
        # the queue on its own.
        history = [("s", INCORRECT)] + [("s", CORRECT)] * 8
        need = practice_rules.subtopic_needs(history)["s"]
        self.assertLess(need, practice_rules.MASTERY_THRESHOLD)

    def test_dict_rows_and_junk_ignored(self):
        needs = practice_rules.subtopic_needs(
            [
                {"subtopic_ref": "s", "outcome": INCORRECT},
                {"subtopic_ref": None, "outcome": INCORRECT},
                {"subtopic_ref": "s", "outcome": "Bogus"},
            ]
        )
        self.assertEqual(needs, {"s": 1.0})


class TestRankItems(unittest.TestCase):
    def test_unseen_beats_just_practiced(self):
        history = [{"item_id": "seen", "outcome": CORRECT}]
        ranked = practice_rules.rank_items(["seen", "new"], history, seed="x")
        self.assertEqual(ranked[0], "new")

    def test_just_correct_sinks_below_just_missed(self):
        history = [
            {"item_id": "missed", "outcome": INCORRECT},
            {"item_id": "aced", "outcome": CORRECT},
        ]
        ranked = practice_rules.rank_items(["aced", "missed"], history, seed="x")
        self.assertLess(ranked.index("missed"), ranked.index("aced"))

    def test_old_miss_resurfaces_above_unseen(self):
        # Spaced retry: a miss from a while back (many attempts since)
        # outranks brand-new material — its retry bonus survives while the
        # seen-penalty has decayed away.
        history = [{"item_id": "old_miss", "outcome": INCORRECT}] + [
            {"item_id": f"filler{i}", "outcome": CORRECT} for i in range(10)
        ]
        ranked = practice_rules.rank_items(["old_miss", "new"], history, seed="x")
        self.assertEqual(ranked[0], "old_miss")

    def test_deterministic_for_a_seed_and_rotating_across_seeds(self):
        items = [f"i{n}" for n in range(12)]
        a = practice_rules.rank_items(items, [], seed="member:2026-08-13")
        b = practice_rules.rank_items(items, [], seed="member:2026-08-13")
        c = practice_rules.rank_items(items, [], seed="member:2026-08-14")
        self.assertEqual(a, b)  # stable within the day — no client randomness
        self.assertNotEqual(a, c)  # rotates when the seed does


class TestAllocateSlots(unittest.TestCase):
    def test_proportional_to_need(self):
        slots = practice_rules.allocate_slots(
            {"weak": 3.0, "ok": 1.0}, {"weak": 10, "ok": 10}, 8
        )
        self.assertEqual(slots, {"weak": 6, "ok": 2})

    def test_capacity_caps_and_overflow_redistributes(self):
        # The needy subtopic only has 2 items; its excess quota must flow
        # to the other, not vanish.
        slots = practice_rules.allocate_slots(
            {"weak": 3.0, "ok": 1.0}, {"weak": 2, "ok": 10}, 8
        )
        self.assertEqual(slots, {"weak": 2, "ok": 6})

    def test_never_exceeds_total_capacity(self):
        slots = practice_rules.allocate_slots({"a": 1.0}, {"a": 3}, 10)
        self.assertEqual(slots, {"a": 3})

    def test_zero_weight_gets_nothing(self):
        slots = practice_rules.allocate_slots({"a": 1.0, "b": 0.0}, {"a": 5, "b": 5}, 4)
        self.assertEqual(slots, {"a": 4})


class TestBuildQueue(unittest.TestCase):
    def test_empty_bank_answers_empty(self):
        self.assertEqual(practice_rules.build_queue({}, [], [], seed="x"), [])

    def test_weighted_toward_incorrect_and_skipped_subtopics(self):
        # The decision-#42 core: the queue leans into subtopics the student
        # missed or skipped, not the ones they aced.
        items = _bank(
            {f"weak{i}": "fractions" for i in range(10)}
            | {f"strong{i}": "algebra" for i in range(10)}
        )
        history = (
            [("fractions", INCORRECT)] * 3
            + [("fractions", SKIPPED)] * 2
            + [("algebra", CORRECT)] * 2
            + [("algebra", INCORRECT)]  # one recent wobble keeps algebra active
        )
        queue = practice_rules.build_queue(items, history, [], limit=10, seed="x")
        weak = sum(1 for item_id in queue if item_id.startswith("weak"))
        strong = len(queue) - weak
        self.assertEqual(len(queue), 10)
        self.assertGreater(weak, strong)

    def test_mastered_subtopic_dropped_when_enough_material(self):
        items = _bank(
            {f"w{i}": "weak_topic" for i in range(10)}
            | {f"m{i}": "mastered_topic" for i in range(10)}
        )
        history = [("weak_topic", INCORRECT)] * 4 + [("mastered_topic", CORRECT)] * 8
        queue = practice_rules.build_queue(items, history, [], limit=8, seed="x")
        self.assertEqual(len(queue), 8)
        self.assertTrue(all(item_id.startswith("w") for item_id in queue))

    def test_mastered_material_backfills_an_underfull_queue(self):
        # Only 2 non-mastered items exist; the queue must still fill from
        # mastered material rather than starve a strong student.
        items = _bank(
            {"w1": "weak_topic", "w2": "weak_topic"}
            | {f"m{i}": "mastered_topic" for i in range(8)}
        )
        history = [("weak_topic", INCORRECT)] + [("mastered_topic", CORRECT)] * 8
        queue = practice_rules.build_queue(items, history, [], limit=6, seed="x")
        self.assertEqual(len(queue), 6)
        self.assertIn("w1", queue)
        self.assertTrue(any(item_id.startswith("m") for item_id in queue))

    def test_no_history_still_serves_a_full_exploratory_queue(self):
        # Brand-new student: baseline need everywhere, full queue, spread
        # across subtopics.
        items = _bank({f"a{i}": "st_a" for i in range(5)} | {f"b{i}": "st_b" for i in range(5)})
        queue = practice_rules.build_queue(items, [], [], limit=6, seed="x")
        self.assertEqual(len(queue), 6)
        self.assertTrue(any(item_id.startswith("a") for item_id in queue))
        self.assertTrue(any(item_id.startswith("b") for item_id in queue))

    def test_interleaves_subtopics(self):
        # Consecutive items should vary subtopic while both pools last —
        # the cheap spacing effect.
        items = _bank({f"a{i}": "st_a" for i in range(3)} | {f"b{i}": "st_b" for i in range(3)})
        history = [("st_a", INCORRECT), ("st_b", INCORRECT)]
        queue = practice_rules.build_queue(items, history, [], limit=6, seed="x")
        subtopics = ["st_a" if item_id.startswith("a") else "st_b" for item_id in queue]
        self.assertEqual(len(queue), 6)
        for first, second in zip(subtopics, subtopics[1:]):
            self.assertNotEqual(first, second)

    def test_items_without_subtopic_still_eligible(self):
        items = {"loose1": {}, "loose2": {"subtopic_ref": None}}
        queue = practice_rules.build_queue(items, [], [], limit=5, seed="x")
        self.assertEqual(sorted(queue), ["loose1", "loose2"])

    def test_practice_attempts_close_the_loop(self):
        # A subtopic drilled to correctness THROUGH PRACTICE leaves the
        # queue: practice attempts feed the same need computation as lesson
        # quiz results (the caller merges them chronologically).
        items = _bank(
            {f"d{i}": "drilled" for i in range(5)} | {f"u{i}": "untouched_weak" for i in range(5)}
        )
        quiz = [("drilled", INCORRECT), ("untouched_weak", INCORRECT)]
        practice = [
            {"item_id": f"d{i}", "subtopic_ref": "drilled", "outcome": CORRECT}
            for i in range(5)
        ]
        merged = list(quiz) + list(practice)
        queue = practice_rules.build_queue(items, merged, practice, limit=5, seed="x")
        self.assertEqual(len(queue), 5)
        self.assertTrue(all(item_id.startswith("u") for item_id in queue))

    def test_queue_is_deterministic_per_seed(self):
        items = _bank({f"i{n}": f"st{n % 3}" for n in range(15)})
        history = [("st0", INCORRECT), ("st1", SKIPPED)]
        a = practice_rules.build_queue(items, history, [], limit=10, seed="m:d1")
        b = practice_rules.build_queue(items, history, [], limit=10, seed="m:d1")
        self.assertEqual(a, b)

    def test_limit_respected(self):
        items = _bank({f"i{n}": "st" for n in range(30)})
        queue = practice_rules.build_queue(
            items, [("st", INCORRECT)], [], limit=99, seed="x"
        )
        self.assertLessEqual(len(queue), practice_rules.MAX_QUEUE_LENGTH)


if __name__ == "__main__":
    unittest.main()
