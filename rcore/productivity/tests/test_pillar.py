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

# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPillar(FrappeTestCase):
    def setUp(self):
        # Create a Vision to link to
        if not frappe.db.exists("Vision", "Test Vision"):
            self.vision = frappe.get_doc(
                {"doctype": "Vision", "title": "Test Vision"}
            ).insert(ignore_permissions=True)
        else:
            self.vision = frappe.get_doc("Vision", "Test Vision")

    def tearDown(self):
        frappe.db.rollback()

    def test_create_pillar(self):
        pillar = frappe.get_doc(
            {
                "doctype": "Pillar",
                "title": "Test Pillar",
                "description": "Test Description",
                "vision": self.vision.name,
            }
        ).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("Pillar", pillar.name))
        self.assertEqual(pillar.vision, self.vision.name)

    def test_update_pillar(self):
        pillar = frappe.get_doc(
            {
                "doctype": "Pillar",
                "title": "Test Pillar Update",
                "vision": self.vision.name,
            }
        ).insert(ignore_permissions=True)

        pillar.description = "Updated Description"
        pillar.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.get_value("Pillar", pillar.name, "description"),
            "Updated Description",
        )

    def test_delete_pillar(self):
        pillar = frappe.get_doc(
            {
                "doctype": "Pillar",
                "title": "Test Pillar Delete",
                "vision": self.vision.name,
            }
        ).insert(ignore_permissions=True)

        pillar.delete(ignore_permissions=True)
        self.assertFalse(frappe.db.exists("Pillar", pillar.name))
