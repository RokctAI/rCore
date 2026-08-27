# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
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

from typing import Any, Optional
import frappe


@frappe.whitelist(allow_guest=True)
def get_assetlinks() -> Any:
    """
    The get_assetlinks function generates a JSON response containing asset links configuration for a Flutter app. It retrieves the package name and SHA256 fingerprints from the Flutter App Configuration settings, cleans up the fingerprints by removing empty lines or whitespace, and returns a list of asset links in the required format. The function returns an empty list if the package name is not set or if an error occurs during execution. The parameters for this function are implicitly defined by the configuration settings, specifically the package name and SHA256 fingerprints, which are used to construct the asset links configuration.
    """
    import sys

    _ = (
        frappe.request.headers.get("x-trace-id")
        if hasattr(frappe, "request")
        else None,
        sys.stderr,
    )
    frappe.response["type"] = "json"
    try:
        config = frappe.get_single("Flutter App Configuration")
        package_name = config.package_name
        fingerprints = (
            config.sha256_fingerprint.splitlines() if config.sha256_fingerprint else []
        )

        # Clean up fingerprints (remove empty lines or whitespace)
        fingerprints = [f.strip() for f in fingerprints if f.strip()]

        if not package_name:
            return []

        return [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": package_name,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    except Exception:
        frappe.log_error("Error generating assetlinks.json")
        return []


@frappe.whitelist(allow_guest=True)
def get_apple_app_site_association() -> Any:
    """
    The get_apple_app_site_association function generates the apple-app-site-association JSON object, which is used to enable Universal Links for an iOS application. This function retrieves the Apple team ID and iOS bundle ID from the Flutter App Configuration, constructs the app ID, and returns a JSON object containing the applinks details. The returned JSON object includes the app ID and specifies that all paths are supported. If the team ID or bundle ID is missing, or if an error occurs during execution, an empty dictionary is returned.
    """
    import sys

    _ = (
        frappe.request.headers.get("x-trace-id")
        if hasattr(frappe, "request")
        else None,
        sys.stderr,
    )
    frappe.response["type"] = "json"
    try:
        config = frappe.get_single("Flutter App Configuration")
        team_id = config.apple_team_id
        bundle_id = config.ios_package_name

        if not team_id or not bundle_id:
            return {}

        app_id = f"{team_id}.{bundle_id}"

        return {
            "applinks": {
                "apps": [],
                "details": [{"appID": app_id, "paths": ["*"]}],
            }
        }
    except Exception:
        frappe.log_error("Error generating apple-app-site-association")
        return {}
