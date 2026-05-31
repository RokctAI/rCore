import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def generate_release_notes(repo_url, commit_log, version_name="vNext"):
    """
    Generates Release Notes via LLM.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Authentication Required: Please provide a valid API Token.", frappe.PermissionError)

    try:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            repo_owner = parts[0]
        else:
            repo_owner = repo_url.split("/")[0]
    except Exception:
        frappe.throw(f"Invalid Repo URL format: {repo_url}.", frappe.InvalidRequestError)

    settings = frappe.get_single("Brain Settings")
    allowed_owners = (settings.allowed_repo_owners or "").split(",")
    allowed_owners = [o.strip().lower() for o in allowed_owners if o.strip()]
    
    if repo_owner.lower() not in allowed_owners:
        frappe.throw(f"Repo Owner '{repo_owner}' is not authorized.", frappe.PermissionError)
        
    from rcore.scripts.generate_release_notes import generate_release_notes as _generate
    return _generate(commit_log, version_name)
