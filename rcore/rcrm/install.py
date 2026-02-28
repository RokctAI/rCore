# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import click
import frappe


def after_install():
    auto_enable_erpnext_integration()
    frappe.db.commit()


def auto_enable_erpnext_integration():
    """
    Automatically enables ERPNext integration if ERPNext is installed.
    This ensures users don't have to manually configure it for thousands of tenants.
    """
    if "erpnext" in frappe.get_installed_apps():
        try:
            settings = frappe.get_doc("ERPNext CRM Settings")
            if not settings.enabled:
                settings.enabled = 1
                # We don't set site URL/keys because we assume same-site integration by default
                # if fields are empty, is_erpnext_in_different_site defaults to
                # 0
                settings.save(ignore_permissions=True)
                click.secho(
                    "* Auto-enabled RCRM - ERPNext Integration",
                    fg="green")
        except Exception as e:
            click.secho(
                f"* Failed to auto-enable RCRM - ERPNext Integration: {e}",
                fg="yellow")
