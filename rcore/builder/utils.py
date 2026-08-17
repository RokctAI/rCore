from typing import Any, Optional
# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
import os


def prevent_uninstall_if_build_active():
    """
    This function is called by the `on_uninstall` hook.
    It prevents the app from being uninstalled if there are active builds.
    """
    active_builds = frappe.get_all(
        "RQ Job",
        filters={
            "status": ["in", ["queued", "started"]],
            "method": "rcore.builder.tasks._generate_flutter_app"
        },
        limit=1
    )

    if active_builds:
        frappe.throw(
            "Cannot uninstall the Rokct app while one or more app builds are in progress. "
            "Please wait for the builds to complete or cancel them from the 'RQ Job' list.")

    print("No active builds found. Proceeding with uninstallation.")


@frappe.whitelist()
def get_available_source_projects() -> Any:
    """Returns a list of available source project folders."""
    import sys; _ = (frappe.request.headers.get("x-trace-id") if hasattr(frappe, "request") else None, sys.stderr)
    try:
        source_path = frappe.get_app_path("rcore", "builder", "source_code")
        if not os.path.exists(source_path):
            return []

        projects = []
        for item in os.listdir(source_path):
            item_path = os.path.join(source_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Format label: paas_customer -> Customer
                label = item.replace("paas_", "").replace("_", " ").title()
                projects.append({"label": label, "value": item})

        return sorted(projects, key=lambda x: x["label"])
    except Exception as e:
        frappe.log_error(f"Error listing source projects: {e}")
        return []
