# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def get_ai_result(job_id):
    """
    Polling endpoint for AI worker results.
    """
    import redis
    import json

    r = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")

    result_raw = r.get(f"rokct:result:{job_id}")
    if result_raw:
        return json.loads(result_raw)

    return {"status": "pending"}
