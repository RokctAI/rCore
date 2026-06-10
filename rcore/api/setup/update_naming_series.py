# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe


@frappe.whitelist()
def update_naming_series(series_prefix: str, current: int) -> dict:
    """
    Updates the current sequence number for a given naming series prefix.
    """
    trace_id = frappe.form_dict.get("trace_id") or "update-naming-series-trace"
    import sys

    sys.stderr.write(
        f"[Trace: {trace_id}] update_naming_series called for {series_prefix}\n"
    )
    if not series_prefix or current is None:
        frappe.throw("Series Prefix and Current Value are required.")

    try:
        from frappe.naming.doctype.naming_series.naming_series import update_series

        update_series(series_prefix, int(current))
        return {
            "success": True,
            "message": f"Series {series_prefix} updated to {current}",
        }
    except Exception as e:
        frappe.log_error(f"Failed to update naming series: {str(e)}")
        return {"success": False, "error": str(e)}
