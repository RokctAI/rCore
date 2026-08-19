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

"""Pure weekly-league rules (decision #42 gap 4 — weekly leagues).

Deliberately frappe-free: `api/engagement.py` does the querying and the
persisting, this module does the DECIDING — point weights, ranking,
cohorting, and week-end promotion/demotion. The server is the sole
authority on points and rank; apps only read the answers.

The shape is the familiar weekly-league one: every student sits in a
cohort of up to [COHORT_SIZE] peers within a tier, earns engagement
points through the week, and at week close the top [PROMOTE_TOP] move up
a tier while the bottom [DEMOTE_BOTTOM] move down. No energy-gating —
demotion is the only downside, and it only ever costs bragging rights.

Point weights (documented defaults, decision #42):
- attended live session: 10
- quiz question completed (answered, right or wrong): 5
- lesson completed: 5
Attendance dominates by design — showing up to the live broadcast is the
behaviour the product most wants to reward.
"""

from datetime import timedelta

ATTENDANCE_POINTS = 10
QUIZ_POINTS = 5
LESSON_POINTS = 5

#: Tier ladder, lowest first. New students start in [TIERS[0]].
TIERS = ["Bronze", "Silver", "Gold", "Sapphire", "Diamond"]

#: Maximum students per cohort within a tier.
COHORT_SIZE = 30

#: Ranks 1..PROMOTE_TOP move up a tier at week close (unless already top).
PROMOTE_TOP = 10

#: The bottom DEMOTE_BOTTOM ranks move down (unless already bottom tier).
DEMOTE_BOTTOM = 5

PROMOTED = "promoted"
DEMOTED = "demoted"
STAYED = "stayed"


def weekly_points(attended=0, quizzes_completed=0, lessons_completed=0):
    """A student's engagement points for one week from their event counts."""
    return (
        attended * ATTENDANCE_POINTS
        + quizzes_completed * QUIZ_POINTS
        + lessons_completed * LESSON_POINTS
    )


def rank_standings(points_by_student):
    """Rank a cohort. [points_by_student] maps student id -> points.

    Returns a list of `{"student", "points", "rank"}` dicts, highest points
    first. Ties share a rank (competition ranking: 1, 1, 3, ...), broken
    for display order only by student id so the listing is stable.
    """
    ordered = sorted(points_by_student.items(), key=lambda kv: (-kv[1], kv[0]))
    standings = []
    rank = 0
    previous_points = None
    for position, (student, points) in enumerate(ordered, start=1):
        if points != previous_points:
            rank = position
            previous_points = points
        standings.append({"student": student, "points": points, "rank": rank})
    return standings


def assign_cohorts(student_ids, cohort_size=COHORT_SIZE):
    """Chunk a tier's students into cohorts of at most [cohort_size].

    Input order is preserved (callers pass a deterministic order); returns
    a list of lists. An empty input yields no cohorts.
    """
    if cohort_size < 1:
        raise ValueError("cohort_size must be >= 1")
    return [
        student_ids[i : i + cohort_size]
        for i in range(0, len(student_ids), cohort_size)
    ]


def movement_for_rank(rank, cohort_count):
    """What happens to one rank at week close, before tier clamping.

    Promotion outranks demotion when a cohort is so small the zones would
    overlap: a rank inside the top-[PROMOTE_TOP] promotes even if it is
    also inside the bottom-[DEMOTE_BOTTOM].
    """
    if rank <= PROMOTE_TOP:
        return PROMOTED
    if rank > cohort_count - DEMOTE_BOTTOM:
        return DEMOTED
    return STAYED


def next_tier(tier, movement):
    """The tier a student lands in after applying [movement], clamped to
    the ladder — Diamond cannot promote further, Bronze cannot demote."""
    index = TIERS.index(tier)
    if movement == PROMOTED:
        index = min(index + 1, len(TIERS) - 1)
    elif movement == DEMOTED:
        index = max(index - 1, 0)
    return TIERS[index]


def close_cohort(standings, tier):
    """Week-close outcomes for one ranked cohort.

    [standings] is rank_standings() output; returns a list of
    `{"student", "points", "rank", "movement", "next_tier"}` dicts.
    """
    count = len(standings)
    outcomes = []
    for row in standings:
        movement = movement_for_rank(row["rank"], count)
        landed = next_tier(tier, movement)
        if landed == tier:
            movement = STAYED
        outcomes.append(
            {
                "student": row["student"],
                "points": row["points"],
                "rank": row["rank"],
                "movement": movement,
                "next_tier": landed,
            }
        )
    return outcomes


def week_start_of(day):
    """The Monday of [day]'s week — league weeks run Monday..Sunday.
    Accepts a date or datetime; answers the same type minus the offset."""
    return day - timedelta(days=day.weekday())


def display_name(full_name, fallback="Student"):
    """Leaderboard privacy: first name plus last initial ("Thabo M."),
    never the full surname. A single-word name stands as-is; an empty name
    answers [fallback]."""
    parts = [p for p in (full_name or "").split() if p]
    if not parts:
        return fallback
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0].upper()}."
