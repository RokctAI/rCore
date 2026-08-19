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
from frappe.utils import nowdate
import json
import random

def reset_monthly_token_usage():
    pass

def manage_daily_tenders():
    if frappe.conf.get("app_role") != "tenant": return
    try:
        from rcore.subscriptions.utils import get_subscription_details
        sub = get_subscription_details()
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
    from rcore.telemetry.utils import call_control
    settings = frappe.get_single("Synaptic Convergence Settings")
    filters = {"category": settings.main_procurement_category}
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
    if frappe.conf.get("app_role") != "tenant": return
    try:
        from rcore.subscriptions.utils import get_subscription_details
        sub = get_subscription_details()
        if not sub.get("enable_funding"): return
    except: return

    _fetch_and_upsert_neurotrophins("grants")
    _fetch_and_upsert_neurotrophins("equity")
    _delete_expired_funding()

def _fetch_and_upsert_neurotrophins(opp_type):
    from rcore.telemetry.utils import call_control
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

def pick_proactive_question():
    if frappe.conf.get("app_role") != "tenant": return
    questions = frappe.get_all("Question Bank", filters={"is_active": 1}, fields=["question", "category"])
    if not questions: return

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

def tag_engram_pillars(doc, method=None):
    text = ((doc.summary or "") + " " + (doc.content or "")).lower()
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
    if frappe.conf.get("app_role") != "tenant": return
    from frappe.utils import add_days
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
