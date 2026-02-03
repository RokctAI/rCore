# -*- coding: utf-8 -*-
# Copyright (c) 2024, Juvo and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import _

class Meeting(Document):
	def validate(self):
		self.validate_dates()

	def on_update(self):
		if self.status == "Planned":
			self.send_invites()

	def validate_dates(self):
		if self.start_date and self.end_date:
			if self.start_date > self.end_date:
				frappe.throw(_("End Date must be after Start Date"))

	def send_invites(self):
		if not self.attendees_list:
			return
		
		attendees = [x.strip() for x in self.attendees_list.split(",") if x.strip()]
		# Logic to send email invites
		# frappe.sendmail(recipients=attendees, subject=f"Meeting: {self.title}", ...)
		pass
