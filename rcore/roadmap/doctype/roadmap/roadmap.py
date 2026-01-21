# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from rcore.roadmap.tasks import _get_api_key

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
			self.github_status = "Unlinked"

	def after_save(self):
		"""
		Trigger Auto-Discovery if:
		1. We have a Repo + Key
		2. Description is empty OR Repo changed (Dirty check logic simplified for now)
		"""
		if not self.source_repository:
			return

		# Check if we have a key (local or global)
		# We use the utility helper to avoid circular imports if possible, or just checking get_password
		has_key = self.get_password("jules_api_key")
		if not has_key:
			settings = frappe.get_single("Roadmap Settings")
			has_key = settings.get_password("jules_api_key")
		
		if has_key:
			# Trigger Discovery if description is missing (First run)
			# OR if we want to force it (Future: maybe a 'force_discovery' flag)
			if not self.description or not self.classifications:
				frappe.enqueue("rcore.roadmap.tasks.discover_roadmap_context", roadmap_name=self.name)
