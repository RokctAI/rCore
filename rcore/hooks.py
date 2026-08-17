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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

app_name = "rcore"
app_title = "Rcore"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "mit"

# NOTE: no required_apps = ["erpnext"] (unlike the retired paas shell).
# ERPNext-touching install/test steps are guarded at runtime with
# `"erpnext" in frappe.get_installed_apps()` instead.

# Testing
# -------
before_tests = "rcore.tests.utils.before_tests"

# Installation
# ------------
before_install = "rcore.install.check_site_role"
after_install = "rcore.install.after_install"
before_uninstall = ["rcore.builder.utils.prevent_uninstall_if_build_active"]

# Website Route Rules
website_route_rules = [
    {
        "from_route": "/.well-known/assetlinks.json",
        "to_route": "rcore.api.app_links.get_assetlinks",
    },
    {
        "from_route": "/.well-known/apple-app-site-association",
        "to_route": "rcore.api.app_links.get_apple_app_site_association",
    },
]

# Whitelisted Methods (Public APIs)
whitelisted_methods = {
    # The single universal entry point for the platform (routes by site role)
    "rokct.platform.api": "rcore.platform.api.execute",
    # Legacy paas.* aliases kept for clients still calling the old app name.
    # Targets are the rcore-substituted paths the SDK module manifests declare.
    "paas.api.auth.refresh": "rcore.auth.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}

# Frappe's dispatcher resolves aliases from this hook (see frappe.override_whitelisted_method)
override_whitelisted_methods = {
    "rokct.platform.api": "rcore.platform.api.execute",
    "paas.api.auth.refresh": "rcore.auth.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}
