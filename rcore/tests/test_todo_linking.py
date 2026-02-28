import frappe
from frappe.tests.utils import FrappeTestCase


class TestToDoLinking(FrappeTestCase):
    def setUp(self):
        # Ensure hierarchy exists
        if not frappe.db.exists("Vision", "Link Vision"):
            self.vision = frappe.get_doc(
                {"doctype": "Vision", "title": "Link Vision"}).insert(ignore_permissions=True)
        else:
            self.vision = frappe.get_doc("Vision", "Link Vision")

        if not frappe.db.exists("Pillar", "Link Pillar"):
            self.pillar = frappe.get_doc(
                {
                    "doctype": "Pillar",
                    "title": "Link Pillar",
                    "vision": self.vision.name}).insert(
                ignore_permissions=True)
        else:
            self.pillar = frappe.get_doc("Pillar", "Link Pillar")

        if not frappe.db.exists("Strategic Objective", "Link Strat Obj"):
            self.strat_obj = frappe.get_doc({
                "doctype": "Strategic Objective",
                "title": "Link Strat Obj",
                "pillar": self.pillar.name
            }).insert(ignore_permissions=True)
        else:
            self.strat_obj = frappe.get_doc(
                "Strategic Objective", "Link Strat Obj")

    def tearDown(self):
        frappe.db.rollback()

    def test_link_todo_to_objective(self):
        """
        Demonstrate that we can link a standard ToDo to a Custom DocType
        without a nested Table field.
        """
        todo = frappe.get_doc({
            "doctype": "ToDo",
            "description": "Complete the strategic analysis",
            "reference_type": "Strategic Objective",
            "reference_name": self.strat_obj.name,
            "status": "Open",
            "owner": "Administrator"
        }).insert(ignore_permissions=True)

        self.assertTrue(frappe.db.exists("ToDo", todo.name))
        self.assertEqual(todo.reference_type, "Strategic Objective")
        self.assertEqual(todo.reference_name, self.strat_obj.name)

        # Simulate fetching todos for this object (Headless pattern)
        linked_todos = frappe.get_all("ToDo", filters={
            "reference_type": "Strategic Objective",
            "reference_name": self.strat_obj.name
        }, fields=["name", "description", "status"])

        self.assertEqual(len(linked_todos), 1)
        self.assertEqual(
            linked_todos[0].description,
            "Complete the strategic analysis")
