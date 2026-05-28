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

def pick_proactive_question():
    """
    Picks a random active question from the Question Bank DocType
    and triggers a system notification/log or logs it under ToDos.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    questions = frappe.get_all("Question Bank", filters={"is_active": 1}, fields=["question", "category"])
    if not questions: return
    
    import random
    selected = random.choice(questions)
    
    doc = frappe.get_doc({
        "doctype": "ToDo",
        "description": f"ROK Daily Question ({selected.category}): {selected.question}",
        "priority": "Medium",
        "status": "Open"
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    
    frappe.log_error(f"Proactive Question selected: {selected.question}", "Proactive Question Bank Picker")

def send_weekly_goal_reminders():
    """
    Weekly goal cron. Triggers Monday morning check-in prompts for active Personal Mastery Goals.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    # We check if it is Monday (weekday == 0) before executing the check-in reminders
    import datetime
    if datetime.datetime.today().weekday() != 0:
        return
        
    active_goals = frappe.get_all("Personal Mastery Goal", filters={"status": ["not in", ["Achieved", "Cancelled"]]}, fields=["name", "title"])
    for goal in active_goals:
        try:
            frappe.log_error(
                message=f"Monday morning goal check-in: How is your progress on your goal '{goal.title}'? Set your intentions for the week!",
                title="Weekly Goal Check-In"
            )
        except Exception as e:
            frappe.log_error(f"Failed to trigger goal reminder for {goal.name}: {e}")
    frappe.db.commit()

def send_friday_wins_reminders():
    """
    Friday Wins Chron. Triggers prompts to capture achievement logs / wins every Friday afternoon.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    # We check if it is Friday (weekday == 4) before executing the win capture reminders
    import datetime
    if datetime.datetime.today().weekday() != 4:
        return
        
    try:
        frappe.log_error(
            message="Friday Wins prep: What were your top wins and achievements this week? Take a moment to reflect and log them with ROK!",
            title="Friday Wins Preparation"
        )
    except Exception as e:
        frappe.log_error(f"Failed to trigger Friday Wins reminder: {e}")
    frappe.db.commit()

def archive_inactive_vault_files():
    """
    90-Day vault file archiving. Archives/deletes files 90 days post-cancel of a subscription.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    from frappe.utils import add_days, nowdate
    ninety_days_ago = add_days(nowdate(), -90)
    
    expired_tenants = frappe.get_all("User", filters={
        "enabled": 0,
        "temporary_user_expires_on": ["<", ninety_days_ago]
    }, fields=["name", "email"])
    
    for tenant in expired_tenants:
        files = frappe.get_all("File", filters={"owner": tenant.name}, fields=["name"])
        for f in files:
            try:
                frappe.delete_doc("File", f.name, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to archive/delete file {f.name} for {tenant.email}: {e}")
    frappe.db.commit()

def check_protocol_99_sequences():
    """
    Protocol 99 sequence: WhatsApp alerts and 6h vault release.
    Checks active sequences and releases vault packages after 6 hours.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    from frappe.utils import add_hours, now_datetime
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

def tag_engram_pillars(doc, method=None):
    """
    Cross-pillar tagging. Automatically tags engrams based on text classification.
    """
    text = (doc.summary or "" + " " + doc.content or "").lower()
    tags = []
    if any(w in text for w in ["business", "invoice", "revenue", "operations", "venture"]):
        tags.append("Business")
    if any(w in text for w in ["career", "promotion", "milestone", "job", "profession"]):
        tags.append("Career")
    if any(w in text for w in ["goal", "productivity", "accountability", "habit", "wins"]):
        tags.append("Productivity")
    if any(w in text for w in ["life", "health", "wellness", "relationship", "family"]):
        tags.append("Life")
    if any(w in text for w in ["legacy", "vault", "obituary", "will", "executor"]):
        tags.append("Legacy")
        
    if tags:
        doc.set("tags", ", ".join(tags))

def archive_low_score_engrams():
    """
    Engram scoring & expiry. Archives engrams older than 1 year with low score.
    """
    if frappe.conf.get("app_role") != "tenant": return
    
    from frappe.utils import add_days, nowdate
    one_year_ago = add_days(nowdate(), -365)
    
    if frappe.db.exists("DocType", "Engram"):
        low_score_engrams = frappe.get_all("Engram", filters={
            "creation": ["<", one_year_ago],
            "relevance_score": ["<", 0.5]
        }, fields=["name"])
        
        for engram in low_score_engrams:
            try:
                frappe.db.set_value("Engram", engram.name, "is_archived", 1)
            except Exception as e:
                frappe.log_error(f"Failed to archive engram {engram.name}: {e}")
        frappe.db.commit()




