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

from typing import Any, Optional
import frappe
from ..utils import api_response


@frappe.whitelist()
def get_weather(location: str) -> Any:
    """
    Proxy endpoint to get weather data from the control site, with tenant-side caching.
    This follows the same authentication pattern as other tenant-to-control-panel APIs.
    """
    if not location:
        frappe.throw("Location is a required parameter.")

    # Use a different cache key for the proxy to avoid conflicts
    cache_key = f"weather_proxy_{location.lower().replace(' ', '_')}"
    cached_data = frappe.cache.get_value(cache_key)

    if cached_data:
        return cached_data

    # Get connection details from site config (set during tenant provisioning)
    control_plane_url = frappe.conf.get("control_plane_url")
    api_secret = frappe.conf.get("api_secret")

    if not control_plane_url or not api_secret:
        frappe.log_error(
            "Tenant site is not configured to communicate with the control panel.",
            "Weather Proxy Error",
        )
        frappe.throw(
            "Platform communication is not configured.",
            title="Configuration Error",
        )

    # Construct the secure API call
    scheme = frappe.conf.get("control_plane_scheme", "https")
    api_url = f"{scheme}://{control_plane_url}/api/method/control.control.weather.get_weather_data"
    headers = {"X-Rokct-Secret": api_secret, "Accept": "application/json"}

    try:
        # Use frappe.make_get_request which is a wrapper around requests
        # and handles logging and exceptions in a standard way.
        response = frappe.make_get_request(
            api_url, headers=headers, params={"location": location}
        )

        # Cache the successful response for 10 minutes on the tenant site
        frappe.cache.set_value(cache_key, response, expires_in_sec=600)

        return api_response(data=response)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Weather Proxy API Error")
        frappe.throw(
            f"An error occurred while fetching weather data from the control plane: {e}")


@frappe.whitelist(allow_guest=True)
def api_status() -> Any:
    """
    Returns a simple status of the API.

    Reports "maintenance" while the site's `maintenance_mode` site_config
    flag is set (bench set-config maintenance_mode 1) — clients use this to
    show their maintenance page instead of treating the site as down.
    """
    return api_response(
        data={
            "status": "maintenance" if frappe.conf.get("maintenance_mode") else "ok",
            "version": frappe.get_attr("frappe.__version__"),
            "user": frappe.session.user,
        }
    )


@frappe.whitelist(allow_guest=True)
def get_languages() -> Any:
    """
    Returns a list of all enabled languages.
    """
    langs = frappe.get_all(
        "Language", filters={"enabled": 1}, fields=["name", "language_name"]
    )
    return api_response(data=langs)


@frappe.whitelist(allow_guest=True)
def get_currencies() -> Any:
    """
    Returns a list of all enabled currencies.
    """
    currencies = frappe.get_all(
        "Currency",
        filters={"enabled": 1},
        fields=["name", "currency_name", "symbol"],
    )
    return api_response(data=currencies)


@frappe.whitelist()
def trigger_system_update() -> Any:
    """
    Triggers a system update. For tenant sites, this only runs a migration.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Unauthorized")

    # Check if user is System Manager
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Unauthorized")

    # Enqueue the migration task
    frappe.enqueue("frappe.migrate.migrate", queue="long")

    return api_response(message="System migration started in background.")


@frappe.whitelist(allow_guest=True)
def get_global_settings() -> Any:
    """
    Retrieves global settings formatted as a key-value list for the frontend.
    Aggregates data from 'Settings' and 'Global Settings'.
    """
    settings_data = []

    try:
        settings = frappe.get_single("Settings")

        # Map specific fields that the frontend likely needs
        # Based on analysis of Flutter app usage, it generally expects keys like:
        # 'app_name', 'default_tax', 'default_currency', etc.
        # mapping schema fields to generic keys

        if settings.project_title:
            settings_data.append(
                {"key": "app_name", "value": settings.project_title}
            )

        if settings.service_fee:
            settings_data.append(
                {"key": "default_tax", "value": str(settings.service_fee)}
            )

        if settings.deliveryman_order_acceptance_time:
            settings_data.append(
                {
                    "key": "deliveryman_order_acceptance_time",
                    "value": str(settings.deliveryman_order_acceptance_time),
                }
            )

        # Add map key if available in Global Settings
        global_settings = frappe.get_single("Global Settings")
        if global_settings.google_maps_api_key:
            settings_data.append(
                {
                    "key": "google_maps_key",
                    "value": global_settings.google_maps_api_key,
                }
            )

        # Add default language
        lang = (
            frappe.db.get_single_value("System Settings", "language") or "en"
        )
        settings_data.append({"key": "default_language", "value": lang})

        # Add default currency
        currency = frappe.db.get_value("Currency", {"enabled": 1}, "name")
        if currency:
            settings_data.append(
                {"key": "default_currency", "value": currency}
            )

        # Add distance unit
        # Check if defined in any relevant settings, otherwise default to km
        distance_unit = (
            frappe.db.get_single_value("System Settings", "distance_unit")
            or "km"
        )
        settings_data.append({"key": "distance_unit", "value": distance_unit})

    except Exception as e:
        frappe.log_error(f"Error fetching global settings: {e}")

    return api_response(data=settings_data)


@frappe.whitelist(allow_guest=True)
def get_policy(lang: str='en') -> Any:
    """
    Returns the privacy policy.
    """
    return {"content": "Privacy Policy content..."}


@frappe.whitelist(allow_guest=True)
def get_terms(lang: str='en') -> Any:
    """
    Returns the terms and conditions.
    """
    return {"content": "Terms and Conditions content..."}
