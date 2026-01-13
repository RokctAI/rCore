# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.core.doctype.file.file import File as FrappeFile

class CustomFile(FrappeFile):
    def validate(self):
        # First, call the standard validation from the parent class
        super(CustomFile, self).validate()

        # Only apply quota checks on tenant sites and when a new file is being inserted
        if frappe.conf.get("app_role") != "tenant" or self.is_new() is False:
            return

        # Attempt to get subscription details from the cache
        try:
            from core.tenant.api import get_subscription_details
            subscription_details = get_subscription_details()
        except Exception as e:
            frappe.log_error(f"Could not fetch subscription details during file upload: {e}", "Storage Quota Check Ignored")
            # Fail open: If we can't get subscription details, allow the upload to prevent blocking the user.
            return

        storage_quota_gb = subscription_details.get("storage_quota_gb", 0)

        # A quota of 0 or less means unlimited storage
        if not storage_quota_gb or storage_quota_gb <= 0:
            return

        # Get the pre-calculated storage usage from the singleton
        # Convert from MB to Bytes for an accurate comparison
        current_usage_bytes = (frappe.db.get_single_value("Storage Tracker", "current_storage_usage_mb") or 0) * (1024**2)
        quota_in_bytes = storage_quota_gb * (1024**3)
        new_file_size_bytes = self.file_size

        if (current_usage_bytes + new_file_size_bytes) > quota_in_bytes:
            # Format numbers for readability in the error message
            usage_in_gb = round(current_usage_bytes / (1024**3), 2)
            frappe.throw(
                f"Storage quota exceeded. Your current usage is approximately {usage_in_gb} GB out of {storage_quota_gb} GB. "
                "Please delete some files or upgrade your plan to upload new files.",
                title="Storage Limit Reached"
            )
