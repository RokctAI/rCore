# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import random_string

from ..lead.lead import add_lead_to_prospect
from ..lead.test_lead import make_lead
# ROKCT: cross-module imports into the composed erp module are resolved from
# __name__ — the composer's app-name token must not appear in doctype-tree
# .py files (designer design_system.py precedent), and the erp SDK module
# composes as a sibling package of this crm module.
from importlib import import_module as _import_module


def _erp_import(path):
	"""Import '<app>.erp.<path>' relative to this module's composed app."""
	return _import_module(__name__.split(".crm.doctype.", 1)[0] + ".erp." + path)

_utils_mod = _erp_import("tests.utils")
ERPNextTestSuite = _utils_mod.ERPNextTestSuite


class TestProspect(ERPNextTestSuite):
	def test_add_lead_to_prospect_and_address_linking(self):
		company = "_Test Company"
		lead_doc = make_lead()
		address_doc = make_address(address_title=lead_doc.name)
		address_doc.append("links", {"link_doctype": lead_doc.doctype, "link_name": lead_doc.name})
		address_doc.save()
		prospect_doc = make_prospect(company=company, company_name=company)
		add_lead_to_prospect(lead_doc.name, prospect_doc.name)
		prospect_doc.reload()
		lead_exists_in_prosoect = False
		for rec in prospect_doc.get("leads"):
			if rec.lead == lead_doc.name:
				lead_exists_in_prosoect = True
		self.assertEqual(lead_exists_in_prosoect, True)
		address_doc.reload()
		self.assertEqual(address_doc.has_link("Prospect", prospect_doc.name), True)

	def test_make_customer_from_prospect(self):
		from ..prospect.prospect import make_customer as make_customer_from_prospect

		frappe.delete_doc_if_exists("Customer", "_Test Prospect")

		prospect = frappe.get_doc(
			{
				"doctype": "Prospect",
				"company_name": "_Test Prospect",
				"customer_group": "_Test Customer Group",
				"company": "_Test Company",
			}
		)
		prospect.insert()

		customer = make_customer_from_prospect("_Test Prospect")

		self.assertEqual(customer.doctype, "Customer")
		self.assertEqual(customer.company_name, "_Test Prospect")
		self.assertEqual(customer.customer_group, "_Test Customer Group")

		customer.company = "_Test Company"
		customer.insert()


def make_prospect(**args):
	args = frappe._dict(args)

	prospect_doc = frappe.get_doc(
		{
			"doctype": "Prospect",
			"company_name": args.company_name or f"_Test Company {random_string(3)}",
			"company": args.company,
		}
	).insert()

	return prospect_doc


def make_address(**args):
	args = frappe._dict(args)

	address_doc = frappe.get_doc(
		{
			"doctype": "Address",
			"address_title": args.address_title or "Address Title",
			"address_type": args.address_type or "Billing",
			"city": args.city or "Mumbai",
			"address_line1": args.address_line1 or "Vidya Vihar West",
			"country": args.country or "India",
		}
	).insert()

	return address_doc
