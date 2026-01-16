# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import subprocess
import json

def run_correction():
    """
    Master script to correct the fiscal year for all applicable tenant sites.
    This is intended to be run from an `on_update` hook on the control panel.
    """
    # This script should only ever run on the control panel.
    if frappe.conf.get("app_role") != "control":
        print("--- SKIPPED: Fiscal year correction is only for control panel sites. ---")
        return

    print("--- Running Fiscal Year Correction for Tenant Sites ---")

    try:
        # 1. Get the correct fiscal year start date from the control panel's config.
        start_date = frappe.db.get_single_value("Subscription Settings", "financial_year_begins_on")

        if not start_date:
            print("ERROR: `financial_year_begins_on` not found in Subscription Settings. Aborting.")
            return

        print(f"INFO: Using start date from Subscription Settings: {start_date}")

        # 2. Get all active and trialing tenant sites.
        tenant_sites = frappe.get_all(
            "Company Subscription",
            filters={"status": ["in", ["Active", "Trialing"]]},
            pluck="site_name"
        )

        if not tenant_sites:
            print("INFO: No active or trialing tenant sites found to correct.")
            return

        print(f"Found {len(tenant_sites)} tenant sites to check for fiscal year correction.")

        bench_path = frappe.utils.get_bench_path()

        # 3. Loop through each site and run the corrective function.
        for site in tenant_sites:
            try:
                print(f"  - Processing site: {site}...")

                command = [
                    "bench", "--site", site, "execute",
                    "rcore.tenant.api.update_fiscal_year_if_default",
                    "--kwargs", json.dumps({"start_date": start_date})
                ]

                process = subprocess.run(
                    command,
                    cwd=bench_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=120
                )

                # Log the output from the tenant site's function for better visibility.
                if process.stdout:
                    response = json.loads(process.stdout)
                    status = response.get("status", "unknown")
                    message = response.get("message", "No message returned.")
                    print(f"    - Status: {status.upper()} | Message: {message}")
                else:
                    print(f"    - WARNING: No output received from {site}. Check the site's error logs if issues persist.")

            except subprocess.CalledProcessError as e:
                print(f"    - ERROR: Failed to execute correction script on {site}.")
                print(f"      - STDERR: {e.stderr}")
                # Log this failure but continue with the next site.
                frappe.log_error(
                    message=f"Failed to correct fiscal year for site {site}.\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}",
                    title="Tenant Fiscal Year Correction Failure"
                )
            except Exception as e:
                print(f"    - ERROR: An unexpected error occurred while processing {site}: {e}")
                frappe.log_error(
                    message=f"An unexpected error occurred while correcting fiscal year for site {site}.\n{frappe.get_traceback()}",
                    title="Tenant Fiscal Year Correction Failure"
                )

        print("--- Fiscal Year Correction for Tenant Sites Complete ---")

    except Exception as e:
        print(f"FATAL ERROR during master fiscal year correction script: {e}")
        frappe.log_error(
            message=f"The master fiscal year correction script failed.\n{frappe.get_traceback()}",
            title="Master Fiscal Year Correction Failure"
        )
