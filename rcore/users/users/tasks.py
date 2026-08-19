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

import frappe
from frappe.utils import now_datetime, add_days, nowdate

def disable_expired_support_users():
    if frappe.conf.get("app_role") != "tenant": return
    expired_users = frappe.get_all("User", filters={"enabled": 1, "temporary_user_expires_on": ["<", now_datetime()]}, fields=["name", "email"])
    for user_info in expired_users:
        try:
            user = frappe.get_doc("User", user_info.name)
            user.enabled = 0
            user.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Failed to disable expired user {user_info.email}: {e}")

def archive_inactive_vault_files():
    if frappe.conf.get("app_role") != "tenant": return
    ninety_days_ago = add_days(nowdate(), -90)
    expired_tenants = frappe.get_all("User", filters={
        "enabled": 0,
        "temporary_user_expires_on": ["<", ninety_days_ago]
    }, fields=["name", "email"])

    for tenant in expired_tenants:
        files = frappe.get_all("File", filters={"owner": tenant.name}, fields=["name"])
        for f in files:
            try:
                frappe.delete_doc("File", f.name, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Failed to archive/delete file {f.name} for {tenant.email}: {e}")
    frappe.db.commit()
