# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch
from rcore.api.auth import login


class TestAPIAuth(FrappeTestCase):
    def setUp(self):
        if not frappe.db.exists("Role", "Employee"):
            frappe.get_doc({"doctype": "Role", "role_name": "Employee"}).insert(
                ignore_permissions=True)

        # Create a test user
        if not frappe.db.exists("User", "test_auth_api@example.com"):
            self.user = frappe.get_doc({
                "doctype": "User",
                "email": "test_auth_api@example.com",
                "first_name": "API",
                "last_name": "Test",
                "enabled": 1,
                "new_password": "password"
            }).insert(ignore_permissions=True)
            self.user.add_roles("System Manager", "Employee")
        else:
            self.user = frappe.get_doc("User", "test_auth_api@example.com")
            self.user.new_password = "password"
            self.user.save(ignore_permissions=True)

        self.sys_user_email = "sys_user_test@example.com"
        if frappe.db.exists("User", self.sys_user_email):
            frappe.delete_doc("User", self.sys_user_email, force=True)

        # LoginManager needs frappe.local.request and cookie_manager to exist.
        # We use frappe._dict for request so all attribute access returns None
        # (a primitive) instead of raising AttributeError or returning MagicMock.
        frappe.local.request = frappe._dict({
            "method": "POST",
            "remote_addr": "127.0.0.1",
            "host": "localhost",
            "path": "/api/method/rcore.api.auth.login",
            "user_agent": "Mozilla/5.0 (CI)",
            "headers": frappe._dict({
                "User-Agent": "Mozilla/5.0 (CI)",
                "X-Forwarded-For": "127.0.0.1",
                "Host": "localhost"
            }),
            "environ": {
                "HTTP_USER_AGENT": "Mozilla/5.0 (CI)",
                "REMOTE_ADDR": "127.0.0.1",
                "HTTP_HOST": "localhost",
            },
            "form": {},
            "args": {},
            "cookies": {},
        })
        frappe.local.cookie_manager = frappe._dict({
            "init_cookies": lambda: None,
            "set_cookie": lambda *a, **kw: None,
            "delete_cookie": lambda *a, **kw: None,
        })

        # Patch post_login to skip session/cookie DB writes.
        # The real post_login creates DB sessions using request attributes,
        # which fails in CI. Our replacement just sets the user context.
        def _mock_post_login(login_manager_self):
            frappe.set_user(login_manager_self.user)

        self.post_login_patcher = patch(
            "frappe.auth.LoginManager.post_login",
            _mock_post_login
        )
        self.post_login_patcher.start()

    def tearDown(self):
        self.post_login_patcher.stop()
        frappe.set_user("Administrator")
        for attr in ("request", "response", "cookie_manager"):
            if hasattr(frappe.local, attr):
                delattr(frappe.local, attr)

    def test_login_success(self):
        response = login(self.user.email, "password")
        self.assertTrue(response.get("status"), f"Login failed: {response.get('message')}")
        self.assertEqual(response.get("message"), "Logged In")
        self.assertIn("access_token", response.get("data"))

        user = frappe.get_doc("User", self.user.name)
        self.assertTrue(user.api_key)
        self.assertTrue(user.api_secret)

    def test_login_failure(self):
        response = login(self.user.email, "wrongpassword")
        self.assertFalse(response.get("status"))
        self.assertEqual(response.get("message"), "Invalid credentials")

    def test_system_user_role_assignment(self):
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.sys_user_email,
            "first_name": "Sys",
            "last_name": "User",
            "user_type": "System User",
            "new_password": "password"
        }).insert(ignore_permissions=True)

        user.add_roles("Employee")
        frappe.db.delete(
            "Has Role", {
                "parent": user.name, "role": "System Manager"})
        frappe.clear_cache(user=user.name)

        response = login(self.sys_user_email, "password")
        self.assertTrue(response.get("status"), f"Login failed: {response.get('message')}")

        frappe.clear_cache(user=user.name)
        roles = frappe.get_roles(user.name)
        self.assertIn("System Manager", roles,
                       f"System Manager role was not assigned to {user.name}. Roles found: {roles}")

        frappe.delete_doc("User", self.sys_user_email, force=True)
