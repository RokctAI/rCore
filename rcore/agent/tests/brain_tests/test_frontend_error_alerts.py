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

import json
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock
from frappe.utils import getdate, nowdate
from rcore.agent.brain.frontend_error_alerts import (
    send_frontend_error_digest,
    _extract_frontend_error_events,
    _split_signature,
)

TODAY = nowdate()

# Summary lines dated today so the digest's since-date filter keeps them.
SUMMARY = (
    "Created by Ray on 2026-08-01.\n"
    f"Frontend error: null check operator used on a null value at url: /lesson/maths-1 by Thandi M on {TODAY}.\n"
    f"Frontend error: timing_report at url: /api/method/ping by Thandi M on {TODAY}.\n"
    f"Frontend error: null check operator used on a null value at url: /lesson/science-2 by Sipho K on {TODAY}.\n"
    "Updated by Ray on 2026-08-13."
)


class TestFrontendErrorAlerts(FrappeTestCase):
    def test_extract_parses_error_lines_and_excludes_timing_report(self):
        events = _extract_frontend_error_events(SUMMARY)

        # timing_report and non-error lines are dropped; 2 real errors remain
        self.assertEqual(len(events), 2)
        self.assertTrue(all("timing_report" not in e["signature"] for e in events))
        self.assertEqual(events[0]["user"], "Thandi M")
        self.assertEqual(events[0]["url"], "/lesson/maths-1")
        self.assertEqual(events[0]["date"], getdate(TODAY))

    def test_extract_respects_since_date(self):
        old_summary = "Frontend error: boom by Thandi M on 2026-08-01."
        self.assertEqual(
            _extract_frontend_error_events(old_summary, since_date=getdate("2026-08-10")),
            [],
        )

    def test_same_error_on_different_urls_shares_one_signature(self):
        sig_a, url_a = _split_signature(
            "frontend error: null check operator used on a null value at url: /lesson/maths-1"
        )
        sig_b, url_b = _split_signature(
            "frontend error: null check operator used on a null value at url: /lesson/science-2"
        )
        self.assertEqual(sig_a, sig_b)
        self.assertNotEqual(url_a, url_b)

    @patch("rcore.agent.brain.frontend_error_alerts.frappe")
    def test_non_tenant_site_is_a_noop(self, mock_frappe):
        mock_frappe.conf.get.return_value = "control"

        send_frontend_error_digest()

        mock_frappe.get_all.assert_not_called()
        mock_frappe.sendmail.assert_not_called()

    @patch("rcore.agent.brain.frontend_error_alerts.get_system_managers")
    @patch("rcore.agent.brain.frontend_error_alerts.frappe")
    def test_digest_emails_system_managers_for_real_errors(
        self, mock_frappe, mock_get_system_managers
    ):
        mock_frappe.conf.get.return_value = "tenant"
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_default.return_value = None
        mock_frappe.local.site = "tenant.example"
        mock_frappe.get_all.return_value = [
            MagicMock(summary=SUMMARY),
        ]
        mock_get_system_managers.return_value = ["Admin User <admin@example.com>"]

        send_frontend_error_digest()

        mock_frappe.sendmail.assert_called_once()
        _, kwargs = mock_frappe.sendmail.call_args
        self.assertEqual(kwargs["recipients"], ["Admin User <admin@example.com>"])
        # both occurrences grouped under ONE signature
        self.assertIn("1 new frontend error", kwargs["subject"])
        self.assertIn("Occurrences since last digest: 2", kwargs["message"])
        self.assertNotIn("timing_report", kwargs["message"])

    @patch("rcore.agent.brain.frontend_error_alerts.get_system_managers")
    @patch("rcore.agent.brain.frontend_error_alerts.frappe")
    def test_timing_report_only_activity_sends_nothing(
        self, mock_frappe, mock_get_system_managers
    ):
        mock_frappe.conf.get.return_value = "tenant"
        mock_frappe.db.exists.return_value = True
        mock_frappe.db.get_default.return_value = None
        mock_frappe.get_all.return_value = [
            MagicMock(
                summary=f"Frontend error: timing_report at url: /x by Thandi M on {TODAY}."
            ),
        ]

        send_frontend_error_digest()

        mock_frappe.sendmail.assert_not_called()
        mock_get_system_managers.assert_not_called()
        # last-run marker still advances
        mock_frappe.db.set_default.assert_called()

    @patch("rcore.agent.brain.frontend_error_alerts._signature_hash")
    @patch("rcore.agent.brain.frontend_error_alerts.get_system_managers")
    @patch("rcore.agent.brain.frontend_error_alerts.frappe")
    def test_recently_alerted_signature_is_not_re_emailed(
        self, mock_frappe, mock_get_system_managers, mock_hash
    ):
        from frappe.utils import now_datetime

        mock_hash.return_value = "abc123"
        mock_frappe.conf.get.return_value = "tenant"
        mock_frappe.db.exists.return_value = True

        def get_default(key):
            if key == "frontend_error_digest_alerted":
                return json.dumps({"abc123": str(now_datetime())})
            return None

        mock_frappe.db.get_default.side_effect = get_default
        mock_frappe.get_all.return_value = [
            MagicMock(summary=f"Frontend error: boom by Thandi M on {TODAY}."),
        ]

        send_frontend_error_digest()

        mock_frappe.sendmail.assert_not_called()


if __name__ == "__main__":
    import unittest
    unittest.main()
