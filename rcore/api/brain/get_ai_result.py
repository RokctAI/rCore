# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_ai_result(job_id: str) -> dict:
    """
    Polling endpoint for AI worker results.
    """
    trace_id = frappe.form_dict.get("trace_id") or "get-ai-result-trace"
    import sys

    sys.stderr.write(f"[Trace: {trace_id}] get_ai_result called for {job_id}\n")
    import redis
    import json

    r = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")

    result_raw = r.get(f"rokct:result:{job_id}")
    if result_raw:
        return json.loads(result_raw)

    return {"status": "pending"}
