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

# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime


class StatusChangeLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		duration: DF.Duration | None
		from_date: DF.Datetime | None
		from_type: DF.Data | None
		last_status_change_log: DF.Link | None
		log_owner: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to: DF.Data | None
		to_date: DF.Datetime | None
		to_type: DF.Data | None
	# end: auto-generated types

	pass


def get_duration(from_date, to_date):
	if not isinstance(from_date, datetime):
		from_date = get_datetime(from_date)
	if not isinstance(to_date, datetime):
		to_date = get_datetime(to_date)
	duration = to_date - from_date
	return duration.total_seconds()


def add_status_change_log(doc):
	to_status_type = frappe.db.get_value("Deal Status", doc.status, "type") if doc.status else None

	if not doc.is_new():
		previous_status = doc.get_doc_before_save().status if doc.get_doc_before_save() else None
		previous_status_type = (
			frappe.db.get_value("Deal Status", previous_status, "type") if previous_status else None
		)
		if not doc.status_change_log and previous_status:
			now_minus_one_minute = add_to_date(datetime.now(), minutes=-1)
			doc.append(
				"status_change_log",
				{
					"from": previous_status,
					"from_type": previous_status_type or "",
					"to": "",
					"to_type": "",
					"from_date": now_minus_one_minute,
					"to_date": "",
					"log_owner": frappe.session.user,
				},
			)
		last_status_change = doc.status_change_log[-1]
		last_status_change.to = doc.status
		last_status_change.to_type = to_status_type or ""
		last_status_change.to_date = datetime.now()
		last_status_change.log_owner = frappe.session.user
		last_status_change.duration = get_duration(last_status_change.from_date, last_status_change.to_date)

	doc.append(
		"status_change_log",
		{
			"from": doc.status,
			"from_type": to_status_type or "",
			"to": "",
			"to_type": "",
			"from_date": datetime.now(),
			"to_date": "",
			"log_owner": frappe.session.user,
		},
	)
