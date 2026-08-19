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

import importlib
import importlib.util
import io
import os
import shutil
import traceback
import urllib.request
import zipfile
import frappe
from rcore.agent.plan_builder.perform_bootstrap_secrets_handshake import perform_bootstrap_secrets_handshake

# The StartupOS engine is consumed as the `startupos` pip package, but this
# SDK does not declare that dependency itself. The design studio SDK owns it:
# the studio fragment's manifest pins `startupos` to a protocol commit, so any
# app composed with the studio SDK gets the engine installed transitively with
# its requirements. plan_builder only detects at runtime whether the studio
# SDK is composed into the app — present means the engine is importable and
# plan compilation proceeds; absent means the feature degrades gracefully with
# a friendly message. This module never downloads engine files; it only
# prepares the site workspace the engine operates on.
#
# Templates are installed from the same protocol ref the studio SDK pins its
# `startupos` dependency to, so the engine and the documents it renders always
# come from one protocol commit.
PROTOCOL_REPO = "RokctAI/The-Rokct-Protocol"
STARTUPOS_PROTOCOL_REF = "564536bade5c154f817b09593fda6cfda8d60012"

# How the design studio SDK appears inside the composed app. The fragment is
# named `studio` today (RokctAI/designer#9 renamed it from `design_studio`);
# both module names are probed so apps composed before the rename keep
# working. Detection uses importlib.util.find_spec, which locates the package
# without importing it — no side effects.
_STUDIO_MODULE_CANDIDATES = ("rcore.studio", "rcore.design_studio")

# Telemetry title for admin-facing error detail (Error Log doctype).
_ERROR_LOG_TITLE = "StartupOS Engine"

# Where the .md templates live inside the protocol repository.
_TEMPLATE_ARCHIVE_PREFIX = "core/skills/.rok/startup_os/templates/"

# The engine's paths.templates_dir(root, type) resolves <root>/templates/<type>;
# both profile types must be populated before compile_instance can run.
_TEMPLATE_TYPES = ("business", "life")


@frappe.whitelist()
def ensure_startup_os_core():
    """
    Gates plan compilation on the studio SDK and readies the site workspace.

    The engine arrives as the `startupos` pip package installed transitively
    through the design studio SDK's own manifest dependency — this SDK
    declares no pip dependency for it. This function's job is:

    1.  Detect whether the studio SDK is composed into the app (find_spec,
        no import side effects). Absent: degrade gracefully — a friendly
        frappe.throw for the user, full detail to the error log for admins.
    2.  Studio present: verify `startupos` imports. If it does not, that is
        an integration bug (studio's dependency should have installed it);
        log full admin detail, throw a friendly one-liner.
        Under FRAPPE_TEST outside Docker, a minimal in-memory stub replaces
        the real engine instead (hermetic test runs skip the studio gate).
    3.  Ensure sites/<site>/StartupOS/ exists with instances/ and templates/
        populated. Templates install once from the pinned protocol ref —
        only .md files, never overwriting existing ones — mirroring the
        protocol skill's sync_templates semantics.

    A stale sites/<site>/StartupOS/core/ left behind by the old fetch
    mechanism is deliberately left in place but is inert: nothing puts the
    StartupOS root on sys.path anymore, so it can never shadow the pip
    package.
    """
    # Trigger bootstrap secrets handshake first to hydrate API keys in-memory
    perform_bootstrap_secrets_handshake()

    # Always use the site-specific StartupOS directory for clean multi-tenant
    # isolation. The engine resolves the same root itself (paths.resolve_
    # workspace_root's Frappe rule), but callers also receive it here to build
    # instance paths and to pass as an explicit workspace_root.
    startup_os_root = frappe.get_site_path("StartupOS")

    in_test = bool(frappe.flags.in_test or os.environ.get("FRAPPE_TEST"))
    is_in_docker = bool(
        os.path.exists("/.dockerenv")
        or os.path.isdir("/home/frappe/frappe-bench/sites")
        or os.environ.get("ROKCT_ECOSYSTEM_BUILD")
    )
    hermetic_test = in_test and not is_in_docker

    # 1. The engine: gated on the studio SDK being composed into this app.
    if hermetic_test:
        # Hermetic test runs skip the studio gate entirely; the in-memory
        # stub stands in for the engine when the real package is absent.
        if _engine_import_error() is not None:
            _install_test_stub()
    elif not _studio_sdk_present():
        # Studio SDK absent: the feature is simply not available here.
        # Full reason to the admin error log, one friendly line to the user.
        frappe.log_error(
            "StartupOS plan compilation was requested but the design studio "
            "SDK is not composed into this app: none of "
            + ", ".join(_STUDIO_MODULE_CANDIDATES)
            + " resolve via importlib.util.find_spec. The `startupos` engine "
            "arrives transitively through the studio SDK's pinned manifest "
            "dependency (startupos @ git+https://github.com/"
            + PROTOCOL_REPO + "@" + STARTUPOS_PROTOCOL_REF
            + "#subdirectory=core/utils/startup_os) — the agent SDK "
            "deliberately declares no pip dependency for it. Compose the "
            "studio SDK into this app to enable plan_builder's compile "
            "features.",
            _ERROR_LOG_TITLE,
        )
        frappe.throw("Business plan generation isn't available on this site yet.")
    else:
        engine_error = _engine_import_error()
        if engine_error is not None:
            # Studio SDK present but the engine does not import: integration
            # bug — studio's pinned dependency should have installed it with
            # the composed app's requirements.
            frappe.log_error(
                "Integration bug: the design studio SDK is composed into "
                "this app, so its pinned `startupos` pip dependency "
                "(startupos @ git+https://github.com/"
                + PROTOCOL_REPO + "@" + STARTUPOS_PROTOCOL_REF
                + "#subdirectory=core/utils/startup_os) should have been "
                "installed with the app's requirements, yet the package "
                f"does not import: {engine_error}. Reinstall the composed "
                "app's requirements to restore plan compilation. "
                "Traceback:\n"
                + "".join(
                    traceback.format_exception(
                        type(engine_error), engine_error, engine_error.__traceback__
                    )
                ),
                _ERROR_LOG_TITLE,
            )
            frappe.throw(
                "Business plan generation is temporarily unavailable. "
                "The site administrator has been notified."
            )

    # 2. The workspace: instances/ for profile data, templates/ for the suite.
    os.makedirs(os.path.join(startup_os_root, "instances"), exist_ok=True)
    _ensure_templates(startup_os_root, hermetic_test)

    return startup_os_root


def _studio_sdk_present():
    """True when the design studio SDK is composed into this app.

    Probes the composed module names with importlib.util.find_spec, which
    locates a package without importing it — detection has no side effects.
    find_spec raises when the app package itself cannot be resolved or a
    parent is not a package; either simply means "not composed here".
    """
    for module_name in _STUDIO_MODULE_CANDIDATES:
        try:
            if importlib.util.find_spec(module_name) is not None:
                return True
        except (ImportError, AttributeError, ValueError):
            continue
    return False


def _engine_import_error():
    """Try to import the engine (`startupos` with compiler and parser).

    Returns None when everything imports cleanly, otherwise the ImportError
    raised — callers decide whether that means "install the stub" (hermetic
    tests) or "integration bug" (studio SDK present in production).
    """
    try:
        importlib.import_module("startupos")
        importlib.import_module("startupos.compiler")
        importlib.import_module("startupos.parser")
    except ImportError as exc:
        return exc
    return None


def _install_test_stub():
    """Register a minimal in-memory `startupos` stub for hermetic test runs.

    Mirrors the old on-disk test stubs: compile_instance is a no-op and
    parse_questions_md returns an empty mapping, so plan_builder code paths
    exercise without the real engine or network access.
    """
    import sys
    import types

    package = types.ModuleType("startupos")
    package.__path__ = []
    package.__version__ = "0.0.0-test-stub"

    compiler = types.ModuleType("startupos.compiler")

    def compile_instance(instance_type, instance_name, **kwargs):
        return None

    compiler.compile_instance = compile_instance

    parser = types.ModuleType("startupos.parser")

    def parse_questions_md(questions_path):
        return {}

    parser.parse_questions_md = parse_questions_md

    package.compiler = compiler
    package.parser = parser
    sys.modules["startupos"] = package
    sys.modules["startupos.compiler"] = compiler
    sys.modules["startupos.parser"] = parser
    print("[StartupOS] Registered in-memory test stub for the startupos package")


def _has_templates(templates_root):
    """True when every profile type has at least one .md template installed."""
    for instance_type in _TEMPLATE_TYPES:
        type_dir = os.path.join(templates_root, instance_type)
        if not os.path.isdir(type_dir):
            return False
        found = False
        for _directory, _subdirs, filenames in os.walk(type_dir):
            if any(name.endswith(".md") for name in filenames):
                found = True
                break
        if not found:
            return False
    return True


def _ensure_templates(startup_os_root, hermetic_test):
    """Install the .md template suite into <root>/templates/ if missing.

    Resolution order mirrors the old engine-file resolution: a sibling
    protocol checkout first (desktop development), then the pinned protocol
    archive on GitHub. Only .md files are installed and existing files are
    never overwritten. Hermetic test runs skip installation entirely — the
    stub compiler does not read templates, and tests that need them build
    their own (see tests/verify_interactive_api.py).
    """
    destination = os.path.join(startup_os_root, "templates")
    if _has_templates(destination):
        return

    if hermetic_test:
        return

    # 1. Sibling protocol checkout (Desktop Sibling Dev check).
    parent = os.path.dirname(os.path.abspath(__file__))
    for _ in range(7):
        parent = os.path.dirname(parent)
        probe = os.path.join(
            parent, "The-Rokct-Protocol", "core", "skills", ".rok",
            "startup_os", "templates",
        )
        if os.path.isdir(probe):
            copied = _copy_md_tree(probe, destination)
            print(f"[StartupOS] Installed {copied} templates from sibling protocol checkout")
            break
    if _has_templates(destination):
        return

    # 2. Pinned protocol archive (production Docker without a checkout).
    try:
        count = _install_templates_from_archive(destination)
        print(f"[StartupOS] Installed {count} templates from protocol archive @ {STARTUPOS_PROTOCOL_REF[:12]}")
    except Exception as net_e:
        print(f"[StartupOS] Template archive fetch failed: {net_e}")

    if not _has_templates(destination):
        raise RuntimeError(
            "Failed to install StartupOS templates. Expected .md templates "
            f"under {destination} for types {', '.join(_TEMPLATE_TYPES)}; "
            "no sibling protocol checkout was found and the pinned protocol "
            f"archive ({PROTOCOL_REPO}@{STARTUPOS_PROTOCOL_REF[:12]}) was "
            "unreachable."
        )


def _copy_md_tree(source, destination):
    """Copy .md files from source into destination, never overwriting."""
    copied = 0
    for directory, subdirs, filenames in os.walk(source):
        subdirs[:] = sorted(name for name in subdirs if not name.startswith("."))
        relative = os.path.relpath(directory, source)
        target_dir = destination if relative == "." else os.path.join(destination, relative)
        os.makedirs(target_dir, exist_ok=True)
        for filename in sorted(filenames):
            if not filename.endswith(".md"):
                continue
            target = os.path.join(target_dir, filename)
            if os.path.exists(target):
                continue
            shutil.copy2(os.path.join(directory, filename), target)
            copied += 1
    return copied


def _install_templates_from_archive(destination):
    """Extract .md templates from the pinned protocol archive, never overwriting.

    `archive/<sha>.zip` resolves for commit SHAs (the pinned ref), branches
    and tags alike, matching the protocol skill's own fallback.
    """
    archive_url = f"https://github.com/{PROTOCOL_REPO}/archive/{STARTUPOS_PROTOCOL_REF}.zip"
    trace_id = frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else "startup-os-templates-trace"
    request = urllib.request.Request(
        archive_url,
        headers={"User-Agent": "ROKCT-Bootstrap-Agent/1.0", "x-trace-id": trace_id or ""},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()

    destination_real = os.path.realpath(destination)
    count = 0
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for name in archive.namelist():
            if name.endswith("/") or _TEMPLATE_ARCHIVE_PREFIX not in name:
                continue
            relative = name.split(_TEMPLATE_ARCHIVE_PREFIX, 1)[1]
            if not relative.endswith(".md"):
                continue
            target = os.path.realpath(os.path.join(destination, relative))
            if not target.startswith(destination_real + os.sep):
                continue  # refuse traversal out of the templates directory
            if os.path.exists(target):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(archive.read(name))
            count += 1
    return count
