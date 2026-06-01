import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def generate_release_notes(repo_url: str, commit_log: str, version_name: str = "vNext") -> dict:
    """
    Generates Release Notes via LLM.
    """
    trace_id = str(uuid.uuid4())
    
    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)
    
    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Generating release notes for repo_url: {repo_url}, version_name: {version_name}")
    
    if frappe.session.user == "Guest":
        log_error("Authentication required: Guest user attempted to generate release notes.")
        frappe.throw("Authentication Required: Please provide a valid API Token.", frappe.PermissionError)

    try:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            repo_owner = parts[0]
        else:
            repo_owner = repo_url.split("/")[0]
    except Exception:
        log_error(f"Invalid Repo URL format: {repo_url}")
        frappe.throw(f"Invalid Repo URL format: {repo_url}.", frappe.InvalidRequestError)

    settings = frappe.get_single("Brain Settings")
    allowed_owners = (settings.allowed_repo_owners or "").split(",")
    allowed_owners = [o.strip().lower() for o in allowed_owners if o.strip()]
    
    if repo_owner.lower() not in allowed_owners:
        log_error(f"Repo Owner '{repo_owner}' is not authorized.")
        frappe.throw(f"Repo Owner '{repo_owner}' is not authorized.", frappe.PermissionError)
        
    from rcore.scripts.generate_release_notes import generate_release_notes as _generate
    result = _generate(commit_log, version_name)
    log_info(f"Successfully generated release notes for repo_url: {repo_url}")
    return result