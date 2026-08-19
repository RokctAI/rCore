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

import json
import frappe
import sys
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient

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

    from rcore.agent.services.llm_service import embed_text

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
