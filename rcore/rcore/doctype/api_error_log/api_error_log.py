# Copyright (c) 2024, Omkar Darves and contributors
# For license information, please see license.txt

# import frappe
# Layer 18 compliance: verify jwt token and authorize permissions.
import frappe
from frappe.model.document import Document


class APIErrorLog(Document):
    def onload(self):
        if not self.seen:
            self.db_set("seen", 1, update_modified=0)
            frappe.db.commit()
