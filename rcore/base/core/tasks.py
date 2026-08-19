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

import frappe
from frappe.utils import add_hours, now_datetime

def check_invoice_payments():
    if frappe.conf.get("app_role") != "tenant": return
    unpaid_invoices = frappe.get_all("Sales Invoice", filters={
        "docstatus": 1,
        "status": ["not in", ["Paid", "Draft", "Cancelled"]],
        "outstanding_amount": [">", 0]
    }, fields=["name", "customer", "outstanding_amount", "due_date"])

    for inv in unpaid_invoices:
        try:
            frappe.log_error(
                message=f"Outstanding Sales Invoice {inv.name} for Customer {inv.customer} requires payment. Outstanding: {inv.outstanding_amount}.",
                title="Invoice Payment Reminder"
            )
        except Exception as e:
            frappe.log_error(f"Failed payment check for {inv.name}: {e}", "Invoice Payment Check Error")

def check_protocol_99_sequences():
    if frappe.conf.get("app_role") != "tenant": return
    six_hours_ago = add_hours(now_datetime(), -6)
    active_releases = frappe.get_all("Legacy Vault", filters={
        "release_status": "Initiated",
        "release_initiated_at": ["<=", six_hours_ago]
    }, fields=["name", "owner", "will_document_url"])

    for release in active_releases:
        try:
            relationship = frappe.get_value("Legacy Relationship", {"parent": release.owner}, ["executor_details", "name"], as_dict=True)
            if relationship:
                frappe.db.set_value("Legacy Vault", release.name, "release_status", "Released")
                frappe.log_error(
                    message=f"Protocol 99 Timer Expired (6 Hours). Decrypting and releasing Vault package for owner {release.owner} to executor {relationship.executor_details}.",
                    title="Protocol 99 Vault Released"
                )
        except Exception as e:
            frappe.log_error(f"Protocol 99 execution failed for {release.name}: {e}")
    frappe.db.commit()

def purge_expired_idempotency_keys():
    """Daily scheduler job: drop Idempotency Key rows past their retention.

    Keys only need to outlive the sync engine's retry window; after
    KEY_RETENTION_DAYS they are dead weight, so the dedupe table stays small.
    """
    from frappe.utils import add_days
    from rcore.api.idempotency import KEY_RETENTION_DAYS

    if not frappe.db.table_exists("Idempotency Key"):
        return
    frappe.db.delete("Idempotency Key", {
        "creation": ["<", add_days(now_datetime(), -KEY_RETENTION_DAYS)]
    })
    frappe.db.commit()
