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

"""Server-side time-gate rules (product log #25) — frappe-free pure module.

#21's client ServerClock stops clock spoofing in the UI; these rules are the
BACKEND half: the decisions content-serving endpoints apply against
`frappe.utils.now_datetime()` so a caller who bypasses the app entirely
(direct API calls, patched client) still can't get early access or forge
attendance timing. API files own the I/O and call these for the judgement
(see SDK_README "Testable Backend Logic" — this module imports no frappe and
is unit-tested standalone).

All datetimes are naive server-local, matching frappe's now_datetime().
"""

from datetime import datetime, timedelta

# A synced-late attendance claim is normal (offline devices flush when back
# online); a claim about a session months past is not a sync, it's a forgery
# attempt or a bug. Two weeks comfortably covers school-holiday offline gaps.
MAX_ATTENDANCE_SYNC_DELAY_DAYS = 14

# Tolerance for ordinary clock skew between app servers — NOT device clocks
# (device time is untrusted entirely; this only pads comparisons between
# server-side timestamps written by different processes).
CLOCK_SKEW = timedelta(minutes=5)

# Product log #35: THE OPENING FIVE MINUTES BELONG TO THE ASSISTANT —
# greeting, intro and handover all fit inside them. "Nobody is locked out in
# the first five minutes": a join inside this window is normal, not a late
# join, and a pre-session answer submitted during it is on time.
OPENING_WINDOW = timedelta(minutes=5)

# §2 door policy / #25: how long after start a NEW live join is still
# allowed when Replay Session.door_close_seconds is set to nothing useful.
# Matches the manifest default ("door_close_seconds": 300) and the client's
# ScheduledSession.doorCloseSeconds fallback — kept here only as the shared
# reference value; the rule itself reads the per-session field.
DEFAULT_DOOR_CLOSE_SECONDS = 300

# FALLBACK: how long after scheduled_at a request is still the LIVE session
# rather than a request for its recording, when the session's real length is
# unknown.
#
# Replay Session now carries a real `duration_seconds` field (see
# [live_session_window], which prefers it); this constant remains only as
# the fallback for rows where it is unset/0 — a deliberate generous upper
# bound rather than a real end time: erring long serves a live lesson,
# erring short locks students out mid-session — and lockout is the harm
# that matters, so an unknown duration must never shorten the window.
LIVE_SESSION_WINDOW = timedelta(hours=3)


def live_session_window(duration_seconds=None) -> timedelta:
    """The live window for a session: its real `duration_seconds`
    (Replay Session field, #40 makes it derivable — see
    [live_duration_seconds]) when set, else the LIVE_SESSION_WINDOW
    3-hour upper bound. Unset/0/negative reads as unknown — the safe
    long fallback, never a shortened window (lockout is the harm that
    matters, and pre-field rows read back as 0)."""
    if not duration_seconds:
        return LIVE_SESSION_WINDOW
    seconds = int(duration_seconds)
    if seconds <= 0:
        return LIVE_SESSION_WINDOW
    return timedelta(seconds=seconds)


def live_duration_seconds(recording_duration_seconds) -> int:
    """#40's derivation: a recorded session IS the live session minus the
    assistant's opening five minutes (a 60-minute live session yields a
    55-minute recording) — so the live duration is the recording length
    plus OPENING_WINDOW. Publishers writing Replay Session rows use this
    to fill `duration_seconds` from the measured recording length."""
    return int(recording_duration_seconds) + int(OPENING_WINDOW.total_seconds())


def recording_unlock_at(scheduled_at: datetime) -> datetime:
    """When a broadcast's recording becomes servable: midnight after the
    broadcast day ("recordings unlock the following day", product doc §2).
    Mirrors the client's LibraryEntry.defaultRecordingUnlock exactly — the
    same rule, now enforced where the content is actually served."""
    day = scheduled_at.replace(hour=0, minute=0, second=0, microsecond=0)
    return day + timedelta(days=1)


def recording_unlocked(scheduled_at: datetime, now: datetime) -> bool:
    """Whether the recording of a session broadcast at [scheduled_at] may be
    served at server-time [now]."""
    return now >= recording_unlock_at(scheduled_at)


def attendance_claim_permitted(scheduled_at: datetime, now: datetime) -> bool:
    """Whether an 'Attended' outcome for a session broadcast at
    [scheduled_at] is acceptable at server-time [now].

    - A claim BEFORE the session starts is a forgery: you cannot have
      attended a broadcast that hasn't begun (small skew pad only).
    - A claim long after is not a late offline sync anymore
      (MAX_ATTENDANCE_SYNC_DELAY_DAYS) — refuse rather than let arbitrary
      backdated rows steer streaks and partner alerts.

    Skip outcomes are deliberately NOT time-gated here: recording a skip
    early harms only the student's own record and the skip flow already
    permits pre-session skips (the §3 skip gate runs before start).
    """
    if now < scheduled_at - CLOCK_SKEW:
        return False
    if now > scheduled_at + timedelta(days=MAX_ATTENDANCE_SYNC_DELAY_DAYS):
        return False
    return True


def is_past_broadcast(scheduled_at: datetime, now: datetime) -> bool:
    """Whether the broadcast has STARTED at server-time [now].

    Note this says started, not finished — it is true for the whole live
    session too, so it must NOT by itself decide "this is a recording
    request" (doing so locked students out of their own live lesson; see
    [is_recording_request], which is what the serving gate uses)."""
    return now >= scheduled_at


def in_opening_window(scheduled_at: datetime, now: datetime) -> bool:
    """#35: inside the assistant's opening block — the first five minutes.
    A join here is normal and a pre-session answer here is on time; nothing
    may lock a student out during it."""
    return scheduled_at <= now < scheduled_at + OPENING_WINDOW


def is_live_window(
    scheduled_at: datetime, now: datetime, duration_seconds=None
) -> bool:
    """Whether a request at [now] is for the LIVE session — from the moment
    it starts (the #35 opening block is squarely inside this) until the
    live window has elapsed. Serving here is a live join, never a recording
    request, so the next-day unlock must not apply.

    [duration_seconds] is the session's real length
    (Replay Session.duration_seconds) when known; unset falls back to the
    3-hour upper bound (see [live_session_window])."""
    return scheduled_at <= now < scheduled_at + live_session_window(duration_seconds)


def door_closed_for_new_joins(
    scheduled_at: datetime, door_close_seconds, now: datetime
) -> bool:
    """#25's live-join door: whether a NEW join at server-time [now] is past
    the session's door-close window (`Replay Session.door_close_seconds`).

    - [door_close_seconds] unset/0/negative → the door NEVER closes (False).
      Deliberately the safe reading: a missing window must not lock students
      out (same ethos as LIVE_SESSION_WINDOW above — lockout is the harm
      that matters), and it keeps every pre-field Replay Session row, which
      reads back as 0, exactly as open as it was before the field existed.
    - Never closed before the session starts: an early request is a
      pre-download, not a late join.
    - A configured window shorter than #35's opening five minutes is widened
      to OPENING_WINDOW ("nobody is locked out in the first five minutes").

    This is about NEW joiners only (spec: door_close_seconds elapsed →
    DOOR_LOCKED "for new joiners only") — the caller decides re-entry by
    checking whether the student already holds an 'Attended' event for the
    session, and skips this gate when they do.
    """
    if not door_close_seconds:
        return False
    seconds = int(door_close_seconds)
    if seconds <= 0:
        return False
    window = max(timedelta(seconds=seconds), OPENING_WINDOW)
    return now >= scheduled_at + window


def is_recording_request(
    scheduled_at: datetime, now: datetime, duration_seconds=None
) -> bool:
    """Whether a request at [now] is for the session's RECORDING — only
    once the live window has fully elapsed. This, not [is_past_broadcast],
    is what gates the next-day unlock and #27 period coverage.

    [duration_seconds] is the session's real length
    (Replay Session.duration_seconds) when known; unset falls back to the
    3-hour upper bound (see [live_session_window])."""
    return now >= scheduled_at + live_session_window(duration_seconds)
