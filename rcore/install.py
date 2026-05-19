# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import os
import subprocess
import frappe


def fetch_agent_scripts():
    """
    Fetches delegate_to_agent.py from The-Rokct-Protocol during app install.
    Called via after_install hook in hooks.py.
    """
    # Resolve the target path in the rcore package
    target_dir = frappe.get_app_path("rcore", "rcore", "scripts")
    target_file = os.path.join(target_dir, "delegate_to_agent.py")
    
    # Skip if already exists to avoid re-downloading
    if os.path.exists(target_file):
        return

    # Ensure target directory exists
    os.makedirs(target_dir, exist_ok=True)

    # Use git sparse-checkout to fetch file from monorepo
    repo_url = "git@github.com:RokctAI/The-Rokct-Protocol.git"
    file_path = "core/skills/agent_delegation/scripts/delegate_to_agent.py"
    
    try:
        # Create temp directory for sparse checkout
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        # Clone with sparse checkout
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", repo_url, temp_dir],
            check=True,
            capture_output=True
        )
        
        # Enable sparse-checkout for the specific file
        subprocess.run(
            ["git", "sparse-checkout", "set", file_path],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Move the file to target location
        src_file = os.path.join(temp_dir, file_path)
        if os.path.exists(src_file):
            import shutil
            shutil.move(src_file, target_file)
            
        # Cleanup temp dir
        shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        frappe.log_error(
            f"Failed to fetch delegate_to_agent.py from The-Rokct-Protocol: {e}",
            "Agent Scripts Fetch Failed"
        )