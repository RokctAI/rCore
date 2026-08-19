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
from frappe import _
from frappe.model.document import Document


class LoanRefund(Document):
    """
    Polaris's own Loan Refund doctype - forked from Frappe Lending's
    `Loan Refund` (Phase 4). Plain Document, no GL posting (Phase 0 decision).

    Deliberately does NOT mutate Loan's principal/balance fields on submit:
    a refund (excess payment or security deposit return) is a payout of funds
    already collected, not a change to what's owed on the loan - there's no
    evidence anywhere in rlending of a wallet/cash-side effect being wired up
    for refunds today (no doc_event hook exists for this doctype, unlike
    Disbursement/Repayment), so this stays record-only pending that being
    scoped as real work.
    """

    def validate(self):
        if not self.refund_amount:
            frappe.throw(_("Refund Amount is mandatory"))
        if not frappe.db.exists("Loan", self.loan):
            frappe.throw(_("Loan {0} does not exist").format(self.loan))
        if not (self.is_excess_amount_refund or self.is_security_amount_refund):
            frappe.throw(_("Select either Excess Amount Refund or Security Amount Refund"))
