import json
import frappe
import sys
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def semantic_search(query: str, limit: int = 5, involved_user: str = None) -> list:
    """
    Performs vector similarity search using pgvector.
    raw_sql
    """
    trace_id = frappe.form_dict.get("trace_id") or "semantic-search-trace"
    sys.stderr.write(f"[Trace: {trace_id}] semantic_search called with query={query}\n")

    if not frappe.session.user:
        frappe.throw("Authentication Required", frappe.PermissionError)
        
    from rcore.services.llm_service import embed_text
    
    vector = embed_text(query)
    if not vector:
        return []
        
    conditions = ""
    params = [str(vector), limit]
    
    if involved_user:
        conditions += " AND involved_users LIKE %s"
        params.insert(1, f"%{involved_user}%")
        
    sql = f"""
        SELECT 
            name, reference_doctype, reference_name, reference_title, summary, 
            (embedding <=> %s) as distance
        FROM "tabEngram"
        WHERE embedding IS NOT NULL {conditions}
        ORDER BY distance ASC
        LIMIT %s
    """
    
    results = frappe.db.sql(sql, tuple(params), as_dict=True)
    return results
