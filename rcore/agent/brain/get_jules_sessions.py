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
import uuid
from rcore import __version__ as brain_version
from rcore.agent.services.jules_service import JulesClient


@frappe.whitelist()
def get_jules_sessions(api_key: str = None) -> dict:
    """
    Retrieve a list of Jules sessions associated with the provided API key.
    If no API key is provided, uses the default credentials configured in the system.
    """
    trace_id = str(uuid.uuid4())

    def log_info(message):
        entry = {"trace_id": trace_id, "message": message, "level": "info"}
        print(json.dumps(entry), file=sys.stderr)

    def log_error(message):
        entry = {"trace_id": trace_id, "message": message, "level": "error"}
        print(json.dumps(entry), file=sys.stderr)

    log_info(f"Fetching Jules sessions with api_key provided: {bool(api_key)}")

    try:
        client = JulesClient()
        result = client.get_sessions(api_key)
        log_info("Successfully retrieved Jules sessions")
        return result
    except Exception as e:
        log_error(f"Failed to retrieve Jules sessions. Error: {str(e)}")
        raise
