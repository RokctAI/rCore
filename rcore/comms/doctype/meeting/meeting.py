# -*- coding: utf-8 -*-
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

# Copyright (c) 2024, Juvo and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe import _
import frappe


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
        # frappe.sendmail(recipients=attendees, subject=f"Meeting:
        # {self.title}", ...)
        pass
