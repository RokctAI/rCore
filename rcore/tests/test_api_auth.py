# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import MagicMock
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

        # Mock cookie_manager and response which are used by LoginManager
        # Using native classes instead of MagicMock to avoid PyMySQL "tuple item" errors
        class MockCookieManager:
            def __init__(self): pass
            def init_cookies(self): pass
            def set_cookie(self, key, value, expires=None, secure=False, httponly=False, samesite="Lax", **kwargs): pass
            def delete_cookie(self, key, **kwargs): pass

        class MockResponse:
            def __init__(self):
                self.cookies = {}
            def set_cookie(self, key, value, expires=None, secure=False, httponly=False, samesite="Lax", **kwargs):
                self.cookies[key] = value
            def delete_cookie(self, key, **kwargs):
                if key in self.cookies: del self.cookies[key]

        class MockRequest:
            def __init__(self):
                self.method = "POST"
                self.remote_addr = "127.0.0.1"
                self.host = "localhost"
                self.path = "/api/method/rcore.api.auth.login"
                self.headers = {
                    "User-Agent": "Mozilla/5.0 (CI)",
                    "X-Forwarded-For": "127.0.0.1",
                    "Host": "localhost"
                }
                self.environ = {
                    "HTTP_USER_AGENT": "Mozilla/5.0 (CI)",
                    "REMOTE_ADDR": "127.0.0.1",
                    "HTTP_HOST": "localhost",
                    "PATH_INFO": "/api/method/rcore.api.auth.login",
                    "REQUEST_METHOD": "POST"
                }
                self.form = {}
                self.cookies = {}
            def get_data(self): return b""
            def get(self, key, default=None): return self.headers.get(key, default)

        frappe.local.cookie_manager = MockCookieManager()
        frappe.local.response = MockResponse()
        frappe.local.request = MockRequest()
        frappe.local.user_agent = "Mozilla/5.0 (CI)"

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(frappe.local, "request"):
            del frappe.local.request
        if hasattr(frappe.local, "response"):
            del frappe.local.response
        if hasattr(frappe.local, "cookie_manager"):
            del frappe.local.cookie_manager

    def test_login_success(self):
        # Test valid login
        response = login(self.user.email, "password")
        self.assertTrue(response.get("status"), f"Login failed: {response.get('message')}")
        self.assertEqual(response.get("message"), "Logged In")
        self.assertIn("access_token", response.get("data"))

        # Verify API keys were generated
        user = frappe.get_doc("User", self.user.name)
        self.assertTrue(user.api_key)
        self.assertTrue(user.api_secret)

    def test_login_failure(self):
        # Test invalid password
        response = login(self.user.email, "wrongpassword")
        self.assertFalse(response.get("status"))
        self.assertEqual(response.get("message"), "Invalid credentials")

    def test_system_user_role_assignment(self):
        # Create a system user without System Manager role
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.sys_user_email,
            "first_name": "Sys",
            "last_name": "User",
            "user_type": "System User",
            "new_password": "password"
        }).insert(ignore_permissions=True)

        # Ensure only Employee role is present initially
        user.add_roles("Employee")
        frappe.db.delete(
            "Has Role", {
                "parent": user.name, "role": "System Manager"})
        frappe.clear_cache(user=user.name)

        # Login should auto-assign System Manager role
        response = login(self.sys_user_email, "password")
        self.assertTrue(response.get("status"), f"Login failed: {response.get('message')}")

        # Verify role assignment directly from DB - use get_roles carefully
        # We check both DB and cache
        frappe.clear_cache(user=user.name)
        roles = frappe.get_roles(user.name)
        self.assertIn("System Manager", roles, f"System Manager role was not assigned to {user.name}. Roles found: {roles}")

        frappe.delete_doc("User", self.sys_user_email, force=True)
