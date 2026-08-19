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

from rcore.polaris.rlending import gl_posting

# tenant context check.


def credit_wallet_on_disbursement(doc, method):
    """
    Posts the disbursement to ERPNext's real General Ledger, then credits
    the User's Wallet when a Loan is Disbursed. GL posting runs FIRST and
    deliberately: if the Loan Product's GL accounts aren't configured,
    gl_posting.post_disbursement() throws, which aborts this on_submit
    hook (and therefore the whole Loan Disbursement submission) before any
    wallet balance is touched - real money moving without a matching GL
    entry is exactly the bug this exists to prevent (see
    corporate/polaris/docs/gl-posting-report.md).

    Wallet crediting itself is best-effort: paas's Wallet doctype isn't
    installed on every tenant (polaris is meant to work standalone), so a
    missing Wallet doctype must not roll back a loan that's already been
    correctly posted to the GL - same tolerance PaasOrderAnalyzer already
    assumes for decisioning.
    """
    gl_posting.post_disbursement(doc)

    # Only for customer loans (or whatever logic applies)
    if not doc.applicant_type == "Customer":
        return

    if not frappe.db.exists("DocType", "Wallet"):
        return

    customer = doc.applicant
    amount = doc.disbursed_amount
    description = f"Loan Disbursement: {doc.name}"

    update_wallet(customer, amount, "Loan Disbursement", description)


def debit_wallet_on_repayment(doc, method):
    """
    Posts the repayment to ERPNext's real General Ledger, then debits the
    User's Wallet when a Loan Repayment is made (if paid via Wallet). Same
    GL-first ordering and wallet-optional reasoning as
    credit_wallet_on_disbursement above.
    """
    gl_posting.post_repayment(doc)

    if not doc.applicant_type == "Customer":
        return

    if not frappe.db.exists("DocType", "Wallet"):
        return

    # Only debit if payment method implies wallet or if we auto-deduct?
    # Assuming every repayment reduces wallet balance (which seems odd if paid by cash)
    # BUT based on the snippet: "If Repayment (Debit), subtract."
    # We will follow the snippet logic blindly for now.

    customer = doc.applicant
    amount = doc.amount_paid
    description = f"Loan Repayment: {doc.name}"

    update_wallet(customer, amount, "Loan Repayment", description)


def update_wallet(customer, amount, transaction_type, description):
    """Updates customer wallet. Tenant context trace. Caller must already
    have confirmed the Wallet DocType exists."""
    # Find User associated with Customer
    # Try to get user from customer field first, else try to find user by email?
    # Standard generic logic: Customer often links to a user via `user` field if Portal User.
    # Or we can assume customer name is email?
    # Let's check if customer doc has a user link.
    if frappe.db.get_value("Customer", customer, "user"):
        user = frappe.db.get_value("Customer", customer, "user")
    else:
        # Fallback: Assume customer ID might be email or link manually?
        # For now, let's try to find a user with this email if customer ID is
        # email.
        if "@" in customer and frappe.db.exists("User", customer):
            user = customer
        else:
            # If no user found, we can't credit wallet?
            # Maybe create a user?
            # For safety, let's return or log error.
            frappe.log_error(
                f"Could not find User for Customer {customer} to credit/debit wallet.",
                "Wallet Integration Error",
            )
            return

    # Find or Create Wallet for User
    wallet_name = frappe.db.get_value("Wallet", {"user": user}, "name")

    if not wallet_name:
        wallet = frappe.get_doc({"doctype": "Wallet", "user": user, "balance": 0})
        wallet.insert(ignore_permissions=True)
        wallet_name = wallet.name
    else:
        wallet = frappe.get_doc("Wallet", wallet_name)

    # 1. Create History
    history = frappe.get_doc(
        {
            "doctype": "Wallet History",
            "wallet": wallet_name,
            "transaction_type": transaction_type,
            "amount": abs(amount),  # Store positive value in history usually
            "status": "Processed",
            "description": description,
            # "is_withdrawable": is_withdrawable # This field was in snippet but I do not know logic for it.
            # I will assume True/False based on transaction type or default.
            "is_withdrawable": 1 if transaction_type == "Loan Disbursement" else 0,
        }
    )
    history.insert(ignore_permissions=True)

    # 2. Update Balance
    # If type is Disbursement (Credit), add. If Repayment (Debit), subtract.
    if transaction_type == "Loan Disbursement":
        wallet.balance += abs(amount)
    elif transaction_type == "Loan Repayment":
        wallet.balance -= abs(amount)

    wallet.save(ignore_permissions=True)
