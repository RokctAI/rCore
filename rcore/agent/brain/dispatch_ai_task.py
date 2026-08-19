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
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient

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

    from rcore.agent.services.llm_service import (
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
