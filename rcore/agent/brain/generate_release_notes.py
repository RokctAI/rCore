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

import json
import frappe
import sys
import uuid
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient


@frappe.whitelist()
def generate_release_notes(repo_url: str, commit_log: str, version_name: str = "vNext", diff_summary: str = None) -> dict:
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

    if diff_summary:
        # Supplied by the release workflow (git diff --stat); appended so the LLM
        # sees change-size context alongside the commit messages.
        commit_log = f"{commit_log}\n\nDiff summary:\n{diff_summary}"

    from rcore.agent.brain.scripts.generate_release_notes import generate_release_notes as _generate
    result = _generate(commit_log, version_name)
    log_info(f"Successfully generated release notes for repo_url: {repo_url}")
    return result
