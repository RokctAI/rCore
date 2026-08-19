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

"""Weekly partner email digest — the calendar maths and the wording rules.

Loaded by file path rather than package import, matching
test_alert_rules.py (workspace modules import through an `rcore`
placeholder; digest_rules.py is deliberately frappe-free).

The wording tests pin the house style: plain language, no outcome enums,
no internal identifiers — the email a partner reads must never leak a
field name or a session id."""

import importlib.util
import os
import unittest
from datetime import date

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "digest_rules.py")
_spec = importlib.util.spec_from_file_location("rlms_digest_rules", _MODULE_PATH)
digest_rules = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(digest_rules)


def _report(**overrides):
    """A weekly_report payload with a quiet-but-typical week's defaults."""
    report = {
        "student_name": "Thandi Mokoena",
        "week_start": "2026-08-10T00:00:00",
        "sessions_scheduled": 5,
        "sessions_attended": 4,
        "sessions_skipped_answered": 1,
        "sessions_skipped_unanswered": 0,
        "performance_scores": {"Fractions": 80, "Algebra Basics": 60},
        "engagement_rate_percent": 90,
        "data_used_mb": 152.4,
        "current_streak": 3,
    }
    report.update(overrides)
    return report


class TestReportWeekStart(unittest.TestCase):
    """The digest cron fires Sunday evening; the run reports the week that
    began the previous Monday — the Monday of the run date's own week."""

    def test_sunday_run_reports_the_week_that_just_ended(self):
        # Sunday 2026-08-16 closes out the week that began Monday the 10th.
        self.assertEqual(
            digest_rules.report_week_start(date(2026, 8, 16)), date(2026, 8, 10)
        )

    def test_monday_is_its_own_week_start(self):
        self.assertEqual(
            digest_rules.report_week_start(date(2026, 8, 10)), date(2026, 8, 10)
        )

    def test_midweek_run_still_anchors_to_monday(self):
        self.assertEqual(
            digest_rules.report_week_start(date(2026, 8, 13)), date(2026, 8, 10)
        )


class TestDigestWording(unittest.TestCase):
    def test_subject_names_the_student(self):
        digest = digest_rules.render_digest(_report())
        self.assertEqual(digest["subject"], "Thandi Mokoena's week on Supacharge")

    def test_greets_the_partner_by_name_when_known(self):
        digest = digest_rules.render_digest(_report(), partner_name="Naledi")
        self.assertTrue(digest["body"].startswith("Hi Naledi,"))

    def test_greets_plainly_when_no_name(self):
        digest = digest_rules.render_digest(_report())
        self.assertTrue(digest["body"].startswith("Hi,"))

    def test_attendance_line_reads_in_plain_language(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertIn(
            "Thandi Mokoena attended 4 of the 5 live sessions scheduled this week.",
            body,
        )

    def test_perfect_week_gets_a_cheer(self):
        body = digest_rules.render_digest(
            _report(
                sessions_attended=5,
                sessions_skipped_answered=0,
                sessions_skipped_unanswered=0,
            )
        )["body"]
        self.assertIn("every single one", body)

    def test_empty_week_is_stated_not_zeroed(self):
        # A week with nothing scheduled must read as "nothing was scheduled",
        # never as "attended 0 of 0".
        body = digest_rules.render_digest(
            _report(
                sessions_scheduled=0,
                sessions_attended=0,
                sessions_skipped_answered=0,
                sessions_skipped_unanswered=0,
            )
        )["body"]
        self.assertIn("No live sessions were scheduled this week", body)
        self.assertNotIn("0 of", body)

    def test_answered_skips_read_as_check_ins(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertIn("answered the quick check-in", body)

    def test_mixed_skips_split_answered_from_silent(self):
        body = digest_rules.render_digest(
            _report(
                sessions_attended=2,
                sessions_skipped_answered=2,
                sessions_skipped_unanswered=1,
            )
        )["body"]
        self.assertIn("3 sessions were missed", body)
        self.assertIn("for 2 of them", body)
        self.assertIn("1 went by without a word", body)

    def test_silent_skips_nudge_a_conversation(self):
        body = digest_rules.render_digest(
            _report(sessions_skipped_answered=0, sessions_skipped_unanswered=2)
        )["body"]
        self.assertIn("without answering the quick check-in", body)
        self.assertIn("worth asking", body)

    def test_streak_is_celebrated(self):
        body = digest_rules.render_digest(_report(current_streak=7))["body"]
        self.assertIn("7 sessions attended in a row", body)

    def test_single_session_streak_is_singular(self):
        body = digest_rules.render_digest(_report(current_streak=1))["body"]
        self.assertIn("1 session attended in a row", body)

    def test_zero_streak_stays_silent(self):
        body = digest_rules.render_digest(_report(current_streak=0))["body"]
        self.assertNotIn("in a row", body)

    def test_quiz_scores_list_each_lesson(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertIn("- Algebra Basics: 60%", body)
        self.assertIn("- Fractions: 80%", body)
        self.assertIn("answered 90% of the quiz questions", body)

    def test_no_quiz_week_omits_the_quiz_section(self):
        body = digest_rules.render_digest(
            _report(performance_scores={}, engagement_rate_percent=0)
        )["body"]
        self.assertNotIn("quiz", body.lower())

    def test_data_usage_is_rounded_and_monthly(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertIn("Data used this month: about 152 MB.", body)

    def test_zero_data_usage_stays_silent(self):
        body = digest_rules.render_digest(_report(data_used_mb=0))["body"]
        self.assertNotIn("Data used", body)

    def test_footer_explains_the_opt_in_and_the_way_out(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertIn("because you switched it on", body)
        self.assertIn("turn it off", body)

    def test_no_jargon_or_internal_identifiers_leak(self):
        # The house style pin: outcome enums, field names, and raw payload
        # keys must never reach a partner's inbox.
        body = digest_rules.render_digest(_report())["body"]
        for term in (
            "Skipped Unanswered",
            "Skipped Answered",
            "session_id",
            "week_start",
            "engagement_rate_percent",
            "data_used_mb",
            "outcome",
        ):
            self.assertNotIn(term, body)


class TestPartnerDigest(unittest.TestCase):
    """One email per partner: a section per student, one greeting, one
    footer — and a single-student partner gets render_digest's email."""

    def _two_reports(self):
        return [
            _report(),
            _report(
                student_name="Sipho Dlamini",
                sessions_attended=5,
                sessions_skipped_answered=0,
                current_streak=0,
                performance_scores={"Geometry": 70},
                engagement_rate_percent=75,
                data_used_mb=0,
            ),
        ]

    def test_single_student_matches_render_digest(self):
        self.assertEqual(
            digest_rules.render_partner_digest([_report()], partner_name="Naledi"),
            digest_rules.render_digest(_report(), partner_name="Naledi"),
        )

    def test_multi_student_subject_covers_them_all(self):
        digest = digest_rules.render_partner_digest(self._two_reports())
        self.assertEqual(digest["subject"], "Your students' week on Supacharge")

    def test_each_student_gets_a_section(self):
        body = digest_rules.render_partner_digest(self._two_reports())["body"]
        self.assertIn("Here's how Thandi Mokoena's week on Supacharge went.", body)
        self.assertIn("Here's how Sipho Dlamini's week on Supacharge went.", body)

    def test_sections_read_in_student_name_order(self):
        body = digest_rules.render_partner_digest(self._two_reports())["body"]
        self.assertLess(body.index("Sipho Dlamini"), body.index("Thandi Mokoena"))

    def test_one_greeting_and_one_footer(self):
        body = digest_rules.render_partner_digest(
            self._two_reports(), partner_name="Naledi"
        )["body"]
        self.assertTrue(body.startswith("Hi Naledi,"))
        self.assertEqual(body.count("Hi Naledi,"), 1)
        self.assertEqual(body.count("because you switched it on"), 1)
        self.assertTrue(body.rstrip().endswith("anytime."))

    def test_each_section_keeps_its_own_numbers(self):
        body = digest_rules.render_partner_digest(self._two_reports())["body"]
        self.assertIn("Thandi Mokoena attended 4 of the 5 live sessions", body)
        self.assertIn("Sipho Dlamini attended 5 of the 5 live sessions", body)
        self.assertIn("- Geometry: 70%", body)

    def test_no_jargon_or_internal_identifiers_leak(self):
        body = digest_rules.render_partner_digest(self._two_reports())["body"]
        for term in (
            "Skipped Unanswered",
            "Skipped Answered",
            "session_id",
            "week_start",
            "engagement_rate_percent",
            "data_used_mb",
            "outcome",
        ):
            self.assertNotIn(term, body)


def _healthy_report(name):
    return _report(
        student_name=name,
        sessions_attended=5,
        sessions_skipped_answered=0,
        sessions_skipped_unanswered=0,
        current_streak=8,
        performance_scores={},
        engagement_rate_percent=0,
        data_used_mb=0,
    )


def _worry_report(name):
    return _report(
        student_name=name,
        sessions_attended=3,
        sessions_skipped_answered=0,
        sessions_skipped_unanswered=2,
        current_streak=0,
        performance_scores={},
        engagement_rate_percent=0,
        data_used_mb=0,
    )


def _roster(healthy=0, worry=0):
    return [_healthy_report(f"Healthy {i:03d}") for i in range(healthy)] + [
        _worry_report(f"Worry {i:03d}") for i in range(worry)
    ]


class TestPartnerDigestAtScale(unittest.TestCase):
    """Rosters past FULL_SECTIONS_MAX switch to one line per student —
    attention cases first, healthy students batched after, and at
    HEALTHY_ROLLUP_FROM the healthy group collapses to a count."""

    def test_thresholds_are_pinned(self):
        self.assertEqual(digest_rules.FULL_SECTIONS_MAX, 5)
        self.assertEqual(digest_rules.HEALTHY_ROLLUP_FROM, 100)
        self.assertEqual(digest_rules.PARTNER_REPORT_CAP, 200)

    def test_one_student_still_matches_render_digest(self):
        self.assertEqual(
            digest_rules.render_partner_digest([_report()], partner_name="Naledi"),
            digest_rules.render_digest(_report(), partner_name="Naledi"),
        )

    def test_five_students_keep_full_sections(self):
        body = digest_rules.render_partner_digest(_roster(healthy=3, worry=2))[
            "body"
        ]
        self.assertEqual(body.count("week on Supacharge went."), 5)
        self.assertNotIn("Worth a closer look", body)

    def test_six_students_switch_to_compact_lines(self):
        body = digest_rules.render_partner_digest(_roster(healthy=4, worry=2))[
            "body"
        ]
        self.assertNotIn("week on Supacharge went.", body)
        self.assertIn("Here's the week across your 6 students on Supacharge.", body)
        self.assertEqual(body.count("- Healthy"), 4)
        self.assertEqual(body.count("- Worry"), 2)

    def test_compact_puts_attention_students_first(self):
        body = digest_rules.render_partner_digest(_roster(healthy=4, worry=2))[
            "body"
        ]
        self.assertIn("Worth a closer look this week:", body)
        self.assertIn("Everyone else had a good week:", body)
        self.assertLess(
            body.index("Worth a closer look this week:"),
            body.index("Everyone else had a good week:"),
        )
        self.assertLess(body.index("Worry 000"), body.index("Healthy 000"))

    def test_compact_lines_carry_attendance_and_flags(self):
        body = digest_rules.render_partner_digest(_roster(healthy=4, worry=2))[
            "body"
        ]
        self.assertIn("- Worry 000: attended 3 of 5 — missed both check-ins", body)
        self.assertIn("- Healthy 000: attended 5 of 5 — 8 in a row", body)

    def test_fifty_students_list_every_healthy_line(self):
        body = digest_rules.render_partner_digest(_roster(healthy=47, worry=3))[
            "body"
        ]
        self.assertIn("Here's the week across your 50 students on Supacharge.", body)
        self.assertEqual(body.count("- Healthy"), 47)
        self.assertIn("Everyone else had a good week:", body)
        self.assertNotIn("nothing to worry about", body)

    def test_hundred_fifty_students_collapse_the_healthy_group(self):
        body = digest_rules.render_partner_digest(_roster(healthy=147, worry=3))[
            "body"
        ]
        self.assertIn(
            "Here's the week across your 150 students on Supacharge.", body
        )
        self.assertEqual(body.count("- Worry"), 3)
        self.assertNotIn("- Healthy", body)
        self.assertIn(
            "Another 147 students had a good week — nothing to worry about.", body
        )

    def test_all_healthy_large_roster_reads_all_clear(self):
        body = digest_rules.render_partner_digest(_roster(healthy=120))["body"]
        self.assertNotIn("Worth a closer look", body)
        self.assertIn(
            "All 120 students had a good week — nothing to worry about.", body
        )

    def test_capped_roster_names_the_overflow(self):
        body = digest_rules.render_partner_digest(
            _roster(healthy=180, worry=20), more_students=30
        )["body"]
        self.assertIn("Here's the week across your 230 students on Supacharge.", body)
        self.assertIn("and 30 more students — see the app for everyone.", body)

    def test_uncapped_roster_never_mentions_more_students(self):
        body = digest_rules.render_partner_digest(_roster(healthy=6))["body"]
        self.assertNotIn("see the app", body)

    def test_compact_keeps_one_greeting_and_one_footer(self):
        body = digest_rules.render_partner_digest(
            _roster(healthy=10, worry=2), partner_name="Naledi"
        )["body"]
        self.assertTrue(body.startswith("Hi Naledi,"))
        self.assertEqual(body.count("Hi Naledi,"), 1)
        self.assertEqual(body.count("because you switched it on"), 1)
        self.assertTrue(body.rstrip().endswith("anytime."))

    def test_compact_no_jargon_or_internal_identifiers_leak(self):
        body = digest_rules.render_partner_digest(_roster(healthy=147, worry=3))[
            "body"
        ]
        for term in (
            "Skipped Unanswered",
            "Skipped Answered",
            "session_id",
            "week_start",
            "engagement_rate_percent",
            "data_used_mb",
            "outcome",
        ):
            self.assertNotIn(term, body)


class TestLeagueLine(unittest.TestCase):
    """One friendly league sentence per student — only when the student
    actually holds a standing this week, and never leaking payload keys."""

    def _league(self, **overrides):
        league = {"tier": "Gold", "points": 45, "rank": 3, "cohort_size": 12}
        league.update(overrides)
        return league

    def test_league_line_names_tier_and_rank(self):
        body = digest_rules.render_digest(_report(league=self._league()))["body"]
        self.assertIn(
            "In this week's league, Thandi Mokoena is in the Gold tier — "
            "3rd of 12 in their group.",
            body,
        )

    def test_rank_reads_as_an_ordinal(self):
        body = digest_rules.render_digest(
            _report(league=self._league(rank=1))
        )["body"]
        self.assertIn("1st of 12", body)
        body = digest_rules.render_digest(
            _report(league=self._league(rank=2))
        )["body"]
        self.assertIn("2nd of 12", body)
        body = digest_rules.render_digest(
            _report(league=self._league(rank=11, cohort_size=30))
        )["body"]
        self.assertIn("11th of 30", body)

    def test_missing_rank_still_names_the_tier(self):
        body = digest_rules.render_digest(
            _report(league=self._league(rank=None))
        )["body"]
        self.assertIn(
            "In this week's league, Thandi Mokoena is in the Gold tier.", body
        )
        self.assertNotIn("of 12", body)

    def test_no_league_data_stays_silent(self):
        body = digest_rules.render_digest(_report())["body"]
        self.assertNotIn("league", body.lower())

    def test_league_payload_keys_never_leak(self):
        body = digest_rules.render_digest(_report(league=self._league()))["body"]
        for term in ("cohort_size", "cohort", "rank", "week_start", "points"):
            self.assertNotIn(term, body)

    def test_each_student_keeps_their_own_league_line(self):
        reports = [
            _report(league=self._league()),
            _report(
                student_name="Sipho Dlamini",
                league=self._league(tier="Silver", rank=8, cohort_size=20),
            ),
        ]
        body = digest_rules.render_partner_digest(reports)["body"]
        self.assertIn("Thandi Mokoena is in the Gold tier — 3rd of 12", body)
        self.assertIn("Sipho Dlamini is in the Silver tier — 8th of 20", body)


if __name__ == "__main__":
    unittest.main()
