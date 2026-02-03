# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from rcore.api.auth import login

class TestAPIAuth(FrappeTestCase):
    def setUp(self):
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
            self.user.add_roles("System Manager")
        else:
            self.user = frappe.get_doc("User", "test_auth_api@example.com")
            self.user.new_password = "password"
            self.user.save(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_login_success(self):
        # Test valid login
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
        login(user_email, "password")
        
        roles = frappe.get_roles(user.name)
        self.assertIn("System Manager", roles)
        
        frappe.delete_doc("User", user_email, force=True)
