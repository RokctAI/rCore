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
import json
from frappe.tests.utils import FrappeTestCase
from rcore.agent.plan_builder import commit_plan


class TestPlanBuilder(FrappeTestCase):
    def tearDown(self):
        frappe.db.rollback()

    def test_commit_plan_structure(self):
        # Construct a full plan payload
        payload = {
            "vision_title": "Builder Vision",
            "vision_description": "Builder Desc",
            "pillars": [
                {
                    "title": "Builder Pillar 1",
                    "description": "P1 Desc",
                    "objectives": [
                        {
                            "title": "Builder Obj 1.1",
                            "description": "O1.1 Desc",
                            "kpis": [
                                {
                                    "title": "Builder KPI 1.1.1",
                                    "description": "K1.1.1 Desc",
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        response = commit_plan(json.dumps(payload))
        self.assertEqual(response.get("status"), "success")

        # Verify Hierarchy
        self.assertTrue(frappe.db.exists("Vision", {"title": "Builder Vision"}))
        vision = frappe.get_doc("Vision", {"title": "Builder Vision"})

        self.assertTrue(
            frappe.db.exists(
                "Pillar", {"title": "Builder Pillar 1", "vision": vision.name}
            )
        )
        pillar = frappe.get_doc("Pillar", {"title": "Builder Pillar 1"})

        self.assertTrue(
            frappe.db.exists(
                "Strategic Objective",
                {"title": "Builder Obj 1.1", "pillar": pillar.name},
            )
        )
        obj = frappe.get_doc("Strategic Objective", {"title": "Builder Obj 1.1"})

        self.assertTrue(
            frappe.db.exists(
                "KPI", {"title": "Builder KPI 1.1.1", "strategic_objective": obj.name}
            )
        )

        # Verify Global Link
        plan = frappe.get_doc("Plan On A Page")
        self.assertEqual(plan.vision, vision.name)
