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

"""Adaptive practice-queue selection (product log #42 item 2) — frappe-free
pure module.

The queue is the practice layer BETWEEN broadcasts: pre-authored MCQ items
(the same manifest-authored question stock the lesson player shows at
subtopic boundaries, published to the backend as `LMS Practice Item Bank`)
selected adaptively from the MCQ/skip data already collected per subtopic
(`LMS Lesson Quiz Result`) plus the member's own practice attempts
(`LMS Practice Attempt`). No runtime LLM calls anywhere — pre-authored
items + this selection IS the whole mechanism, so serving a queue costs a
database read. The broadcast schedule (product log #37) is untouched:
nothing here schedules, gates, or replaces a live session.

The SERVER is the sole authority on queue composition: every constant that
shapes the queue (outcome weights, recency decay, mastery threshold, queue
length bounds) lives in this module, never in the client. The client
renders the returned list in order — that is all it does.

Selection model:

1. **Subtopic need** — per subtopic, an exponentially-decayed average of
   outcome "need" scores over the member's merged history (lesson quiz
   results AND practice attempts, oldest-to-newest): Incorrect = 1.0,
   Skipped = 0.75 (avoidance is a real signal, but weaker than a confirmed
   wrong answer), Correct = 0.0. Newer observations dominate (decay 0.8
   per step back), so a subtopic the student has started getting right
   fades out of the queue on its own — the mastery loop.
2. **Baseline / exploration** — a subtopic with bank items but no history
   gets a fixed baseline need (0.25): unseen material surfaces without
   swamping genuinely weak areas.
3. **Mastery cutoff** — decayed need below 0.15 counts as mastered and is
   dropped, unless the queue would otherwise underfill (mastered material
   then backfills at a token weight, so a strong student still gets a
   full queue of review).
4. **Slot allocation** — queue slots split across surviving subtopics
   proportionally to need (largest-remainder via iterative max-deficit),
   capped by how many items each subtopic actually has; overflow
   redistributes deterministically.
5. **Item choice within a subtopic** — never-seen items carry no penalty;
   a previously-missed item earns a retry bonus but a decaying seen-penalty
   right after being shown (so misses resurface after spacing rather than
   immediately); a recently-CORRECT item takes the seen-penalty plus a
   cooldown. Ties break by a seeded hash — the API seeds per (member, day),
   so a queue is stable within the day, rotates daily, and needs no client
   randomness.
6. **Interleaving** — the final order round-robins across subtopics
   (neediest first) so consecutive items vary: the spacing effect, cheaply
   approximated.
"""

import hashlib

# Outcome labels — must match the Select options on LMS Lesson Quiz Result
# and LMS Practice Attempt exactly.
CORRECT = "Correct"
INCORRECT = "Incorrect"
SKIPPED = "Skipped"

# How much "need" one observation contributes (step 1). A skip is weaker
# than a wrong answer: skipping may be time pressure, wrong is confirmed.
NEED_SCORES = {INCORRECT: 1.0, SKIPPED: 0.75, CORRECT: 0.0}

# Per-step-back decay when averaging a subtopic's history (step 1) and when
# fading an item's seen-penalty (step 5). 0.8 ≈ the last five observations
# carry ~2/3 of the weight.
RECENCY_DECAY = 0.8

# Need assigned to a subtopic with items but no history at all (step 2).
BASELINE_NEED = 0.25

# Decayed need below this = mastered; excluded unless backfilling (step 3).
MASTERY_THRESHOLD = 0.15

# Token weight a mastered subtopic re-enters allocation with when the
# queue would underfill without it.
BACKFILL_FLOOR = 0.01

# Queue length bounds — server-owned; the client cannot widen them.
DEFAULT_QUEUE_LENGTH = 10
MAX_QUEUE_LENGTH = 20

# Item-level scoring (step 5), all relative to an unseen item's base 1.0.
ITEM_RETRY_BONUS = 0.5  # last attempt on this item was missed/skipped
ITEM_SEEN_PENALTY = 0.6  # just-shown penalty, decays per attempt since
ITEM_CORRECT_COOLDOWN = 0.4  # extra on top when the last attempt was correct

# Key under which bank items missing a subtopic_ref are grouped: they
# compete as one baseline-need pool rather than being dropped.
GENERAL_POOL = "__general__"


def clamp_limit(limit):
    """Server-side clamp of a requested queue length: non-numeric/absent
    falls back to the default; the cap can never be exceeded."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_QUEUE_LENGTH
    return max(1, min(n, MAX_QUEUE_LENGTH))


def _row(entry):
    """(subtopic_ref, outcome) from a dict row or a 2-tuple."""
    if isinstance(entry, dict):
        return entry.get("subtopic_ref"), entry.get("outcome")
    subtopic_ref, outcome = entry
    return subtopic_ref, outcome


def subtopic_needs(history):
    """Decayed need per subtopic (step 1).

    [history]: outcome rows ordered oldest→newest — dicts with
    `subtopic_ref`/`outcome` keys, or (subtopic_ref, outcome) tuples. Rows
    without a subtopic or with an unknown outcome are ignored.
    Returns {subtopic_ref: need in [0, 1]}.
    """
    per_subtopic = {}
    for entry in history:
        subtopic_ref, outcome = _row(entry)
        if not subtopic_ref or outcome not in NEED_SCORES:
            continue
        per_subtopic.setdefault(subtopic_ref, []).append(NEED_SCORES[outcome])

    needs = {}
    for subtopic_ref, scores in per_subtopic.items():
        numerator = denominator = 0.0
        for steps_back, score in enumerate(reversed(scores)):
            weight = RECENCY_DECAY**steps_back
            numerator += weight * score
            denominator += weight
        needs[subtopic_ref] = numerator / denominator if denominator else 0.0
    return needs


def _tie_break(seed, key):
    """Deterministic pseudo-random tiebreak: stable for a given seed, no
    client randomness, rotates with the seed (the API seeds per member+day)."""
    return hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()


def rank_items(item_ids, practice_history, seed):
    """Item order within one subtopic, best first (step 5).

    [practice_history]: the member's practice attempts (ALL subtopics),
    ordered oldest→newest, dicts with `item_id`/`outcome`. Position in this
    list is the recency measure: the seen-penalty decays per attempt made
    since the item was last shown, so "recently" means recent in practice
    activity, not wall-clock — a student returning after a month isn't
    blocked from their own material.
    """
    last_outcome = {}
    last_position = {}
    for position, row in enumerate(practice_history):
        item_id = row.get("item_id") if isinstance(row, dict) else None
        if not item_id:
            continue
        last_outcome[item_id] = row.get("outcome")
        last_position[item_id] = position

    total = len(practice_history)
    scored = []
    for item_id in item_ids:
        score = 1.0
        if item_id in last_position:
            attempts_since = (total - 1) - last_position[item_id]
            freshness = RECENCY_DECAY**attempts_since
            score -= ITEM_SEEN_PENALTY * freshness
            if last_outcome.get(item_id) == CORRECT:
                score -= ITEM_CORRECT_COOLDOWN * freshness
            else:
                # Missed or skipped last time: worth retrying — but the
                # seen-penalty above spaces the retry out instead of
                # re-asking immediately.
                score += ITEM_RETRY_BONUS
        scored.append((item_id, score))

    scored.sort(key=lambda pair: (-pair[1], _tie_break(seed, pair[0])))
    return [item_id for item_id, _ in scored]


def allocate_slots(weights, capacities, limit):
    """[limit] slots split across keys proportionally to [weights], capped
    by [capacities] (step 4). Iterative max-deficit assignment — equivalent
    to largest-remainder while handling caps and overflow redistribution in
    one deterministic loop. Returns {key: slots > 0}."""
    keys = [k for k in weights if weights.get(k, 0) > 0 and capacities.get(k, 0) > 0]
    if not keys or limit <= 0:
        return {}
    limit = min(limit, sum(capacities[k] for k in keys))
    total_weight = sum(weights[k] for k in keys)
    quotas = {k: limit * weights[k] / total_weight for k in keys}

    slots = {k: 0 for k in keys}
    for _ in range(limit):
        open_keys = [k for k in keys if slots[k] < capacities[k]]
        if not open_keys:
            break
        open_keys.sort(key=lambda k: (-(quotas[k] - slots[k]), -weights[k], k))
        slots[open_keys[0]] += 1
    return {k: count for k, count in slots.items() if count > 0}


def build_queue(items, history, practice_history, limit=None, seed=""):
    """The member's practice queue: ordered item ids (steps 1-6).

    [items]: {item_id: item dict} — already scope-filtered (subject/grade/
    lesson) by the caller; only `subtopic_ref` is read here.
    [history]: merged lesson-quiz + practice outcome rows, oldest→newest.
    [practice_history]: practice attempts only, oldest→newest.
    """
    limit = clamp_limit(limit)

    by_subtopic = {}
    for item_id, item in items.items():
        subtopic_ref = (item or {}).get("subtopic_ref") or GENERAL_POOL
        by_subtopic.setdefault(subtopic_ref, []).append(item_id)
    if not by_subtopic:
        return []

    needs = subtopic_needs(history)
    weights = {
        subtopic_ref: needs.get(subtopic_ref, BASELINE_NEED)
        for subtopic_ref in by_subtopic
    }

    # Mastery cutoff, with underfill backfill (step 3).
    active = {st: w for st, w in weights.items() if w >= MASTERY_THRESHOLD}
    mastered = {st: w for st, w in weights.items() if w < MASTERY_THRESHOLD}
    active_capacity = sum(len(by_subtopic[st]) for st in active)
    if active_capacity < limit and mastered:
        for subtopic_ref, weight in mastered.items():
            active[subtopic_ref] = max(weight, BACKFILL_FLOOR)

    capacities = {st: len(by_subtopic[st]) for st in active}
    slots = allocate_slots(active, capacities, limit)

    picked = {
        subtopic_ref: rank_items(by_subtopic[subtopic_ref], practice_history, seed)[:count]
        for subtopic_ref, count in slots.items()
    }

    # Interleave round-robin, neediest subtopic first (step 6).
    order = sorted(slots.keys(), key=lambda st: (-active[st], st))
    queue = []
    longest = max((len(chosen) for chosen in picked.values()), default=0)
    for position in range(longest):
        for subtopic_ref in order:
            chosen = picked.get(subtopic_ref, [])
            if position < len(chosen):
                queue.append(chosen[position])
    return queue[:limit]
