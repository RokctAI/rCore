# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import click
import frappe

@click.command("update-tenant-ecosystem")
def update_tenant_ecosystem_command():
    """
    Triggers self-update for the tenant spoke (rcore).
    """
    from rcore.update_manager import update_tenant_ecosystem
    
    if not frappe.local.site:
        print("Please provide a site using --site [site]")
        return

    result = update_tenant_ecosystem()
    if result.get("status") == "success":
        print(f"✅ {result.get('message')}")
    elif result.get("status") == "ignored":
        print(f"ℹ️ {result.get('message')}")
    else:
        print(f"❌ {result.get('message')}")

commands = [
    update_tenant_ecosystem_command
]
