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


@frappe.whitelist(allow_guest=True)
def get_languages(active: Any=True) -> Any:
    """
    Retrieves list of languages.
    """
    filters = {}
    if active:
        filters["active"] = 1

    return frappe.get_list(
        "PaaS Language",
        filters=filters,
        fields=[
            "name",
            "title",
            "locale",
            "backward",
            "default",
            "active",
            "img",
        ],
    )


@frappe.whitelist(allow_guest=True)
def get_default_language() -> Any:
    """
    Retrieves the default language.
    """
    return frappe.get_doc("PaaS Language", {"default": 1}).as_dict()


@frappe.whitelist(allow_guest=True)
def get_translations(locale: Any, group: Any=None) -> Any:
    """
    Retrieves translations for a specific locale, optionally filtered by group.
    Returns a dictionary mapping keys to values, as expected by many frontends.
    """
    filters = {"locale": locale, "status": 1}
    if group:
        filters["group"] = group

    translations = frappe.get_list(
        "PaaS Translation", filters=filters, fields=["key", "value", "group"]
    )

    # Transform into nested dict if needed, or flat key-value pairs
    result = {}
    for t in translations:
        if group:
            result[t.key] = t.value
        else:
            if t.group not in result:
                result[t.group] = {}
            result[t.group][t.key] = t.value

    return result
