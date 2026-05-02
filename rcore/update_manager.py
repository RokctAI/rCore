# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
import subprocess
import os

@frappe.whitelist()
def update_tenant_ecosystem(immediate=False):
    """
    Tenant-specific self-update engine. 
    Only active if app_role is 'tenant'.
    """
    # Guardrail: Only run if this is a tenant spoke
    if frappe.conf.get("app_role") != "tenant":
        return {"status": "ignored", "message": "Self-update skipped: app_role is not 'tenant'"}

    print("🚀 Rcore: Starting Tenant Self-Update...")
    
    try:
        compose_file = "docker-compose.tenant.yml"
        
        if os.path.exists(compose_file):
            print(f"--- Pulling latest tenant images ---")
            subprocess.run(["docker", "compose", "-f", compose_file, "pull"], check=True)
            
            print(f"--- Restarting tenant spoke ---")
            subprocess.run(["docker", "compose", "-f", compose_file, "up", "-d", "--remove-orphans"], check=True)
            
            return {"status": "success", "message": "Tenant ecosystem upgrade initiated."}
        else:
            return {"status": "error", "message": f"Tenant compose file {compose_file} not found."}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Tenant Ecosystem Upgrade Failed")
        return {"status": "error", "message": str(e)}
