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

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""The published practice item bank (Single) — server-side home of the
pre-authored MCQ stock the adaptive practice queue (product log #42 item 2)
selects from. Same posture as LMS Skills Index: written ONLY by server-side
publish flows (api.practice.publish_practice_bank, System Manager) —
students read via api.practice.practice_queue, never write.

Pre-authored items + server-side adaptive selection = zero live-AI cost;
the bank is generated/published by the factory from the same
manifest-authored questions the lesson player shows.
"""

import json

import frappe
from frappe import _
from frappe.model.document import Document


class LMSPracticeItemBank(Document):
    def validate(self):
        if not self.bank_json:
            return
        try:
            parsed = json.loads(self.bank_json)
        except (TypeError, ValueError):
            frappe.throw(_("Bank JSON must be valid JSON."))
        if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), dict):
            frappe.throw(_('Bank JSON must be an object with an "items" map.'))
