# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, add_days, getdate, nowdate, get_datetime
import json
from rcore.utils.common import call_control

def reset_monthly_token_usage():
    if frappe.conf.get("app_role") != "tenant": return
    today = nowdate()
    thirty_days_ago = add_days(today, -30)
    trackers_to_reset = frappe.get_all("Token Usage Tracker", filters={"period_start_date": ("<=", thirty_days_ago)}, fields=["name"])
    for item in trackers_to_reset:
        try:
            tracker = frappe.get_doc("Token Usage Tracker", item.name)
            tracker.current_period_usage = 0
            tracker.period_start_date = today
            tracker.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to reset token tracker: {e}", "Token Usage Job Failed")
    frappe.db.commit()

def update_storage_usage():
    if frappe.conf.get("app_role") != "tenant": return
    try:
        total_size_bytes = frappe.db.sql("SELECT SUM(file_size) FROM `tabFile`")[0][0] or 0
        total_size_mb = total_size_bytes / (1024 * 1024)
        storage_tracker = frappe.get_doc("Storage Tracker")
        storage_tracker.current_storage_usage_mb = total_size_mb
        storage_tracker.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Storage usage calculation failed: {e}", "Storage Usage Job Failed")

def disable_expired_support_users():
    if frappe.conf.get("app_role") != "tenant": return
    expired_users = frappe.get_all("User", filters={"enabled": 1, "temporary_user_expires_on": ["<", now_datetime()]}, fields=["name", "email"])
    for user_info in expired_users:
        try:
            user = frappe.get_doc("User", user_info.name)
            user.enabled = 0
            user.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Failed to disable expired user {user_info.email}: {e}")

# ------------------------------------------------------------------------------
# Daily Tender/Funding Sync (Tenant side only)
# ------------------------------------------------------------------------------

def manage_daily_tenders():
    """
    Fetches new tenders (Stimuli) from the control panel.
    """
    if frappe.conf.get("app_role") != "tenant": return
    try:
        from rcore.utils.subscription_checker import get_cached_subscription_details
        sub = get_cached_subscription_details()
        if not sub.get("enable_tenders"): return
        
        allowed_country = sub.get("tender_country")
        default_company = frappe.get_single("Global Defaults").default_company
        if not default_company: return
        
        company_country = frappe.db.get_value("Company", default_company, "country")
        if company_country != allowed_country: return
    except: return

    _fetch_and_upsert_stimuli()
    _delete_expired_stimuli()

def _fetch_and_upsert_stimuli():
    settings = frappe.get_single("Synaptic Convergence Settings")
    filters = {"category": settings.main_procurement_category}
    
    # Call the NEW consolidated API on control
    relevant_tenders = call_control("tenders.get_relevant_tenders", {"filters": json.dumps(filters)})
    if not relevant_tenders: return

    for tender in relevant_tenders:
        try:
            ocid = tender.get("slug") or tender.get("tender_number")
            if not ocid: continue

            existing = frappe.db.get_value("Stimulus", {"ocid": ocid}, "name")
            doc_data = {
                "title": tender.get("title"),
                "status": tender.get("status"),
                "published_date": tender.get("date_published"),
                "stimulus_end_date": tender.get("closing_date"),
                "description": tender.get("category"),
                "organ_of_state": tender.get("institution"),
                "province": tender.get("province"),
                "custom_workflow_json": json.dumps(tender)
            }

            if not existing:
                doc = frappe.new_doc("Stimulus")
                doc.ocid = ocid
                doc.update(doc_data)
                doc.insert(ignore_permissions=True)
            else:
                frappe.db.set_value("Stimulus", existing, doc_data)
        except Exception as e:
            frappe.log_error(f"Stimulus processing failed: {e}", "Tender Sync Error")
    frappe.db.commit()

def _delete_expired_stimuli():
    expired = frappe.get_all("Stimulus", filters={"stimulus_end_date": ["<", nowdate()]}, fields=["name"])
    for s in expired:
        frappe.delete_doc("Stimulus", s.name, ignore_permissions=True, force=True)
    frappe.db.commit()

def manage_daily_funding():
    """
    Fetches new Grants and Equity opportunities (Neurotrophins) from the control panel.
    """
    if frappe.conf.get("app_role") != "tenant": return
    try:
        from rcore.utils.subscription_checker import get_cached_subscription_details
        sub = get_cached_subscription_details()
        if not sub.get("enable_funding"): return
    except: return

    print("Running Daily Funding Management Job on tenant...")
    # Fetch Grants
    _fetch_and_upsert_neurotrophins("grants")
    # Fetch Equity
    _fetch_and_upsert_neurotrophins("equity")
    
    _delete_expired_funding()

def _fetch_and_upsert_neurotrophins(opp_type):
    endpoint = f"tenders.get_relevant_{opp_type}"
    opportunities = call_control(endpoint, {"filters": "{}"})
    if not opportunities: return

    for opp in opportunities:
        try:
            slug = opp.get("slug")
            if not slug: continue

            existing = frappe.db.get_value("Neurotrophin", {"slug": slug}, "name")
            doc_data = {
                "title": opp.get("title"),
                "brief": opp.get("focus_area") or opp.get("industry") or "",
                "deadline": opp.get("deadline") or opp.get("closing_date"),
                "organization": opp.get("organization") or opp.get("institution"),
                "status": "Active",
                "opportunity_type": opp_type.title(),
                "raw_json": json.dumps(opp)
            }

            if not existing:
                doc = frappe.new_doc("Neurotrophin")
                doc.slug = slug
                doc.update(doc_data)
                doc.insert(ignore_permissions=True)
            else:
                frappe.db.set_value("Neurotrophin", existing, doc_data)
        except Exception as e:
            frappe.log_error(f"Neurotrophin sync failed: {e}", "Funding Sync Error")
    frappe.db.commit()

def _delete_expired_funding():
    expired = frappe.get_all("Neurotrophin", filters={"deadline": ["<", nowdate()]}, fields=["name"])
    for f in expired:
        frappe.delete_doc("Neurotrophin", f.name, ignore_permissions=True, force=True)
    frappe.db.commit()

def check_invoice_payments():
    """
    Automated payment reminders. Checks all unpaid and overdue Sales Invoices
    and triggers reminders/system logs.
    """
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

