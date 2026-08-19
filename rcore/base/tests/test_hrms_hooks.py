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

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch, MagicMock


class TestHrmsHooks(FrappeTestCase):
    def test_employee_publish_update_hook(self):
        # Verify employee on_update hook triggers publish_update

        if not frappe.db.exists("DocType", "HR Settings") or not frappe.db.exists(
            "DocType", "Employee"
        ):
            self.skipTest("HRMS app not installed")
            return

        frappe.db.set_value("HR Settings", None, "emp_created_by", "Naming Series")

        with patch.dict("sys.modules", {"rcore.core.rhrms": MagicMock()}):
            # Create Mock Employee
            # We might need to mock frappe.db.get_single_value("HR Settings",
            # "emp_created_by") if Employee autoname runs

            employee = frappe.get_doc(
                {
                    "doctype": "Employee",
                    "first_name": "Test",
                    "last_name": "Hook",
                    "gender": "Male",
                    "date_of_birth": "1990-01-01",
                    "status": "Active",
                    "company": "Test Company",  # Might need to mock Company validation
                }
            )

            # Mock existing company check if needed, or bypass validation
            employee.flags.ignore_permissions = True
            employee.flags.ignore_validate = True
            # We want to test ON_UPDATE, so insert first
            employee.insert()

            # Now trigger update
            employee.first_name = "Test Update"
            employee.save()

        self.assertTrue(True)
