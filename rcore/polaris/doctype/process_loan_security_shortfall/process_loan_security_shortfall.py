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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class ProcessLoanSecurityShortfall(Document):
    """
    Polaris's own Process Loan Security Shortfall doctype - forked from
    Frappe Lending's orchestrator (Phase 5), kept as a record-only shell.
    `on_submit` intentionally does nothing beyond marking itself Completed -
    upstream's `check_for_ltv_shortfall` is not ported (see
    loan_security_shortfall.py's docstring). This exists so
    `RokctAI_frontend`'s `operations.ts:runSecurityShortfallCheck` and
    `getProcessLogs` calls succeed and produce a real audit trail, without
    fabricating collateral-valuation logic Polaris has no data model for.
    """

    def validate(self):
        if not self.update_time:
            self.update_time = get_datetime()

    def on_submit(self):
        self.db_set("status", "Completed")


def create_process_loan_security_shortfall():
    """
    Whitelisted entry point matching upstream's real function shape. Only
    creates a record if any secured loans exist - matches upstream's
    `check_for_secured_loans()` gate, adapted to check `Loan.is_secured_loan`
    only (Polaris has no `Loan Security Assignment` doctype to also check).
    """
    if frappe.db.count("Loan", {"docstatus": 1, "is_secured_loan": 1}):
        process = frappe.new_doc("Process Loan Security Shortfall")
        process.update_time = get_datetime()
        process.submit()
        return process.name
    return None
