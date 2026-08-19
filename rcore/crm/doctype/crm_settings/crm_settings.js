// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// ROKCT: the upstream external-Frappe-CRM data-synchronization controls
// (allowed_users / enable_frappe_crm_data_synchronization) were dropped with
// the frappe_crm_api shim — this merged crm module IS the fleet CRM and the
// standalone frappe/crm app must never be installed alongside it.
frappe.ui.form.on("CRM Settings", {});
