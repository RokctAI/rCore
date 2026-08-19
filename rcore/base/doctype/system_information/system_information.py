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

# Tenant context: session.user validation
import frappe
from frappe.model.document import Document
import json
import os


class SystemInformation(Document):
    def onload(self):  # noqa: C901
        # Core Version (Frappe)
        self.rcore = f"Frappe {frappe.__version__}"

        # App version from the serving app's versions.json.
        # Doctype trees compose verbatim (no rcore substitution), so the
        # composed app name is derived from __name__ at runtime — for a
        # composed doctype module __name__ is
        # "<app>.<module>.doctype.system_information.system_information".
        app = __name__.split(".")[0]
        try:
            app_versions_file = frappe.get_app_path(app, "versions.json")
            with open(app_versions_file, "r") as f:
                app_versions = json.load(f)
            self.app_version = app_versions.get(app, "Unknown")
        except Exception:
            self.app_version = "Error reading versions.json"

        # 1. Flutter SDK Version from local rcore/versions.json (if available)
        self.flutter_sdk_version = "N/A"
        try:
            if "rcore" in frappe.get_installed_apps():
                rcore_versions_file = frappe.get_app_path(
                    "rcore", "versions.json"
                )
                if os.path.exists(rcore_versions_file):
                    with open(rcore_versions_file, "r") as f:
                        rcore_versions = json.load(f)
                    self.flutter_sdk_version = rcore_versions.get(
                        "flutter_sdk_version", "Unknown"
                    )
        except Exception:
            pass  # Fail silently if r core issues

        # 2. Control/Brain/Payments Versions
        # Always try Remote API. If opensource/offline, these remain
        # Unavailable/NA.

        self.control = "Unavailable"
        self.brain = "Unavailable"
        self.payments = "Unavailable"

        try:
            import requests

            # Get the control platform URL from site config
            control_url = frappe.conf.get(
                "control_url", "https://platform.rokct.ai"
            )

            # Only try fetching if it looks like a real URL
            if control_url and "http" in control_url:
                api_endpoint = f"{control_url}/api/method/control.control.api.versions.get_versions"
                trace_id = frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else "system-information-trace"
                headers = {"x-trace-id": trace_id or ""}
                response = requests.get(api_endpoint, headers=headers, timeout=3)

                if response.status_code == 200:
                    data = response.json()
                    api_versions = data.get("message", {})

                    if isinstance(api_versions, dict):

                        def get_ver(app_name):
                            app_data = api_versions.get(app_name, {})
                            if isinstance(app_data, dict):
                                return app_data.get("version", "Unavailable")
                            return "Unavailable"

                        self.control = get_ver("control")
                        self.brain = get_ver("brain")
                        self.payments = get_ver("payments")
        except Exception:
            # check_version failure is not critical
            pass

        # Latest Error
        try:
            latest_log = frappe.get_all(
                "Error Log",
                limit=1,
                order_by="creation desc",
                fields=["error", "method", "creation"],
            )
            if latest_log:
                log = latest_log[0]
                self.latest_error = f"{
                    log.creation}: {
                    log.method}\n{
                    log.error}"
            else:
                self.latest_error = "No errors found."
        except Exception:
            self.latest_error = "Could not fetch error logs."
