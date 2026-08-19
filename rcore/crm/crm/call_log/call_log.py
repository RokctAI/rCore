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

# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Platform call-log API, ported from the standalone CRM Call Log controller
onto the erp telephony `Call Log` doctype (the CRM Call Log doctype dissolved
into it in the CRM merge wave). The historic api.crm.call_log.* cmd aliases
keep resolving here. Lead/deal/task/note context rides on Call Log's `links`
Dynamic Link table instead of the standalone doctype's reference fields."""

import frappe
from frappe import _

from rcore.crm.crm.core.records import seconds_to_duration


def get_contact_by_phone_number(phone_number: str):
	"""Best-effort Contact lookup by exact phone number match."""
	if not phone_number:
		return {"full_name": "Unknown", "image": None}

	contact_name = frappe.db.get_value("Contact Phone", {"phone": phone_number}, "parent")
	if not contact_name:
		return {"full_name": "Unknown", "image": None}

	contact = frappe.db.get_value(
		"Contact", contact_name, ["name", "full_name", "image"], as_dict=True
	)
	return contact or {"full_name": "Unknown", "image": None}


def parse_call_log(call):
	call["show_recording"] = False
	call["_duration"] = seconds_to_duration(call.get("duration"))
	# erp Call Log models the internal party as employee_user_id (Link User)
	agent = call.get("employee_user_id")
	if call.get("type") == "Incoming":
		call["activity_type"] = "incoming_call"
		contact = get_contact_by_phone_number(call.get("from"))
		receiver = (
			frappe.db.get_values("User", agent, ["full_name", "user_image"])[0]
			if agent
			else [None, None]
		)
		call["_caller"] = {
			"label": contact.get("full_name", "Unknown"),
			"image": contact.get("image"),
		}
		call["_receiver"] = {
			"label": receiver[0],
			"image": receiver[1],
		}
	elif call.get("type") == "Outgoing":
		call["activity_type"] = "outgoing_call"
		contact = get_contact_by_phone_number(call.get("to"))
		caller = (
			frappe.db.get_values("User", agent, ["full_name", "user_image"])[0]
			if agent
			else [None, None]
		)
		call["_caller"] = {
			"label": caller[0],
			"image": caller[1],
		}
		call["_receiver"] = {
			"label": contact.get("full_name", "Unknown"),
			"image": contact.get("image"),
		}

	return call


@frappe.whitelist()
def get_call_log(name: str):
	call = frappe.get_cached_doc("Call Log", name).as_dict()

	call = parse_call_log(call)

	notes = []
	tasks = []

	if call.get("links"):
		for link in call.get("links"):
			if link.get("link_doctype") == "Sales Task":
				task = frappe.get_cached_doc("Sales Task", link.get("link_name")).as_dict()
				tasks.append(task)
			elif link.get("link_doctype") == "Sales Note":
				note = frappe.get_cached_doc("Sales Note", link.get("link_name")).as_dict()
				notes.append(note)
			elif link.get("link_doctype") == "Lead":
				call["_lead"] = link.get("link_name")
			elif link.get("link_doctype") == "Opportunity":
				call["_deal"] = link.get("link_name")

	call["_tasks"] = tasks
	call["_notes"] = notes
	return call


def _link_with_reference_doc(call_doc, reference_doctype, reference_name):
	for link in call_doc.links:
		if link.link_doctype == reference_doctype and link.link_name == reference_name:
			return

	call_doc.append("links", {"link_doctype": reference_doctype, "link_name": reference_name})


@frappe.whitelist()
def create_lead_from_call_log(call_log: str | dict, lead_details: str | dict | None = None):
	call_log_data = frappe.parse_json(call_log or {})

	if isinstance(call_log_data, str):
		call_log_name = call_log_data
	elif isinstance(call_log_data, dict):
		call_log_name = call_log_data.get("name")
	else:
		call_log_name = None

	if not call_log_name:
		frappe.throw(_("A valid call log is required."), frappe.ValidationError)

	call_doc = frappe.get_doc("Call Log", call_log_name)

	if not call_doc.has_permission("write"):
		frappe.throw(_("You are not permitted to update this call log."), frappe.PermissionError)

	if not frappe.has_permission("Lead", "create"):
		frappe.throw(_("You are not permitted to create leads."), frappe.PermissionError)

	lead_details_data = frappe.parse_json(lead_details or {})
	if lead_details_data and not isinstance(lead_details_data, dict):
		frappe.throw(_("Invalid lead details supplied."), frappe.ValidationError)

	lead = frappe.new_doc("Lead")
	meta = frappe.get_meta("Lead")
	valid_fieldnames = [df.fieldname for df in meta.fields]

	sanitized_details = {
		key: value for key, value in (lead_details_data or {}).items() if key in valid_fieldnames
	}

	if "lead_owner" in valid_fieldnames and not sanitized_details.get("lead_owner"):
		sanitized_details["lead_owner"] = frappe.session.user

	if "mobile_no" in valid_fieldnames and not sanitized_details.get("mobile_no"):
		sanitized_details["mobile_no"] = call_doc.get("from") or ""

	if "first_name" in valid_fieldnames and not sanitized_details.get("first_name"):
		reference_label = sanitized_details.get("mobile_no") or call_doc.name
		sanitized_details["first_name"] = _("Lead from call {0}").format(reference_label)

	lead.update(sanitized_details)
	lead.flags.ignore_mandatory = True
	lead.insert()

	_link_with_reference_doc(call_doc, "Lead", lead.name)
	call_doc.save()

	return lead.name
