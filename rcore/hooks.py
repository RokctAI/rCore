# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

app_name = "rcore"
app_title = "Rcore"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "AGPL-3.0-only"

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
# before_uninstall for the build-in-progress guard is composed from the
# builder SDK module's manifest (corporate/builder/frappe) - not declared
# statically here, so it is registered exactly once.

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
    "paas.api.auth.refresh": "rcore.auth.tenant.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.tenant.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}

# Frappe's dispatcher resolves aliases from this hook (see frappe.override_whitelisted_method)
override_whitelisted_methods = {
    "rokct.platform.api": "rcore.platform.api.execute",
    "paas.api.auth.refresh": "rcore.auth.tenant.api.auth.auth.refresh",
    "paas.tenant.api.log_frontend_error": "rcore.telemetry.tenant.telemetry.log_frontend_error.log_frontend_error",
    "paas.api.upload.upload_file": "rcore.base.api.upload.upload_file",
}
