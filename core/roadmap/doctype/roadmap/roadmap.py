# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from core.roadmap.tasks import _get_api_key

class Roadmap(Document):
	def before_save(self):
		"""
		On saving the Roadmap document, automatically update the AI and GitHub statuses
		based on the current configuration.
		"""
		if self.source_repository:
			# Update AI Status
			if _get_api_key():
				self.ai_status = "Ready"
			else:
				self.ai_status = "Not Configured"
		else:
			# If the repository is cleared, reset statuses
			self.ai_status = "Not Configured"
			self.github_status = "Unlinked"
