# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
import os
import sys
import urllib.request
from rcore.api.plan_builder.perform_bootstrap_secrets_handshake import (
    perform_bootstrap_secrets_handshake,
)


def ensure_startup_os_core():
    """
    Ensures that the compiler.py and parser.py are available for the plan builder API.
    Resolves the StartupOS path dynamically. Always uses the site-specific StartupOS folder
    to ensure clean isolation and prevent workspace cluttering. If files are missing,
    fetches them from raw GitHub.
    """
    # Trigger bootstrap secrets handshake first to hydrate API keys in-memory
    perform_bootstrap_secrets_handshake()

    # Always use the site-specific StartupOS directory for clean multi-tenant isolation
    startup_os_root = frappe.get_site_path("StartupOS")

    core_dir = os.path.join(startup_os_root, "core")
    os.makedirs(core_dir, exist_ok=True)

    init_py = os.path.join(core_dir, "__init__.py")
    if not os.path.exists(init_py):
        with open(init_py, "w") as f:
            f.write("")

    core_files = ["compiler.py", "parser.py", "agent_bridge.py"]

    for f_name in core_files:
        dest_file = os.path.join(core_dir, f_name)

        # If the file already exists locally, keep it (do not auto-fetch or overwrite)
        if os.path.exists(dest_file):
            continue

        # Determine if we are in Docker or building the ecosystem
        is_in_docker = (
            os.path.exists("/.dockerenv")
            or os.path.isdir("/home/frappe/frappe-bench/sites")
            or os.environ.get("ROKCT_ECOSYSTEM_BUILD")
        )
        in_test = frappe.flags.in_test or os.environ.get("FRAPPE_TEST")

        # 1. Attempt to resolve locally by traversing up out of the current repository (Desktop Sibling Dev check)
        resolved = False
        if not (in_test and not is_in_docker):
            parent = os.path.dirname(os.path.abspath(__file__))
            for _ in range(7):
                parent = os.path.dirname(parent)
                probe_path = os.path.join(
                    parent,
                    "The-Rokct-Protocol",
                    "core",
                    "skills",
                    "startup_os",
                    "scripts",
                    "core",
                    f_name,
                )
                if os.path.exists(probe_path):
                    import shutil

                    shutil.copy(probe_path, dest_file)
                    resolved = True
                    print(
                        f"[StartupOS] Resolved and loaded local core module: {f_name}"
                    )
                    break

        # 2. If missing (e.g. running in isolated production Docker without submodules), fetch remotely from raw GitHub
        if not resolved and not (in_test and not is_in_docker):
            try:
                print(f"[StartupOS] Attempting remote fetch for {f_name}...")
                github_url = f"https://raw.githubusercontent.com/RokctAI/The-Rokct-Protocol/main/core/skills/startup_os/scripts/core/{f_name}"
                req = urllib.request.Request(
                    github_url, headers={"User-Agent": "ROKCT-Bootstrap-Agent/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    with open(dest_file, "wb") as out_f:
                        out_f.write(response.read())
                resolved = True
                print(f"[StartupOS] Successfully fetched remote core module: {f_name}")
            except Exception as net_e:
                print(f"[StartupOS] Remote fetch failed for {f_name}: {net_e}")

        # 3. Last resort fallback to test mock if in test mode
        if not resolved:
            if frappe.flags.in_test or os.environ.get("FRAPPE_TEST"):
                with open(dest_file, "w", encoding="utf-8") as f:
                    if f_name == "compiler.py":
                        f.write(
                            "def compile_instance(profile_type, instance_name):\n    pass\n"
                        )
                    elif f_name == "parser.py":
                        f.write(
                            "def parse_questions_md(questions_path):\n    return {}\n"
                        )
                    else:
                        f.write("")
                resolved = True
                print(f"[StartupOS] Created test stub for missing module: {f_name}")
            else:
                raise RuntimeError(
                    f"Failed to load StartupOS core engine {f_name}. "
                    "File is missing locally and remote fetching is offline/unavailable."
                )

    if startup_os_root not in sys.path:
        sys.path.insert(0, startup_os_root)

    return startup_os_root
