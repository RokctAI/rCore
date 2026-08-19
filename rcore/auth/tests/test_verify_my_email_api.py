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
# See license.txt

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch
from rcore.auth.auth.verify_my_email import verify_my_email as vme_module


def _impl(fn):
    """The undecorated endpoint body. The frappe rate limiter needs a live
    request context; it is frappe core's responsibility, not under test."""
    return inspect.unwrap(fn)


class TestVerifyMyEmailApiClients(FrappeTestCase):
    """API clients (the app's deferred-OTP email verify) must get JSON they
    can parse; browser link clicks keep the web page."""

    EMAIL = "verify_my_email_api_test@example.com"
    TOKEN = "654321"

    def setUp(self):
        frappe.set_user("Administrator")
        self._delete_user()
        frappe.get_doc({
            "doctype": "User",
            "email": self.EMAIL,
            "first_name": "Verify",
            "last_name": "Api",
            "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        frappe.db.set_value(
            "User", self.EMAIL, "email_verification_token", self.TOKEN,
            update_modified=False,
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        self._delete_user()

    def _delete_user(self):
        if frappe.db.exists("User", self.EMAIL):
            frappe.delete_doc(
                "User", self.EMAIL, ignore_permissions=True, force=True
            )

    def _as_mobile_client(self):
        return patch.object(
            frappe.local, "request", frappe._dict({
                "headers": frappe._dict({"X-Client-Type": "mobile"}),
            }), create=True,
        )

    def test_mobile_client_gets_json_success(self):
        with self._as_mobile_client(), patch("frappe.enqueue"):
            result = _impl(vme_module.verify_my_email)(self.TOKEN)
        self.assertIsInstance(result, dict)
        self.assertTrue(result["data"]["verified"])
        self.assertTrue(
            frappe.db.get_value("User", self.EMAIL, "email_verified_at")
        )
        self.assertFalse(
            frappe.db.get_value("User", self.EMAIL, "email_verification_token")
        )

    def test_mobile_client_gets_json_error_for_bad_token(self):
        with self._as_mobile_client():
            result = _impl(vme_module.verify_my_email)("000000")
        self.assertIsInstance(result, dict)
        self.assertFalse(result["data"]["verified"])
        self.assertEqual(result.get("status_code"), 401)

    def test_browser_click_keeps_web_page(self):
        with patch.object(
            frappe.local, "request", frappe._dict({
                "headers": frappe._dict({"Accept": "text/html"}),
            }), create=True,
        ), patch("frappe.enqueue"), patch(
            "frappe.respond_as_web_page"
        ) as web_page:
            result = _impl(vme_module.verify_my_email)(self.TOKEN)
        self.assertIsNone(result)
        web_page.assert_called_once()
