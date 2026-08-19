# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.contacts.address_and_contact import (
	delete_contact_and_address,
	load_address_and_contact,
)
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from frappe.desk.form.assign_to import _add as assign
from frappe.email.inbox import link_communication_to_document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import comma_and, get_link_to_form, validate_email_address

from ..status_change_log.status_change_log import add_status_change_log

# ROKCT: cross-module imports into the composed erp module are resolved from
# __name__ — the composer's app-name token must not appear in doctype-tree
# .py files (designer design_system.py precedent), and the erp SDK module
# composes as a sibling package of this crm module.
from importlib import import_module as _import_module


def _erp_import(path):
	"""Import '<app>.erp.<path>' relative to this module's composed app."""
	return _import_module(__name__.split(".crm.doctype.", 1)[0] + ".erp." + path)

_party_mod = _erp_import("accounts.party")
set_taxes = _party_mod.set_taxes
_selling_controller_mod = _erp_import("controllers.selling_controller")
SellingController = _selling_controller_mod.SellingController
from ...utils import CRMNote, copy_comments, link_communications, link_open_events
_customer_mod = _erp_import("doctype.customer.customer")
parse_full_name = _customer_mod.parse_full_name


class Lead(SellingController, CRMNote):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from ..crm_note.crm_note import CRMNote

		annual_revenue: DF.Currency
		blog_subscriber: DF.Check
		city: DF.Data | None
		company: DF.Link | None
		company_name: DF.Data | None
		country: DF.Link | None
		customer: DF.Link | None
		disabled: DF.Check
		email_id: DF.Data | None
		fax: DF.Data | None
		first_name: DF.Data | None
		gender: DF.Link | None
		image: DF.AttachImage | None
		industry: DF.Link | None
		job_title: DF.Data | None
		language: DF.Link | None
		last_name: DF.Data | None
		lead_name: DF.Data | None
		lead_owner: DF.Link | None
		market_segment: DF.Link | None
		middle_name: DF.Data | None
		mobile_no: DF.Data | None
		naming_series: DF.Literal["CRM-LEAD-.YYYY.-"]
		no_of_employees: DF.Literal["1-10", "11-50", "51-200", "201-500", "501-1000", "1000+"]
		notes: DF.Table[CRMNote]
		phone: DF.Data | None
		phone_ext: DF.Data | None
		qualification_status: DF.Literal["Unqualified", "In Process", "Qualified"]
		qualified_by: DF.Link | None
		qualified_on: DF.Date | None
		request_type: DF.Literal["", "Product Enquiry", "Request for Information", "Suggestions", "Other"]
		salutation: DF.Link | None
		state: DF.Data | None
		status: DF.Literal[
			"Lead",
			"Open",
			"Replied",
			"Opportunity",
			"Quotation",
			"Lost Quotation",
			"Interested",
			"Converted",
			"Do Not Contact",
		]
		territory: DF.Link | None
		title: DF.Data | None
		type: DF.Literal["", "Client", "Channel Partner", "Consultant"]
		unsubscribed: DF.Check
		utm_campaign: DF.Link | None
		utm_content: DF.Data | None
		utm_medium: DF.Link | None
		utm_source: DF.Link | None
		website: DF.Data | None
		whatsapp_no: DF.Data | None
	# end: auto-generated types

	def onload(self):
		customer = frappe.db.get_value("Customer", {"lead_name": self.name})
		self.get("__onload").is_customer = customer
		load_address_and_contact(self)
		self.set_onload("linked_prospects", self.get_linked_prospects())

	def validate(self):
		self.set_full_name()
		self.set_lead_name()
		self.set_title()
		self.set_status()
		self.set_default_pipeline_status()
		self.check_email_id_is_unique()
		self.validate_email_id()
		self.validate_lost_reason()
		# ROKCT platform pipeline behaviors (ported from the standalone
		# CRM Lead controller): owner share/assign + status change log.
		if not self.is_new() and self.has_value_changed("lead_owner") and self.lead_owner:
			self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)
		if self.has_value_changed("status"):
			add_status_change_log(self)

	def set_default_pipeline_status(self):
		"""status is a Link to the seeded Lead Status kanban master; fall
		back to the first Open-type status when the JSON default record is
		missing on this site."""
		if not self.status or frappe.db.exists("Lead Status", self.status):
			return
		open_statuses = frappe.get_all("Lead Status", {"type": "Open"}, pluck="name")
		if open_statuses:
			self.status = open_statuses[0]

	def validate_lost_reason(self):
		"""Require a reason when the status is moved to a Lost-type status."""
		if self.status and frappe.get_cached_value("Lead Status", self.status, "type") == "Lost":
			if not self.lost_reason:
				frappe.throw(_("Please specify a reason for losing the lead."), frappe.ValidationError)
			elif self.lost_reason == "Other" and not self.lost_notes:
				frappe.throw(_("Please specify the reason for losing the lead."), frappe.ValidationError)

	def assign_agent(self, agent):
		if not agent:
			return

		assignees = self.get_assigned_users()
		if assignees:
			for assignee in assignees:
				if agent == assignee:
					# the agent is already set as an assignee
					return

		assign({"assign_to": [agent], "doctype": self.doctype, "name": self.name}, ignore_permissions=True)

	def share_with_agent(self, agent):
		if not agent:
			return

		docshares = frappe.get_all(
			"DocShare",
			filters={"share_name": self.name, "share_doctype": self.doctype},
			fields=["name", "user"],
		)

		shared_with = [d.user for d in docshares] + [agent]

		for user in shared_with:
			if user == agent and not frappe.db.exists(
				"DocShare",
				{"user": agent, "share_name": self.name, "share_doctype": self.doctype},
			):
				frappe.share.add_docshare(
					self.doctype,
					self.name,
					agent,
					write=1,
					flags={"ignore_share_permission": True},
				)
			elif user != agent:
				frappe.share.remove(
					self.doctype,
					self.name,
					user,
					flags={"ignore_share_permission": True, "ignore_permissions": True},
				)

	def before_insert(self):
		self.contact_doc = None
		if frappe.db.get_single_value("CRM Settings", "auto_creation_of_contact"):
			if self.utm_source == "Existing Customer" and self.customer:
				contact = frappe.db.get_value(
					"Dynamic Link",
					{"link_doctype": "Customer", "parenttype": "Contact", "link_name": self.customer},
					"parent",
				)
				if contact:
					self.contact_doc = frappe.get_doc("Contact", contact)
					return
			self.contact_doc = self.create_contact()

		# leads created by email inbox only have the full name set
		if self.lead_name and not any([self.first_name, self.middle_name, self.last_name]):
			self.first_name, self.middle_name, self.last_name = parse_full_name(self.lead_name)

	def after_insert(self):
		self.link_to_contact()
		if self.lead_owner:
			if self.lead_owner != frappe.session.user:
				self.share_with_agent(self.lead_owner)
			self.assign_agent(self.lead_owner)

	def on_update(self):
		self.update_prospect()

	def on_trash(self):
		frappe.db.set_value("Issue", {"lead": self.name}, "lead", None)
		delete_contact_and_address(self.doctype, self.name)
		self.remove_link_from_prospect()

	def set_full_name(self):
		if self.first_name:
			self.lead_name = " ".join(
				filter(None, [self.salutation, self.first_name, self.middle_name, self.last_name])
			)

	def set_lead_name(self):
		if not self.lead_name:
			# Check for leads being created through data import
			if not self.company_name and not self.email_id and not self.flags.ignore_mandatory:
				frappe.throw(_("A Lead requires either a person's name or an organization's name"))
			elif self.company_name:
				self.lead_name = self.company_name
			else:
				self.lead_name = self.email_id.split("@")[0]

	def set_title(self):
		self.title = self.company_name or self.lead_name

	def check_email_id_is_unique(self):
		if self.email_id:
			# validate email is unique
			if not frappe.db.get_single_value("CRM Settings", "allow_lead_duplication_based_on_emails"):
				duplicate_leads = frappe.get_all(
					"Lead", filters={"email_id": self.email_id, "name": ["!=", self.name]}
				)
				duplicate_leads = [
					frappe.bold(get_link_to_form("Lead", lead.name)) for lead in duplicate_leads
				]

				if duplicate_leads:
					frappe.throw(
						_("Email Address must be unique, it is already used in {0}").format(
							comma_and(duplicate_leads)
						),
						frappe.DuplicateEntryError,
					)

	def validate_email_id(self):
		if self.email_id:
			if not self.flags.ignore_email_validation:
				validate_email_address(self.email_id, throw=True)

			if self.email_id == self.lead_owner:
				frappe.throw(_("Lead Owner cannot be same as the Lead Email Address"))

	def link_to_contact(self):
		# update contact links
		if self.contact_doc:
			self.contact_doc.append(
				"links", {"link_doctype": "Lead", "link_name": self.name, "link_title": self.lead_name}
			)
			self.contact_doc.save()

	def update_prospect(self):
		lead_row_name = frappe.db.get_value("Prospect Lead", filters={"lead": self.name}, fieldname="name")
		if lead_row_name:
			lead_row = frappe.get_doc("Prospect Lead", lead_row_name)
			lead_row.update(
				{
					"lead_name": self.lead_name,
					"email": self.email_id,
					"mobile_no": self.mobile_no,
					"lead_owner": self.lead_owner,
					"status": self.status,
				}
			)
			lead_row.db_update()

	def remove_link_from_prospect(self):
		prospects = self.get_linked_prospects()

		for d in prospects:
			prospect = frappe.get_doc("Prospect", d.parent)
			if len(prospect.get("leads")) == 1:
				prospect.delete(ignore_permissions=True)
			else:
				to_remove = None
				for d in prospect.get("leads"):
					if d.lead == self.name:
						to_remove = d

				if to_remove:
					prospect.remove(to_remove)
					prospect.save(ignore_permissions=True)

	def get_linked_prospects(self):
		return frappe.get_all(
			"Prospect Lead",
			filters={"lead": self.name},
			fields=["parent"],
		)

	def has_customer(self):
		return frappe.db.get_value("Customer", {"lead_name": self.name})

	def has_opportunity(self):
		return frappe.db.get_value("Opportunity", {"party_name": self.name, "status": ["!=", "Lost"]})

	def has_quotation(self):
		return frappe.db.get_value(
			"Quotation", {"party_name": self.name, "docstatus": 1, "status": ["!=", "Lost"]}
		)

	def has_lost_quotation(self):
		return frappe.db.get_value("Quotation", {"party_name": self.name, "docstatus": 1, "status": "Lost"})

	@frappe.whitelist()
	def create_prospect_and_contact(self, data):
		data = frappe._dict(data)
		if data.create_contact:
			self.create_contact()

		if data.create_prospect:
			self.create_prospect(data.prospect_name)

	def create_contact(self):
		if not self.lead_name:
			self.set_full_name()
			self.set_lead_name()

		contact = frappe.new_doc("Contact")
		contact.update(
			{
				"first_name": self.first_name or self.lead_name,
				"last_name": self.last_name,
				"salutation": self.salutation,
				"gender": self.gender,
				"designation": self.job_title,
				"company_name": self.company_name,
			}
		)

		if self.email_id:
			contact.append("email_ids", {"email_id": self.email_id, "is_primary": 1})

		if self.phone:
			contact.append("phone_nos", {"phone": self.phone, "is_primary_phone": 1})

		if self.mobile_no:
			contact.append("phone_nos", {"phone": self.mobile_no, "is_primary_mobile_no": 1})

		contact.insert(ignore_permissions=True)
		contact.reload()  # load changes by hooks on contact

		return contact

	def create_prospect(self, company_name):
		try:
			prospect = frappe.new_doc("Prospect")

			prospect.company_name = company_name or self.company_name
			prospect.no_of_employees = self.no_of_employees
			prospect.industry = self.industry
			prospect.market_segment = self.market_segment
			prospect.annual_revenue = self.annual_revenue
			prospect.territory = self.territory
			prospect.fax = self.fax
			prospect.website = self.website
			prospect.prospect_owner = self.lead_owner
			prospect.company = self.company
			prospect.notes = self.notes

			prospect.append(
				"leads",
				{
					"lead": self.name,
					"lead_name": self.lead_name,
					"email": self.email_id,
					"mobile_no": self.mobile_no,
					"lead_owner": self.lead_owner,
					"status": self.status,
				},
			)
			prospect.flags.ignore_permissions = True
			prospect.flags.ignore_mandatory = True
			prospect.save()
		except frappe.DuplicateEntryError:
			frappe.throw(_("Prospect {0} already exists").format(company_name or self.company_name))

	# --- ROKCT platform SDK contract (ported from the standalone CRM Lead
	# controller): the api.crm.doc.* gateway methods read these statics.

	@staticmethod
	def get_non_filterable_fields():
		return ["converted"]

	@staticmethod
	def default_list_data():
		columns = [
			{
				"label": "Full Name",
				"type": "Data",
				"key": "lead_name",
				"width": "12rem",
			},
			{
				"label": "Organization",
				"type": "Data",
				"key": "company_name",
				"width": "10rem",
			},
			{
				"label": "Status",
				"type": "Link",
				"options": "Lead Status",
				"key": "status",
				"width": "8rem",
			},
			{
				"label": "Email",
				"type": "Data",
				"key": "email_id",
				"width": "12rem",
			},
			{
				"label": "Mobile No.",
				"type": "Data",
				"key": "mobile_no",
				"width": "11rem",
			},
			{
				"label": "Assigned To",
				"type": "Text",
				"key": "_assign",
				"width": "10rem",
			},
			{
				"label": "Last Modified",
				"type": "Datetime",
				"key": "modified",
				"width": "8rem",
			},
		]
		rows = [
			"name",
			"lead_name",
			"company_name",
			"status",
			"email_id",
			"mobile_no",
			"lead_owner",
			"first_name",
			"modified",
			"_assign",
			"image",
		]
		return {"columns": columns, "rows": rows}

	@staticmethod
	def default_kanban_settings():
		return {
			"column_field": "status",
			"title_field": "lead_name",
			"kanban_fields": '["company_name", "email_id", "mobile_no", "_assign", "modified"]',
		}


@frappe.whitelist()
def convert_to_deal(
	lead: str,
	doc=None,
	deal=None,
	existing_contact: str | None = None,
	existing_organization: str | None = None,
):
	"""Convert a Lead into an Opportunity (the platform 'deal'), carrying the
	standalone-CRM conversion semantics onto the ERPNext masters: the lead is
	marked converted, a Contact and a Prospect are found-or-created and the
	new Opportunity links back to both.

	Kept under its historic `api.crm.lead.convert_to_deal` cmd alias."""
	if not (doc and getattr(doc, "flags", None) and doc.flags.get("ignore_permissions")) and not frappe.has_permission(
		"Lead", "write", lead
	):
		frappe.throw(_("Not allowed to convert Lead to Deal"), frappe.PermissionError)

	lead_doc = frappe.get_doc("Lead", lead)
	if frappe.db.exists("Lead Status", "Qualified"):
		lead_doc.db_set("status", "Qualified")
	lead_doc.db_set("converted", 1)

	contact = existing_contact
	if not contact:
		contact = get_default_contact("Lead", lead_doc.name)
	if not contact:
		contact = lead_doc.create_contact().name

	organization = existing_organization
	if not organization and lead_doc.company_name:
		organization = frappe.db.exists("Prospect", {"company_name": lead_doc.company_name})
		if not organization:
			lead_doc.create_prospect(lead_doc.company_name)
			organization = frappe.db.exists("Prospect", {"company_name": lead_doc.company_name})

	opportunity = make_opportunity(lead_doc.name)
	opportunity.update(
		{
			"lead": lead_doc.name,
			"organization": organization,
			"contacts": [{"contact": contact, "is_primary": 1}] if contact else [],
		}
	)
	if not opportunity.company:
		opportunity.company = (
			frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)
	if deal:
		if isinstance(deal, str):
			deal = frappe.parse_json(deal)
		opportunity.update(deal)
	opportunity.flags.ignore_mandatory = True
	opportunity.insert(ignore_permissions=True)

	for user in lead_doc.get_assigned_users() or []:
		if user and user != opportunity.opportunity_owner:
			opportunity.assign_agent(user)

	return opportunity.name


@frappe.whitelist()
def make_customer(source_name, target_doc=None):
	return _make_customer(source_name, target_doc)


def _make_customer(source_name, target_doc=None, ignore_permissions=False):
	def set_missing_values(source, target):
		if source.company_name:
			target.customer_type = "Company"
			target.customer_name = source.company_name
		else:
			target.customer_type = "Individual"
			target.customer_name = source.lead_name

		if not target.customer_group:
			target.customer_group = frappe.db.get_default("Customer Group")

		address = get_default_address("Lead", source.name)
		contact = get_default_contact("Lead", source.name)
		if address:
			target.customer_primary_address = address
		if contact:
			target.customer_primary_contact = contact

	doclist = get_mapped_doc(
		"Lead",
		source_name,
		{
			"Lead": {
				"doctype": "Customer",
				"field_map": {
					"name": "lead_name",
					"company_name": "customer_name",
					"contact_no": "phone_1",
					"fax": "fax_1",
				},
				"field_no_map": ["disabled"],
			}
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)

	return doclist


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc(
		"Lead",
		source_name,
		{
			"Lead": {
				"doctype": "Opportunity",
				"field_map": {
					"doctype": "opportunity_from",
					"name": "party_name",
					"lead_name": "contact_display",
					"company_name": "customer_name",
					"email_id": "contact_email",
					"mobile_no": "contact_mobile",
					"lead_owner": "opportunity_owner",
					"notes": "notes",
				},
			}
		},
		target_doc,
		set_missing_values,
	)

	return target_doc


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		_set_missing_values(source, target)

	target_doc = get_mapped_doc(
		"Lead",
		source_name,
		{"Lead": {"doctype": "Quotation", "field_map": {"name": "party_name"}}},
		target_doc,
		set_missing_values,
	)

	target_doc.quotation_to = "Lead"
	target_doc.run_method("set_missing_values")
	target_doc.run_method("set_other_charges")
	target_doc.run_method("calculate_taxes_and_totals")

	return target_doc


def _set_missing_values(source, target):
	address = frappe.get_all(
		"Dynamic Link",
		{
			"link_doctype": source.doctype,
			"link_name": source.name,
			"parenttype": "Address",
		},
		["parent"],
		limit=1,
	)

	contact = frappe.get_all(
		"Dynamic Link",
		{
			"link_doctype": source.doctype,
			"link_name": source.name,
			"parenttype": "Contact",
		},
		["parent"],
		limit=1,
	)

	if address:
		target.customer_address = address[0].parent

	if contact:
		target.contact_person = contact[0].parent


@frappe.whitelist()
def get_lead_details(lead, posting_date=None, company=None, doctype=None):
	if not lead:
		return {}

	_party_mod = _erp_import("accounts.party")
	set_address_details = _party_mod.set_address_details

	out = frappe._dict()

	lead_doc = frappe.get_doc("Lead", lead)
	lead_doc.check_permission()
	lead = lead_doc

	out.update(
		{
			"territory": lead.territory,
			"customer_name": lead.company_name or lead.lead_name,
			"contact_display": " ".join(filter(None, [lead.lead_name])),
			"contact_email": lead.email_id,
			"contact_mobile": lead.mobile_no,
			"contact_phone": lead.phone,
		}
	)

	set_address_details(out, lead, "Lead", doctype=doctype, company=company)

	taxes_and_charges = set_taxes(
		None,
		"Lead",
		posting_date,
		company,
		billing_address=out.get("customer_address"),
		shipping_address=out.get("shipping_address_name"),
	)
	if taxes_and_charges:
		out["taxes_and_charges"] = taxes_and_charges

	return out


@frappe.whitelist()
def make_lead_from_communication(communication: str, ignore_communication_links: bool = False):
	"""raise a issue from email"""

	doc = frappe.get_doc("Communication", communication)
	lead_name = None
	if doc.sender:
		lead_name = frappe.db.get_value("Lead", {"email_id": doc.sender})
	if not lead_name and doc.phone_no:
		lead_name = frappe.db.get_value("Lead", {"mobile_no": doc.phone_no})
	if not lead_name:
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": doc.sender_full_name,
				"email_id": doc.sender,
				"mobile_no": doc.phone_no,
			}
		)
		lead.flags.ignore_mandatory = True
		lead.insert()

		lead_name = lead.name

	link_communication_to_document(doc, "Lead", lead_name, ignore_communication_links)
	return lead_name


def get_lead_with_phone_number(number):
	if not number:
		return

	leads = frappe.get_all(
		"Lead",
		or_filters={
			"phone": ["like", f"%{number}"],
			"whatsapp_no": ["like", f"%{number}"],
			"mobile_no": ["like", f"%{number}"],
		},
		limit=1,
		order_by="creation DESC",
	)

	lead = leads[0].name if leads else None

	return lead


@frappe.whitelist()
def add_lead_to_prospect(lead, prospect):
	prospect = frappe.get_doc("Prospect", prospect)
	prospect.append("leads", {"lead": lead})
	prospect.save()

	carry_forward_communication_and_comments = frappe.db.get_single_value(
		"CRM Settings", "carry_forward_communication_and_comments"
	)

	if carry_forward_communication_and_comments:
		copy_comments("Lead", lead, prospect)
		link_communications("Lead", lead, prospect)
	link_open_events("Lead", lead, prospect)

	frappe.msgprint(
		_("Lead {0} has been added to prospect {1}.").format(frappe.bold(lead), frappe.bold(prospect.name)),
		title=_("Lead -> Prospect"),
		indicator="green",
	)
