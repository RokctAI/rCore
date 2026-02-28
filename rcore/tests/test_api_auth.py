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

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(frappe.local, "request"):
            del frappe.local.request
        if hasattr(frappe.local, "response"):
            del frappe.local.response

    def test_login_success(self):
        # Test valid login
        # LoginManager requires request and response objects
        frappe.local.request = MagicMock()
        frappe.local.response = MagicMock()
        frappe.local.response.set_cookie = MagicMock()
        frappe.local.response.delete_cookie = MagicMock()
        frappe.local.request.method = "POST"
        frappe.local.request.remote_addr = "127.0.0.1"

        response = login(self.user.email, "password")
        self.assertTrue(response.get("status"))
        self.assertEqual(response.get("message"), "Logged In")
        self.assertIn("access_token", response.get("data"))

        # Verify API keys were generated
        user = frappe.get_doc("User", self.user.name)
        self.assertTrue(user.api_key)
        self.assertTrue(user.api_secret)

    def test_login_failure(self):
        # Test invalid password
        frappe.local.request = MagicMock()
        frappe.local.response = MagicMock()
        frappe.local.response.set_cookie = MagicMock()
        frappe.local.response.delete_cookie = MagicMock()
        frappe.local.request.method = "POST"
        frappe.local.request.remote_addr = "127.0.0.1"

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
            "new_password": "password",
            "roles": [{"role": "Employee"}]
        }).insert(ignore_permissions=True)

        # Login should auto-assign System Manager role
        frappe.local.request = MagicMock()
        frappe.local.response = MagicMock()
        frappe.local.response.set_cookie = MagicMock()
        frappe.local.response.delete_cookie = MagicMock()
        frappe.local.request.method = "POST"
        frappe.local.request.remote_addr = "127.0.0.1"

        login(self.sys_user_email, "password")

        # Verify role assignment directly from DB to avoid caching issues
        has_role = frappe.db.exists("Has Role", {
            "parent": user.name,
            "role": "System Manager"
        })
        self.assertTrue(has_role, f"System Manager role was not assigned to {user.name}")

        frappe.delete_doc("User", self.sys_user_email, force=True)
