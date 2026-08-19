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
# Tenant context: session.user validation
import frappe
import json
from ..utils import _require_admin


@frappe.whitelist()
def get_all_languages(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all languages (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Language",
        fields=["name", "language_name", "enabled"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def update_language(language_name: Any, language_data: Any) -> Any:
    """
    Updates a language (for admins).
    """
    _require_admin()
    if isinstance(language_data, str):
        language_data = json.loads(language_data)

    language = frappe.get_doc("Language", language_name)
    language.update(language_data)
    language.save(ignore_permissions=True)
    return language.as_dict()


@frappe.whitelist()
def get_all_currencies(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all currencies (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Currency",
        fields=["name", "currency_name", "symbol", "enabled"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def update_currency(currency_name: Any, currency_data: Any) -> Any:
    """
    Updates a currency (for admins).
    """
    _require_admin()
    if isinstance(currency_data, str):
        currency_data = json.loads(currency_data)

    currency = frappe.get_doc("Currency", currency_name)
    currency.update(currency_data)
    currency.save(ignore_permissions=True)
    return currency.as_dict()


@frappe.whitelist()
def get_email_settings() -> Any:
    """
    Retrieves the email settings (for admins).
    """
    _require_admin()
    return frappe.get_doc("Email Settings").as_dict()


@frappe.whitelist()
def update_email_settings(settings_data: Any) -> Any:
    """
    Updates the email settings (for admins).
    """
    _require_admin()
    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    settings = frappe.get_doc("Email Settings")
    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


@frappe.whitelist()
def get_all_email_templates(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all email templates on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Email Template",
        fields=["name", "subject", "response"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def update_email_template(template_name: Any, template_data: Any) -> Any:
    """
    Updates an email template (for admins).
    """
    _require_admin()
    if isinstance(template_data, str):
        template_data = json.loads(template_data)

    template = frappe.get_doc("Email Template", template_name)
    template.update(template_data)
    template.save(ignore_permissions=True)
    return template.as_dict()


@frappe.whitelist()
def get_email_subscriptions(limit_start: int=0, limit_page_length: int=20) -> Any:
    """
    Retrieves a list of all email subscriptions on the platform (for admins).
    """
    _require_admin()
    return frappe.get_list(
        "Email Subscription",
        fields=["name", "email"],
        offset=limit_start,
        limit=limit_page_length,
    )


@frappe.whitelist()
def create_email_subscription(subscription_data: Any) -> Any:
    """
    Creates a new email subscription (for admins).
    """
    _require_admin()
    if isinstance(subscription_data, str):
        subscription_data = json.loads(subscription_data)

    new_subscription = frappe.get_doc(
        {"doctype": "Email Subscription", **subscription_data}
    )
    new_subscription.insert(ignore_permissions=True)
    return new_subscription.as_dict()


@frappe.whitelist()
def delete_email_subscription(subscription_name: Any) -> Any:
    """
    Deletes an email subscription (for admins).
    """
    _require_admin()
    frappe.delete_doc(
        "Email Subscription", subscription_name, ignore_permissions=True
    )
    return {
        "status": "success",
        "message": "Email subscription deleted successfully.",
    }


@frappe.whitelist()
def get_general_settings() -> Any:
    """
    Retrieves the General Settings (Settings Doctype).
    """
    _require_admin()
    return frappe.get_single("Settings").as_dict()


@frappe.whitelist()
def update_general_settings(settings_data: Any) -> Any:
    """
    Updates the General Settings.
    """
    _require_admin()
    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    settings = frappe.get_single("Settings")
    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()


@frappe.whitelist()
def get_app_settings() -> Any:
    """
    Retrieves the App Settings.
    """
    _require_admin()
    return frappe.get_single("App Settings").as_dict()


@frappe.whitelist()
def update_app_settings(settings_data: Any) -> Any:
    """
    Updates the App Settings.
    """
    _require_admin()
    if isinstance(settings_data, str):
        settings_data = json.loads(settings_data)

    settings = frappe.get_single("App Settings")
    settings.update(settings_data)
    settings.save(ignore_permissions=True)
    return settings.as_dict()
