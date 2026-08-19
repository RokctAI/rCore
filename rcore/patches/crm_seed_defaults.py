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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Seed the CRM module's required master data.

The Lead/Deal controllers hard-require at least one Open status of each
kind (validate_status), and the doctype permissions reference the Sales
Manager / Sales User roles. Ported from the upstream CRM app's install.py
defaults; every step is idempotent.

Note: Frappe marks all patches as completed (without running them) when the
host app is installed fresh, so on a brand-new site this seed must be run
once by hand or by the host's own install hook:
    bench --site <site> execute <app>.patches.crm_seed_defaults.execute
On migrate-based rollouts (an existing host composing this module in) it
runs automatically.
"""

import frappe

SEEDED_DOCTYPES = (
	"lead_status",
	"deal_status",
	"communication_status",
	"lead_source",
	"opportunity_lost_reason",
)

LEAD_STATUSES = {
	# standalone-CRM pipeline defaults
	"New": {"color": "gray", "type": "Open", "position": 1},
	"Contacted": {"color": "orange", "type": "Ongoing", "position": 2},
	"Nurture": {"color": "blue", "type": "Ongoing", "position": 3},
	"Qualified": {"color": "green", "type": "Won", "position": 4},
	"Converted": {"color": "teal", "type": "Won", "position": 5},
	"Unqualified": {"color": "red", "type": "Lost", "position": 6},
	"Junk": {"color": "purple", "type": "Lost", "position": 7},
	# ERPNext Lead status Select values (erp code string-matches these)
	"Lead": {"color": "gray", "type": "Open", "position": 8},
	"Open": {"color": "gray", "type": "Open", "position": 9},
	"Replied": {"color": "orange", "type": "Ongoing", "position": 10},
	"Opportunity": {"color": "blue", "type": "Ongoing", "position": 11},
	"Quotation": {"color": "blue", "type": "Ongoing", "position": 12},
	"Lost Quotation": {"color": "red", "type": "Lost", "position": 13},
	"Interested": {"color": "orange", "type": "Ongoing", "position": 14},
	"Do Not Contact": {"color": "red", "type": "Lost", "position": 15},
}

DEAL_STATUSES = {
	# standalone-CRM pipeline defaults
	"Qualification": {"color": "gray", "type": "Open", "probability": 10, "position": 1},
	"Demo/Making": {"color": "orange", "type": "Ongoing", "probability": 25, "position": 2},
	"Proposal/Quotation": {"color": "blue", "type": "Ongoing", "probability": 50, "position": 3},
	"Negotiation": {"color": "yellow", "type": "Ongoing", "probability": 70, "position": 4},
	"Ready to Close": {"color": "purple", "type": "Ongoing", "probability": 90, "position": 5},
	"Won": {"color": "green", "type": "Won", "probability": 100, "position": 6},
	"Lost": {"color": "red", "type": "Lost", "probability": 0, "position": 7},
	# ERPNext Opportunity status Select values (erp code string-matches these)
	"Open": {"color": "gray", "type": "Open", "probability": 10, "position": 8},
	"Quotation": {"color": "blue", "type": "Ongoing", "probability": 50, "position": 9},
	"Converted": {"color": "green", "type": "Won", "probability": 100, "position": 10},
	"Replied": {"color": "orange", "type": "Ongoing", "probability": 25, "position": 11},
	"Closed": {"color": "green", "type": "Won", "probability": 100, "position": 12},
}

COMMUNICATION_STATUSES = ["Open", "Replied"]

LEAD_SOURCES = [
	"Email",
	"Existing Customer",
	"Reference",
	"Advertisement",
	"Cold Calling",
	"Exhibition",
	"Supplier Reference",
	"Mass Mailing",
	"Customer's Vendor",
	"Campaign",
	"Walk In",
	"Website",
]

LOST_REASONS = [
	{"reason": "Pricing", "description": "The prospect found the pricing to be too high or not competitive."},
	{"reason": "Competition", "description": "The prospect chose a competitor's product or service."},
	{
		"reason": "Budget Constraints",
		"description": "The prospect did not have the budget to proceed with the purchase.",
	},
	{
		"reason": "Missing Features",
		"description": "The prospect felt that the product or service was missing key features they needed.",
	},
	{
		"reason": "Long Sales Cycle",
		"description": "The sales process took too long, leading to loss of interest.",
	},
	{
		"reason": "No Decision-Maker",
		"description": "The prospect was not the decision-maker and could not proceed.",
	},
	{"reason": "Unresponsive Prospect", "description": "The prospect did not respond to follow-ups."},
	{"reason": "Poor Fit", "description": "The prospect was not a good fit for the product or service."},
	{"reason": "Other", "description": ""},
]

ROLES = ["Sales Manager", "Sales User"]


def execute():
	# Make sure the seeded doctypes exist even when this patch is scheduled
	# pre-model-sync (compose registers it in the host's patches.txt, whose
	# section placement depends on the host file).
	for doctype in SEEDED_DOCTYPES:
		frappe.reload_doc("crm", "doctype", doctype)

	add_roles()
	add_lead_statuses()
	add_deal_statuses()
	add_communication_statuses()
	add_lead_sources()
	add_lost_reasons()


def add_roles():
	for role in ROLES:
		if frappe.db.exists("Role", role):
			continue
		doc = frappe.new_doc("Role")
		doc.role_name = role
		doc.desk_access = 1
		doc.insert(ignore_permissions=True)


def add_lead_statuses():
	for status, config in LEAD_STATUSES.items():
		if frappe.db.exists("Lead Status", status):
			continue
		doc = frappe.new_doc("Lead Status")
		doc.lead_status = status
		doc.color = config["color"]
		doc.type = config["type"]
		doc.position = config["position"]
		doc.insert(ignore_permissions=True)


def add_deal_statuses():
	for status, config in DEAL_STATUSES.items():
		if frappe.db.exists("Deal Status", status):
			continue
		doc = frappe.new_doc("Deal Status")
		doc.deal_status = status
		doc.color = config["color"]
		doc.type = config["type"]
		doc.probability = config["probability"]
		doc.position = config["position"]
		doc.insert(ignore_permissions=True)


def add_communication_statuses():
	for status in COMMUNICATION_STATUSES:
		if frappe.db.exists("Communication Status", status):
			continue
		doc = frappe.new_doc("Communication Status")
		doc.status = status
		doc.insert(ignore_permissions=True)


def add_lead_sources():
	for source in LEAD_SOURCES:
		if frappe.db.exists("Lead Source", source):
			continue
		doc = frappe.new_doc("Lead Source")
		doc.source_name = source
		doc.insert(ignore_permissions=True)


def add_lost_reasons():
	for reason in LOST_REASONS:
		if frappe.db.exists("Opportunity Lost Reason", reason["reason"]):
			continue
		doc = frappe.new_doc("Opportunity Lost Reason")
		doc.lost_reason = reason["reason"]
		doc.description = reason["description"]
		doc.insert(ignore_permissions=True)
