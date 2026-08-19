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

"""Product log #25's server-side time rules, pinned standalone (no frappe,
no site — `python -m unittest tests.test_time_gates`).

Loaded by file path rather than package import, matching
test_alert_rules.py: workspace python modules import through an `rcore`
placeholder and only resolve inside a composed app; time_gates.py is
deliberately frappe-free so this test runs anywhere python does."""

import importlib.util
import os
import unittest
from datetime import datetime, timedelta

_MODULE_PATH = os.path.join(os.path.dirname(__file__), "..", "time_gates.py")
_spec = importlib.util.spec_from_file_location("rlms_time_gates", _MODULE_PATH)
time_gates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(time_gates)


class TestRecordingUnlock(unittest.TestCase):
    # A 10:00 broadcast on the 15th unlocks at midnight into the 16th —
    # "the following day", same rule the client's LibraryEntry uses.
    broadcast = datetime(2026, 7, 15, 10, 0)

    def test_locked_during_and_after_broadcast_same_day(self):
        self.assertFalse(
            time_gates.recording_unlocked(self.broadcast, datetime(2026, 7, 15, 10, 30))
        )
        self.assertFalse(
            time_gates.recording_unlocked(self.broadcast, datetime(2026, 7, 15, 23, 59))
        )

    def test_unlocks_exactly_at_midnight_next_day(self):
        self.assertTrue(
            time_gates.recording_unlocked(self.broadcast, datetime(2026, 7, 16, 0, 0))
        )

    def test_late_evening_broadcast_still_unlocks_next_midnight(self):
        evening = datetime(2026, 7, 15, 23, 30)
        self.assertEqual(
            time_gates.recording_unlock_at(evening), datetime(2026, 7, 16, 0, 0)
        )


class TestAttendanceClaim(unittest.TestCase):
    scheduled = datetime(2026, 7, 15, 10, 0)

    def test_future_session_claim_is_forged(self):
        # "I attended tomorrow's session" — the spoof record_attendance_event
        # previously accepted, poisoning streaks and partner alerts.
        self.assertFalse(
            time_gates.attendance_claim_permitted(
                self.scheduled, datetime(2026, 7, 14, 10, 0)
            )
        )

    def test_claim_during_session_is_fine(self):
        self.assertTrue(
            time_gates.attendance_claim_permitted(
                self.scheduled, datetime(2026, 7, 15, 10, 20)
            )
        )

    def test_small_skew_before_start_is_tolerated(self):
        # Server-to-server skew pad, not device tolerance.
        self.assertTrue(
            time_gates.attendance_claim_permitted(
                self.scheduled, self.scheduled - timedelta(minutes=4)
            )
        )

    def test_offline_late_sync_within_window_is_fine(self):
        self.assertTrue(
            time_gates.attendance_claim_permitted(
                self.scheduled, self.scheduled + timedelta(days=13)
            )
        )

    def test_backdated_claim_beyond_window_is_refused(self):
        self.assertFalse(
            time_gates.attendance_claim_permitted(
                self.scheduled, self.scheduled + timedelta(days=15)
            )
        )


class TestPastBroadcast(unittest.TestCase):
    def test_future_session_is_a_predownload_not_a_recording(self):
        s = datetime(2026, 7, 20, 10, 0)
        self.assertFalse(time_gates.is_past_broadcast(s, datetime(2026, 7, 19, 10, 0)))
        self.assertTrue(time_gates.is_past_broadcast(s, datetime(2026, 7, 20, 10, 0)))


class TestLiveWindowVsRecording(unittest.TestCase):
    """Regression: `is_past_broadcast` is true from the FIRST SECOND of a
    broadcast, so using it alone to mean "this is a recording request" made
    the next-day unlock fire during the live lesson — locking every student
    out of every live session until midnight. The serving gate must use
    [is_recording_request] instead."""

    start = datetime(2026, 7, 15, 10, 0)

    def _recording_locked(self, now):
        """What the serving gate concludes: a recording request whose
        unlock has not passed."""
        return time_gates.is_recording_request(
            self.start, now
        ) and not time_gates.recording_unlocked(self.start, now)

    def test_joining_at_the_bell_is_not_locked(self):
        self.assertFalse(self._recording_locked(self.start))

    def test_opening_window_join_is_not_locked(self):
        # #35: "nobody is locked out in the first five minutes".
        self.assertFalse(self._recording_locked(self.start + timedelta(minutes=3)))

    def test_mid_session_join_is_not_locked(self):
        self.assertFalse(self._recording_locked(self.start + timedelta(minutes=45)))

    def test_after_the_live_window_it_is_a_recording_and_locks_until_unlock(self):
        # Same evening, session long over: the recording genuinely is not
        # out yet (it unlocks the following day).
        self.assertTrue(self._recording_locked(datetime(2026, 7, 15, 20, 0)))

    def test_next_day_the_recording_serves(self):
        self.assertFalse(self._recording_locked(datetime(2026, 7, 16, 9, 0)))

    def test_live_window_classification(self):
        self.assertTrue(time_gates.is_live_window(self.start, self.start))
        self.assertTrue(
            time_gates.is_live_window(self.start, self.start + timedelta(minutes=59))
        )
        self.assertFalse(
            time_gates.is_live_window(self.start, self.start - timedelta(minutes=1))
        )
        self.assertFalse(
            time_gates.is_live_window(self.start, datetime(2026, 7, 15, 20, 0))
        )


class TestRealDuration(unittest.TestCase):
    """Replay Session's real `duration_seconds` field (#40: live duration is
    derivable — recording length + the assistant's opening five minutes)
    replaces the 3-hour approximation when set; unset keeps the generous
    fallback so no pre-field row can lock a student out early."""

    start = datetime(2026, 7, 15, 10, 0)

    def test_real_duration_ends_the_live_window(self):
        # A 60-minute session: live until 11:00, a recording request after.
        duration = 3600
        self.assertTrue(
            time_gates.is_live_window(
                self.start, self.start + timedelta(minutes=59), duration
            )
        )
        self.assertFalse(
            time_gates.is_live_window(
                self.start, self.start + timedelta(minutes=60), duration
            )
        )
        self.assertTrue(
            time_gates.is_recording_request(
                self.start, self.start + timedelta(minutes=60), duration
            )
        )
        # Under the old 3-hour bound this moment was still "live".
        self.assertFalse(
            time_gates.is_recording_request(
                self.start, self.start + timedelta(minutes=60)
            )
        )

    def test_unset_duration_falls_back_to_three_hours(self):
        for unknown in (None, 0, -1):
            self.assertEqual(
                time_gates.live_session_window(unknown),
                time_gates.LIVE_SESSION_WINDOW,
            )
        self.assertEqual(
            time_gates.live_session_window(3600), timedelta(seconds=3600)
        )

    def test_forty_derivation_recording_plus_opening(self):
        # #40's own example: a 55-minute recording means a 60-minute live
        # session (the recording IS the live session minus the opening
        # five minutes).
        self.assertEqual(time_gates.live_duration_seconds(55 * 60), 3600)


class TestOpeningWindow(unittest.TestCase):
    """#35: the opening five minutes belong to the assistant."""

    start = datetime(2026, 7, 15, 10, 0)

    def test_window_is_the_first_five_minutes(self):
        self.assertTrue(time_gates.in_opening_window(self.start, self.start))
        self.assertTrue(
            time_gates.in_opening_window(
                self.start, self.start + timedelta(minutes=4, seconds=59)
            )
        )
        self.assertFalse(
            time_gates.in_opening_window(self.start, self.start + timedelta(minutes=5))
        )

    def test_before_the_bell_is_not_the_opening_block(self):
        self.assertFalse(
            time_gates.in_opening_window(self.start, self.start - timedelta(seconds=1))
        )

    def test_a_pre_session_answer_during_the_opening_block_is_on_time(self):
        # #35: a student who hasn't answered the pre-session questions
        # answers them during this block — attendance recorded then must be
        # accepted, not rejected as a forged/early claim.
        self.assertTrue(
            time_gates.attendance_claim_permitted(
                self.start, self.start + timedelta(minutes=3)
            )
        )


class TestDoorClose(unittest.TestCase):
    """#25 door policy: past start + door_close_seconds a NEW live join is
    refused server-side. Unset/0 means the door never closes (a missing
    window must not lock students out), and re-entry is the caller's call —
    this rule only judges the window itself."""

    start = datetime(2026, 7, 15, 10, 0)

    def test_before_start_the_door_is_not_closed(self):
        # An early request is a pre-download, never a late join.
        self.assertFalse(
            time_gates.door_closed_for_new_joins(
                self.start, 300, self.start - timedelta(hours=2)
            )
        )

    def test_join_at_the_bell_is_allowed(self):
        self.assertFalse(
            time_gates.door_closed_for_new_joins(self.start, 300, self.start)
        )

    def test_join_inside_the_window_is_allowed(self):
        self.assertFalse(
            time_gates.door_closed_for_new_joins(
                self.start, 300, self.start + timedelta(minutes=4, seconds=59)
            )
        )

    def test_join_at_the_close_boundary_is_refused(self):
        self.assertTrue(
            time_gates.door_closed_for_new_joins(
                self.start, 300, self.start + timedelta(minutes=5)
            )
        )

    def test_join_well_after_close_is_refused(self):
        self.assertTrue(
            time_gates.door_closed_for_new_joins(
                self.start, 300, self.start + timedelta(minutes=45)
            )
        )

    def test_unset_window_means_the_door_never_closes(self):
        # Pre-field Replay Session rows read back as 0/None — they must be
        # exactly as open as before the field existed.
        for unset in (None, 0, "", "0"):
            self.assertFalse(
                time_gates.door_closed_for_new_joins(
                    self.start, unset, self.start + timedelta(days=1)
                )
            )

    def test_negative_window_is_treated_as_never_closes(self):
        self.assertFalse(
            time_gates.door_closed_for_new_joins(
                self.start, -60, self.start + timedelta(hours=1)
            )
        )

    def test_window_shorter_than_opening_five_minutes_is_widened(self):
        # #35: "nobody is locked out in the first five minutes" — a
        # 60-second door still keeps the opening block open...
        self.assertFalse(
            time_gates.door_closed_for_new_joins(
                self.start, 60, self.start + timedelta(minutes=3)
            )
        )
        # ...and closes right when the opening block ends.
        self.assertTrue(
            time_gates.door_closed_for_new_joins(
                self.start, 60, self.start + timedelta(minutes=5)
            )
        )

    def test_longer_window_is_honoured(self):
        ten_minutes = 600
        self.assertFalse(
            time_gates.door_closed_for_new_joins(
                self.start, ten_minutes, self.start + timedelta(minutes=9)
            )
        )
        self.assertTrue(
            time_gates.door_closed_for_new_joins(
                self.start, ten_minutes, self.start + timedelta(minutes=10)
            )
        )

    def test_default_constant_matches_the_manifest_default(self):
        self.assertEqual(time_gates.DEFAULT_DOOR_CLOSE_SECONDS, 300)


if __name__ == "__main__":
    unittest.main()
