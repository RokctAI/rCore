import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

@frappe.whitelist()
def dispatch_ai_task(task_type: str, data: dict) -> dict:
    """
    Dispatches tasks to the AI workers.
    """
    trace_id = frappe.form_dict.get("trace_id") or "dispatch-ai-task-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] dispatch_ai_task called with {task_type}\n")
    if isinstance(data, str):
        data = frappe.parse_json(data)
        
    from rcore.services.llm_service import (
        dispatch_ai_task as service_dispatch, 
        BRAIN_QUEUE, 
        VISION_QUEUE, 
        ROUTER_QUEUE
    )

    queue_map = {
        "vision": VISION_QUEUE,
        "rcore": BRAIN_QUEUE,
        "router": ROUTER_QUEUE
    }
    
    queue = queue_map.get(task_type)
    if not queue:
        frappe.throw(f"Invalid Task Type: {task_type}")

    return service_dispatch(queue, data)
