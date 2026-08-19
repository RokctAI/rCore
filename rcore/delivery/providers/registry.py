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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Resolves the configured intercity provider for a booking.

Inert by default: unless ``enable_intercity`` is switched on in
Delivery Provider Settings AND the active provider is fully configured,
``get_provider`` raises -- it never returns a placeholder provider.
"""

import frappe
from frappe.utils import cint

from .base import IntercityDisabledError, ProviderNotConfiguredError
from .shiprazor import ShipRazorProvider

SETTINGS_DOCTYPE = "Delivery Provider Settings"

PROVIDERS = {
    ShipRazorProvider.name: ShipRazorProvider,
}


def get_settings():
    return frappe.get_single(SETTINGS_DOCTYPE)


def is_intercity_enabled(settings=None):
    settings = settings or get_settings()
    return bool(cint(settings.get("enable_intercity") or 0))


def get_provider(name=None, settings=None):
    """Resolve a fully configured provider or raise a typed error."""
    settings = settings or get_settings()
    if not is_intercity_enabled(settings):
        raise IntercityDisabledError(
            "Intercity delivery is disabled. Enable it in Delivery Provider "
            "Settings once a provider contract is in place."
        )
    name = (name or settings.get("active_provider") or "").strip()
    if not name:
        raise ProviderNotConfiguredError(
            "No intercity provider is configured. Set 'Active Provider' in "
            "Delivery Provider Settings."
        )
    provider_class = PROVIDERS.get(name)
    if provider_class is None:
        supported = ", ".join(sorted(PROVIDERS))
        raise ProviderNotConfiguredError(
            f"Unknown intercity provider '{name}'. Supported: {supported}."
        )
    provider = provider_class(settings)
    provider.validate_configured()
    return provider
