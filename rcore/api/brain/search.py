import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def search(module=None, module_group=None, involved_user=None, limit=20):
    """
    A search API for finding relevant Engrams based on metadata.
    """
    if not frappe.session.user:
        frappe.throw("You must be logged in to use this feature.", frappe.PermissionError)
    
    t_engram = frappe.qb.DocType("Engram")
    query = (
        frappe.qb.from_(t_engram)
        .select(t_engram.name, t_engram.reference_doctype, t_engram.reference_name, t_engram.reference_title, t_engram.module, t_engram.summary, t_engram.last_activity_date)
        .orderby(t_engram.last_activity_date, order=frappe.qb.desc)
    )

    if module:
        query = query.where(t_engram.module == module)

    if module_group:
        modules_in_group = frappe.get_all("Module Def", filters={"parent": module_group}, pluck="name")
        if modules_in_group:
             query = query.where(t_engram.module.isin(modules_in_group))
        else:
             return []

    try:
        engrams = query.limit(limit).run(as_dict=True)
        return engrams
    except Exception as e:
        frappe.log_error(f"Brain: Search API failed: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred during the search: {e}")
