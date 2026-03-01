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

        # Patch LoginManager.post_login to skip session/cookie creation.
        # The real post_login tries to create DB sessions using request attributes,
        # which fails in CI where there is no real HTTP request.
        # Our minimal replacement just sets the user context.
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

        # Verify role assignment
        frappe.clear_cache(user=user.name)
        roles = frappe.get_roles(user.name)
        self.assertIn("System Manager", roles,
                       f"System Manager role was not assigned to {user.name}. Roles found: {roles}")

        frappe.delete_doc("User", self.sys_user_email, force=True)
