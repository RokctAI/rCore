import frappe

@frappe.whitelist()
def update_naming_series(series_prefix, current):
    """
    Updates the current sequence number for a given naming series prefix.
    """
    if not series_prefix or current is None:
        frappe.throw("Series Prefix and Current Value are required.")
        
    try:
        from frappe.naming.doctype.naming_series.naming_series import update_series
        update_series(series_prefix, int(current))
        return {"success": True, "message": f"Series {series_prefix} updated to {current}"}
    except Exception as e:
        frappe.log_error(f"Failed to update naming series: {str(e)}")
        return {"success": False, "error": str(e)}
