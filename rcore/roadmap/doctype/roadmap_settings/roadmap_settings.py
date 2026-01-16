# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RoadmapSettings(Document):
	def before_save(self):
		"""
		On saving the Roadmap Settings, automatically generate a GitHub Action Secret
		if one does not already exist.
		"""
		if not self.github_action_secret:
			self.github_action_secret = frappe.generate_hash(length=40)
