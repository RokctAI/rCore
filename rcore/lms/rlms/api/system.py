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

"""System-level helpers for lms_sdk's client.

Server-authoritative time: the schedule dashboard's door policy, the skip-gate
release timer, and the join on-time window all decide access from a wall clock.
Reading the *device* wall clock lets a student unlock content early or dodge the
skip gate by changing their phone's date/time. The client instead computes a
clock offset against this endpoint (anchored to a monotonic timer, so a later
wall-clock change can't move it) and gates against server_time + elapsed.

Kept deliberately tiny: no auth-specific data, no DB read, safe to call often.
It is whitelisted (authenticated) like every other rlms endpoint — a student is
always logged in before they have a schedule to game.
"""

from datetime import datetime, timezone

import frappe


@frappe.whitelist()
def server_time():
    """Authoritative wall-clock time, as UTC.

    Returns both an ISO-8601 string (human/debug) and an integer epoch in
    milliseconds (the client's parse path — unambiguous, timezone-free). The
    client subtracts round-trip latency and anchors this to a monotonic timer;
    it does not trust its own device clock for any gating decision.
    """
    now = datetime.now(timezone.utc)
    return {
        "server_time": now.isoformat(),
        "server_epoch_ms": int(now.timestamp() * 1000),
    }
