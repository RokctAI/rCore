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


import click
import frappe


def after_install():
    auto_enable_erpnext_integration()
    frappe.db.commit()


def auto_enable_erpnext_integration():
    """
    Automatically enables ERPNext integration if ERPNext is installed.
    This ensures users don't have to manually configure it for thousands of tenants.
    """
    if "erpnext" in frappe.get_installed_apps():
        try:
            settings = frappe.get_doc("ERPNext CRM Settings")
            if not settings.enabled:
                settings.enabled = 1
                # We don't set site URL/keys because we assume same-site integration by default
                # if fields are empty, is_erpnext_in_different_site defaults to
                # 0
                settings.save(ignore_permissions=True)
                click.secho("* Auto-enabled RCRM - ERPNext Integration", fg="green")
        except Exception as e:
            click.secho(
                f"* Failed to auto-enable RCRM - ERPNext Integration: {e}", fg="yellow"
            )
