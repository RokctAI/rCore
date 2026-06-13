# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
import subprocess
import os
import sys
import json
import uuid


@frappe.whitelist()
def update_tenant_ecosystem(immediate: bool = False) -> dict:
    """
    Tenant-specific self-update engine.
    Only active if app_role is 'tenant'.
    """
    # Guardrail: Only run if this is a tenant spoke
    if frappe.conf.get("app_role") != "tenant":
        return {
            "status": "ignored",
            "message": "Self-update skipped: app_role is not 'tenant'",
        }

    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info("🚀 Rcore: Starting Tenant Self-Update...")

    try:
        compose_file = "docker-compose.tenant.yml"

        if os.path.exists(compose_file):
            log_info(f"--- Pulling latest tenant images ---")
            subprocess.run(
                ["docker", "compose", "-f", compose_file, "pull"], check=True
            )

            log_info(f"--- Restarting tenant spoke ---")
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    compose_file,
                    "up",
                    "-d",
                    "--remove-orphans",
                ],
                check=True,
            )

            return {
                "status": "success",
                "message": "Tenant ecosystem upgrade initiated.",
            }
        else:
            log_error(f"Tenant compose file {compose_file} not found.")
            return {
                "status": "error",
                "message": f"Tenant compose file {compose_file} not found.",
            }

    except Exception as e:
        log_error(f"Tenant Ecosystem Upgrade Failed: {str(e)}")
        frappe.log_error(frappe.get_traceback(), "Tenant Ecosystem Upgrade Failed")
        return {"status": "error", "message": str(e)}
