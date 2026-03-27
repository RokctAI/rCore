# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, add_days, getdate, nowdate, get_datetime
from rcore.tenant.utils import send_tenant_email
import re
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def reset_monthly_token_usage():
    """
    Checks all token usage trackers and resets the count if the 30-day
    period has elapsed. Runs as a daily background job.
    """
    if frappe.conf.get("app_role") != "tenant":
        return

    frappe.log("Running Daily Token Usage Reset Job...", "Token Usage Job")

    today = nowdate()
    thirty_days_ago = add_days(today, -30)

    trackers_to_reset = frappe.get_all(
        "Token Usage Tracker",
        filters={"period_start_date": ("<=", thirty_days_ago)},
        fields=["name"]
    )

    if not trackers_to_reset:
        frappe.log("No token trackers due for a reset.", "Token Usage Job")
        return

    frappe.log(
        f"Found {
            len(trackers_to_reset)} token trackers to reset.",
        "Token Usage Job")

    for item in trackers_to_reset:
        try:
            tracker = frappe.get_doc("Token Usage Tracker", item.name)
            tracker.current_period_usage = 0
            tracker.period_start_date = today
            tracker.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                f"Failed to reset token tracker for {item.name}: {e}",
                "Token Usage Job Failed"
            )

    frappe.db.commit()
    frappe.log("Token Usage Reset Job Complete.", "Token Usage Job")


def update_storage_usage():
    """
    Calculates the total storage usage for the site and updates the
    Storage Tracker singleton. Runs as a daily background job.
    """
    if frappe.conf.get("app_role") != "tenant":
        return

    frappe.log(
        "Running Daily Storage Usage Calculation Job...",
        "Storage Usage Job")

    try:
        # Calculate total file size in bytes from the database
        total_size_bytes = frappe.db.sql(
            "SELECT SUM(file_size) FROM `tabFile`")[0][0] or 0

        # Convert bytes to megabytes for storing
        total_size_mb = total_size_bytes / (1024 * 1024)

        # Update the singleton doctype
        storage_tracker = frappe.get_doc("Storage Tracker")
        storage_tracker.current_storage_usage_mb = total_size_mb
        storage_tracker.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.log(
            f"Successfully updated storage usage to {
                total_size_mb:.2f} MB.",
            "Storage Usage Job")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"An unexpected error occurred during storage usage calculation: {e}\\n{
                frappe.get_traceback()}",
            "Storage Usage Job Failed")


def disable_expired_support_users():
    """
    Find and disable temporary support users whose access has expired.
    This is run daily by the scheduler on tenant sites.
    """
    if frappe.conf.get("app_role") != "tenant":
        return

    print("Running Daily Expired Support User Cleanup Job...")

    expired_users = frappe.get_all(
        "User", filters={
            "enabled": 1, "temporary_user_expires_on": [
                "<", now_datetime()]}, fields=[
            "name", "email", "first_name"])

    if not expired_users:
        print("No expired support users to disable.")
        return

    print(f"Found {len(expired_users)} expired support users to disable...")

    # Get all system managers to notify them
    system_managers = frappe.get_all(
        "User",
        filters={
            "role_profile_name": "System Manager",
            "enabled": 1},
        fields=["email"])
    recipients = [user.email for user in system_managers]

    if not recipients:
        print("No System Managers found to notify.")
        # Still proceed to disable the user, but log it
        frappe.log_error(
            "No System Managers found to notify about expired support user.",
            "Support User Expiration")

    for user_info in expired_users:
        try:
            user = frappe.get_doc("User", user_info.name)
            user.enabled = 0
            user.save(ignore_permissions=True)

            frappe.db.commit()
            print(f"  - Disabled expired support user: {user.email}")

            if recipients:
                email_context = {
                    "support_user_name": user.full_name,
                    "support_user_email": user.email,
                    "disabled_at": now_datetime().strftime("%Y-%m-%d %H:%M:%S")
                }
                send_tenant_email(
                    recipients=recipients,
                    template="Support User Expired",
                    args=email_context,
                    now=True
                )
                print(
                    f"  - Sent expiration notification to System Managers for {user.email}")

        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to disable expired support user {
                    user_info.email}")

    print("Expired Support User Cleanup Job Complete.")


# ------------------------------------------------------------------------------
# Daily Job (General)
# ------------------------------------------------------------------------------


def manage_daily_tenders():
    """
    Fetches new tenders, updates existing ones, and removes expired tenders.
    This function is now split based on the site's role.
    """
    if frappe.conf.get("app_role") == "control":
        _fetch_and_cache_tenders_on_control()
    else:  # Tenant site
        # Perform access checks before running the job
        try:
            from rcore.utils.subscription_checker import get_cached_subscription_details

            subscription_details = get_cached_subscription_details()

            if not subscription_details.get("enable_tenders"):
                print(
                    "Tender feature is not enabled for this subscription plan. Skipping job.")
                return

            allowed_country = subscription_details.get("tender_country")
            if not allowed_country:
                print("Tender country not configured on control panel. Skipping job.")
                return

            default_company = frappe.get_single(
                "Global Defaults").default_company
            if not default_company:
                print("No default company set for this site. Skipping tender job.")
                return

            company_country = frappe.db.get_value(
                "Company", default_company, "country")
            if company_country != allowed_country:
                print(
                    f"Company country '{company_country}' does not match the allowed tender country '{allowed_country}'. Skipping job.")
                return

        except Exception as e:
            frappe.log_error(
                f"Failed to verify tender access permissions: {e}",
                "Tender Access Check Failed")
            return

        print("Running Daily Tender Management Job on tenant...")
        _fetch_and_upsert_stimuli()
        _delete_expired_stimuli()
        print("Daily Tender Management Job Complete on tenant.")


def _fetch_monorepo_via_ssh(repo_path, target_root):
    """
    (Helper) Uses SSH to fetch a specific directory from the Monorepo
    without a full clone.
    """
    repo_url = "git@github.com:RokctAI/Monorepo.git"
    print(f"Fetching {repo_path} from {repo_url} via SSH...")
    
    try:
        # 1. Create a temporary clone (shallow and no checkout)
        temp_repo = tempfile.mkdtemp()
        subprocess.run(
            ["git", "clone", "--depth", "1", "--no-checkout", repo_url, "."],
            cwd=temp_repo, check=True, capture_output=True
        )
        
        # 2. Checkout only the requested path
        subprocess.run(
            ["git", "checkout", "main", "--", repo_path],
            cwd=temp_repo, check=True, capture_output=True
        )
        
        # 3. Move the fetched directory to our target root
        src_path = Path(temp_repo) / repo_path
        if src_path.exists():
            if target_root.exists():
                shutil.rmtree(target_root)
            shutil.copytree(src_path, target_root)
            return True
            
    except subprocess.CalledProcessError as e:
        frappe.log_error(f"SSH Fetch Failed: {e.stderr.decode()}", "Monorepo SSH Sync Error")
    except Exception as e:
        frappe.log_error(f"Unexpected error during SSH sync: {e}", "Monorepo SSH Sync Error")
    finally:
        if 'temp_repo' in locals() and os.path.exists(temp_repo):
            shutil.rmtree(temp_repo)
            
    return False


def _fetch_and_cache_tenders_on_control():
    """
    (Control Panel only) Pivoted: Now fetches from Monorepo via SSH.
    """
    print("Syncing tenders from Monorepo via SSH...")
    
    # Use a temporary directory for the sync session
    with tempfile.TemporaryDirectory() as sync_dir:
        sync_path = Path(sync_dir) / "tenders"
        if not _fetch_monorepo_via_ssh("opportunities/03_tenders", sync_path):
            return

        total_cached = 0
        for md_file in sync_path.glob("*.md"):
            if md_file.name == "template.md":
                continue
                
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Use regex to extract data into the OCDS-like structure control expects
                ocid_match = re.search(r'-\s+\*\*Tender Number\*\*:\s*(.+)$', content, re.M)
                title_match = re.search(r'^#\s+Tender Opportunity:\s*(.+)$', content, re.M)
                institution_match = re.search(r'-\s+\*\*Institution\*\*:\s*(.+)$', content, re.M)
                closing_match = re.search(r'-\s+\*\*Closing Date\*\*:\s*(.+)$', content, re.M)
                
                # --- AI Checklist Parsing ---
                checklist = []
                checklist_section = re.search(r'## AI Checklist \(Jules\)\s*(.*?)(?:\n##|$)', content, re.S)
                if checklist_section:
                    items = re.findall(r'-\s+\[\s*\]\s*(.*?)\|\s*(\d+)', checklist_section.group(1))
                    for subject, offset in items:
                        checklist.append({
                            "subject": subject.strip(),
                            "due_date_offset_days": int(offset)
                        })

                if not ocid_match: continue
                
                # --- Freshness Guard ---
                if closing_match:
                    try:
                        date_part = closing_match.group(1).split(" - ")[0].strip()
                        closing_datetime = get_datetime(date_part)
                        if closing_datetime < now_datetime():
                            continue
                    except: pass
                
                ocid = ocid_match.group(1).strip()
                release = {
                    "ocid": ocid,
                    "date": now_datetime().isoformat(),
                    "tender": {
                        "title": title_match.group(1).strip() if title_match else "Unknown",
                        "procuringEntity": {"name": institution_match.group(1).strip() if institution_match else "Unknown"},
                        "tenderPeriod": {"endDate": closing_match.group(1).strip() if closing_match else ""},
                        "custom_tasks": checklist
                    }
                }
                
                release_json = json.dumps(release)
                
                # Deduplicate by OCID: Find existing cache entry containing this OCID
                # Since 'ocid' is a key in the 'data' JSON blob, we query by data content
                existing_cache = frappe.db.sql("""
                    SELECT name, data FROM `tabRaw Tender Cache` 
                    WHERE JSON_EXTRACT(data, '$.ocid') = %s
                """, ocid, as_dict=1)

                if not existing_cache:
                    frappe.get_doc({
                        "doctype": "Raw Tender Cache",
                        "retrieved_on": now_datetime(),
                        "data": release_json
                    }).insert(ignore_permissions=True)
                    total_cached += 1
                else:
                    # Update if content has changed
                    if existing_cache[0].data != release_json:
                        frappe.db.set_value("Raw Tender Cache", existing_cache[0].name, "data", release_json)
                        print(f"Updated cache record for OCID: {ocid}")
                    
            except Exception as e:
                frappe.log_error(f"Failed to process fetched tender {md_file.name}: {e}", "Tender Sync Error")

        frappe.db.commit()
        print(f"Successfully synced {total_cached} tenders from Monorepo.")


def _format_datetime_str(datetime_obj):
    """
    Formats a datetime object into a string ('YYYY-MM-DD HH:MM:SS')
    for database insertion, stripping any timezone info.
    """
    if not datetime_obj:
        return None
    return datetime_obj.strftime('%Y-%m-%d %H:%M:%S')


def _fetch_and_upsert_stimuli():
    """
    Fetches relevant stimuli from the control panel and upserts them locally.
    """
    try:
        # Fetch tenant-specific filters from Synaptic Convergence Settings
        stimulus_settings = frappe.get_single("Synaptic Convergence Settings")
        filters = {
            "mainProcurementCategory": stimulus_settings.main_procurement_category}

        relevant_tenders = frappe.call(
            "control.control.api.tenders.get_relevant_tenders",
            filters=json.dumps(filters))

        if not relevant_tenders:
            print("No new relevant tenders found.")
            return

        total_upserted = 0
        for release in relevant_tenders:
            try:
                tender_data = release.get("tender", {})
                if not tender_data or not release.get("ocid"):
                    continue

                # Check for existing Stimulus by OCID
                existing_stimulus = frappe.db.get_value("Stimulus", {"ocid": release.get("ocid")}, "name")
                
                category = _get_linked_doc_name(
                    "Stimulus Category", tender_data.get("mainProcurementCategory"))
                organ_of_state = _get_linked_doc_name(
                    "Organ of State", tender_data.get(
                        "procuringEntity", {}).get("name"))
                stimulus_type = _get_linked_doc_name(
                    "Stimulus Type", tender_data.get("procurementMethod"))
                province = _find_province_from_parties(release)

                stimulus_doc_data = {
                    "title": tender_data.get("title"),
                    "status": tender_data.get("status"),
                    "publisher_name": release.get(
                        "publisher",
                        {}).get("name"),
                    "published_date": _format_datetime_str(
                        get_datetime(
                            release.get("date"))),
                    "stimulus_start_date": _format_datetime_str(
                        get_datetime(
                            tender_data.get(
                                "tenderPeriod",
                                {}).get("startDate"))),
                    "stimulus_end_date": _format_datetime_str(
                        get_datetime(
                            tender_data.get(
                                "tenderPeriod",
                                {}).get("endDate"))),
                    "value_amount": tender_data.get(
                        "value",
                        {}).get("amount"),
                    "value_currency": tender_data.get(
                        "value",
                        {}).get("currency"),
                    "description": tender_data.get("description"),
                    "stimulus_category": category,
                    "organ_of_state": organ_of_state,
                    "stimulus_type": stimulus_type,
                    "province": province,
                    "esubmission": 1 if "electronicSubmission" in tender_data.get(
                        "submissionMethod",
                        []) else 0,
                    "custom_workflow_json": json.dumps(tender_data.get("custom_tasks", []))
                }

                if not existing_stimulus:
                    doc = frappe.new_doc("Stimulus")
                    doc.ocid = release.get("ocid")
                    doc.update(stimulus_doc_data)
                    doc.insert(ignore_permissions=True)
                    total_upserted += 1
                else:
                    # Update existing stimulus with new data
                    frappe.db.set_value("Stimulus", existing_stimulus, stimulus_doc_data)
                    print(f"Updated Stimulus for OCID: {release.get('ocid')}")
                    total_upserted += 1

            except Exception as e:
                frappe.log_error(
                    f"Failed to process release {
                        release.get('ocid')}: {e}",
                    "Tender Release Processing Failed")

        frappe.db.commit()
        print(f"Successfully created {total_upserted} new Stimuli.")

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Tender Upsert Failed")


def _get_linked_doc_name(doctype, value):
    if not value:
        return None

    doctype_field_map = {
        "Stimulus Category": "category_name",
        "Organ of State": "organ_name",
        "Province": "province_name",
        "Stimulus Type": "stimulus_type_name",
    }
    fieldname = doctype_field_map.get(doctype)
    if not fieldname:
        frappe.log_error(
            f"No field mapping found for Doctype {doctype}",
            "Stimulus Linking Error")
        return None
    try:
        return frappe.db.get_value(doctype, {fieldname: value}, "name")
    except Exception:
        frappe.log_error(
            f"Could not find matching document for {doctype} with value '{value}'",
            "Stimulus Linking Warning")
        return None


def _find_province_from_parties(release):
    if not release or not release.get("parties"):
        return None

    buyer = release.get("buyer", {})
    buyer_name = buyer.get("name")
    if not buyer_name:
        return None

    for party in release.get("parties", []):
        if party.get("name") == buyer_name:
            region = party.get("address", {}).get("region")
            if region:
                return _get_linked_doc_name("Province", region)
    return None


def _delete_expired_stimuli():
    from frappe.utils import getdate, nowdate
    try:
        today = getdate(nowdate())
        expired_stimuli = frappe.get_all(
            "Stimulus", filters={
                "stimulus_end_date": [
                    "<", today]}, fields=["name"])

        if not expired_stimuli:
            print("No expired stimuli to delete.")
            return

        for stimulus in expired_stimuli:
            frappe.delete_doc(
                "Stimulus",
                stimulus.name,
                ignore_permissions=True,
                force=True)

        frappe.db.commit()
        print(f"Successfully deleted {len(expired_stimuli)} expired stimuli.")
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Expired Stimulus Deletion Failed")


def manage_daily_funding():
    """
    Fetches new funding opportunities, updates existing ones, and removes expired ones.
    """
    if frappe.conf.get("app_role") == "control":
        _fetch_and_cache_funding_on_control()
    else:  # Tenant site
        try:
            from rcore.utils.subscription_checker import get_cached_subscription_details
            subscription_details = get_cached_subscription_details()
            if not subscription_details.get("enable_funding"):
                print(
                    "Funding feature is not enabled for this subscription plan. Skipping job.")
                return
        except Exception as e:
            frappe.log_error(
                f"Failed to verify funding access permissions: {e}",
                "Funding Access Check Failed")
            return

        print("Running Daily Funding Management Job on tenant...")
        # Since there is no API, we will just process the cache
        _process_funding_cache()
        _delete_expired_funding()
        print("Daily Funding Management Job Complete on tenant.")


def _fetch_and_cache_funding_on_control():
    """
    (Control Panel only) Pivoted: Now synchronizes from curated Monorepo grants via SSH.
    """
    print("Syncing funding opportunities from Monorepo via SSH...")
    
    with tempfile.TemporaryDirectory() as sync_dir:
        sync_path = Path(sync_dir) / "grants"
        if not _fetch_monorepo_via_ssh("opportunities/02_grants", sync_path):
            return

        total_cached = 0
        for md_file in sync_path.glob("*.md"):
            if md_file.name == "grant_template.md":
                continue
                
            try:
                with open(md_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # --- Freshness Guard ---
                deadline_match = re.search(r'-\s+\*\*Deadline\*\*:\s*(\d{4}-\d{2}-\d{2})', content)
                if deadline_match:
                    try:
                        deadline_date = get_datetime(deadline_match.group(1))
                        if deadline_date < now_datetime():
                            continue
                    except: pass

                # Simple content change check
                if not frappe.db.exists("Raw Neurotrophin Cache", {"data": content}):
                    frappe.get_doc({
                        "doctype": "Raw Neurotrophin Cache",
                        "retrieved_on": now_datetime(),
                        "data": content
                    }).insert(ignore_permissions=True)
                    total_cached += 1
                    
            except Exception as e:
                frappe.log_error(f"Failed to process fetched grant {md_file.name}: {e}", "Funding Sync Error")

        frappe.db.commit()
        print(f"Successfully synced {total_cached} grants from Monorepo.")


def _process_funding_cache():
    """
    Processes the raw HTML from the cache and creates Neurotrophin documents.
    """
    from bs4 import BeautifulSoup
    from dateutil.parser import parse

    print("Processing funding cache...")
    raw_cache = frappe.get_all(
        "Raw Neurotrophin Cache",
        fields=[
            "data",
            "name"],
        order_by="retrieved_on desc",
        limit=1)
    if not raw_cache:
        print("No funding cache to process.")
        return

    html_content = raw_cache[0].data
    soup = BeautifulSoup(html_content, "html.parser")

    total_created = 0
    # This selector is based on the structure of the fundsforngos.org website as of October 2025
    # It might need to be updated if the website structure changes.
    for item in soup.select(".listing-item"):
        try:
            title_element = item.select_one("h3 a")
            title = title_element.text.strip() if title_element else None

            if not title or frappe.db.exists("Neurotrophin", {"title": title}):
                continue

            brief_element = item.select_one(".col-md-12 p")
            brief = brief_element.text.strip() if brief_element else ""

            deadline_element = item.select_one(".date")
            deadline_str = deadline_element.text.strip() if deadline_element else None
            deadline = None
            if deadline_str:
                try:
                    # Attempt to parse dates like "15-Nov-25"
                    deadline = parse(deadline_str).strftime(
                        '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Could not parse date: {deadline_str}")

            neurotrophin_doc = frappe.get_doc({
                "doctype": "Neurotrophin",
                "title": title,
                "brief": brief,
                "deadline": deadline,
            })
            neurotrophin_doc.insert(ignore_permissions=True)
            total_created += 1

        except Exception as e:
            frappe.log_error(
                f"Failed to process funding item: {e}",
                "Funding Processing Failed")

    frappe.db.commit()
    print(f"Successfully created {total_created} new Neurotrophins.")
    # Delete the cache after processing
    frappe.delete_doc(
        "Raw Neurotrophin Cache",
        raw_cache[0].name,
        ignore_permissions=True,
        force=True)
    frappe.db.commit()


def _delete_expired_funding():
    """
    Deletes Neurotrophin documents where the deadline has passed.
    """
    from frappe.utils import getdate, nowdate
    try:
        today = getdate(nowdate())
        expired_funding = frappe.get_all("Neurotrophin",
                                         filters={"deadline": ["<", today]},
                                         fields=["name"]
                                         )

        if not expired_funding:
            print("No expired funding to delete.")
            return

        for fund in expired_funding:
            frappe.delete_doc(
                "Neurotrophin",
                fund.name,
                ignore_permissions=True,
                force=True)

        frappe.db.commit()
        print(
            f"Successfully deleted {
                len(expired_funding)} expired funding opportunities.")
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            "Expired Funding Deletion Failed")
