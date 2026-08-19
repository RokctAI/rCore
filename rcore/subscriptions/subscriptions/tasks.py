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
from frappe.utils import nowdate, add_days

def reset_monthly_token_usage():
    if frappe.conf.get("app_role") != "tenant": return
    today = nowdate()
    thirty_days_ago = add_days(today, -30)
    trackers_to_reset = frappe.get_all("Token Usage Tracker", filters={"period_start_date": ("<=", thirty_days_ago)}, fields=["name"])
    for item in trackers_to_reset:
        try:
            tracker = frappe.get_doc("Token Usage Tracker", item.name)
            tracker.current_period_usage = 0
            tracker.period_start_date = today
            tracker.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to reset token tracker: {e}", "Token Usage Job Failed")
    frappe.db.commit()

def update_storage_usage():
    if frappe.conf.get("app_role") != "tenant": return
    try:
        total_size_bytes = frappe.db.sql("SELECT SUM(file_size) FROM `tabFile`")[0][0] or 0
        total_size_mb = total_size_bytes / (1024 * 1024)
        storage_tracker = frappe.get_doc("Storage Tracker")
        storage_tracker.current_storage_usage_mb = total_size_mb
        storage_tracker.save(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Storage usage calculation failed: {e}", "Storage Usage Job Failed")
