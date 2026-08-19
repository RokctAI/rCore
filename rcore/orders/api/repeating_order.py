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

from typing import Any, Optional
# Repeating Order API
import frappe
from croniter import croniter
from datetime import datetime


def calculate_ringfence_amount(
    cron_pattern, start_date_str, end_date_str, unit_price
):
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        # Default to 4 weeks if no end date
        from datetime import timedelta

        end_date = start_date + timedelta(days=28)

    iter = croniter(cron_pattern, start_date)
    count = 0
    while True:
        next_dt = iter.get_next(datetime)
        if next_dt > end_date:
            break
        count += 1

    return count * unit_price


@frappe.whitelist()
def create_repeating_order(original_order: str, start_date: str, cron_pattern: str, end_date: str=None, payment_method: str='Wallet', saved_card: str=None, lang: str='en') -> Any:
    """
    The create_repeating_order function creates a new repeating order based on an existing order, with specified payment preferences and ringfencing. It takes several parameters: original_order, the identifier of the original order; start_date, the date when the repeating order starts; cron_pattern, a cron expression defining the repetition schedule; end_date, an optional date when the repeating order ends; payment_method, the payment method to use, defaulting to 'Wallet'; saved_card, an optional saved card identifier; and lang, the language, defaulting to 'en'. The function enforces the use of the 'Wallet' payment method for auto-orders and handles ringfencing of the order amount in the user's wallet balance. It returns the newly created repeating order as a dictionary.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Creates a new repeating order with payment preferences and ringfencing.
    Note: Payment method is enforced to 'Wallet' for auto-orders.
    trace context
    """
    user = frappe.session.user
    order_doc = frappe.get_doc("Order", original_order)

    # Enforce Wallet for Auto Orders
    payment_method = "Wallet"

    ringfenced_amount = 0
    if payment_method == "Wallet":
        ringfenced_amount = calculate_ringfence_amount(
            cron_pattern, start_date, end_date, order_doc.grand_total
        )
        user_doc = frappe.get_doc("User", user)

        balance = user_doc.get("wallet_balance") or 0.0
        if balance < ringfenced_amount:
            # Specific error message for frontend interception
            frappe.throw(
                f"Insufficient Wallet Balance. Required: {ringfenced_amount}, Available: {balance}. Suggest Topup")

        # Ringfence
        user_doc.set("wallet_balance", balance - ringfenced_amount)
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) + ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

        # Log Transaction
        transaction = frappe.get_doc(
            {
                "doctype": "Transaction",
                "user": user,
                "amount": -ringfenced_amount,
                "status": "Success",
                "type": "Wallet Reservation",
                "reference_doctype": "Order",
                "reference_docname": original_order,
            }
        )
        transaction.insert(ignore_permissions=True)

    repeating_order = frappe.get_doc(
        {
            "doctype": "Repeating Order",
            "user": frappe.session.user,
            "original_order": original_order,
            "start_date": start_date,
            "cron_pattern": cron_pattern,
            "end_date": end_date,
            "payment_method": payment_method,
            "saved_card": saved_card,
            "ringfenced_amount": ringfenced_amount,
            "is_active": 1,
        }
    )
    repeating_order.insert(ignore_permissions=True)
    return repeating_order.as_dict()


@frappe.whitelist()
def pause_repeating_order(repeating_order_id: str, lang: str='en') -> Any:
    """
    pause_repeating_order pauses a specific repeating order and, if applicable, releases any funds that were ring‑fenced for that order back to the user’s wallet.  
    
    Parameters  
    - repeating_order_id (str): The unique identifier of the Repeating Order document to be paused.  
    - lang (str, optional): Language code for any localized messages; defaults to 'en'.  
    
    The function checks that the order is active, uses the wallet payment method, and has a positive ring‑fenced amount. When those conditions are met it transfers the ring‑fenced amount from the user’s ring‑fenced balance to their wallet balance, records a “Wallet Release” transaction, clears the ring‑fenced amount, deactivates the order, and returns a success response indicating the order has been paused and funds released.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Pauses a repeating order and releases ringfenced funds.
    trace context
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)
    if (
        ro.is_active
        and ro.payment_method == "Wallet"
        and ro.ringfenced_amount > 0
    ):
        user_doc = frappe.get_doc("User", ro.user)
        user_doc.set(
            "wallet_balance",
            (user_doc.get("wallet_balance") or 0.0) + ro.ringfenced_amount,
        )
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) - ro.ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

        # Log Release Transaction
        transaction = frappe.get_doc(
            {
                "doctype": "Transaction",
                "user": ro.user,
                "amount": ro.ringfenced_amount,
                "status": "Success",
                "type": "Wallet Release",
                "reference_doctype": "Repeating Order",
                "reference_docname": repeating_order_id,
            }
        )
        transaction.insert(ignore_permissions=True)

        ro.ringfenced_amount = 0

    ro.is_active = 0
    ro.save(ignore_permissions=True)
    return {"status": "success", "message": "Order paused and funds released"}


@frappe.whitelist()
def resume_repeating_order(repeating_order_id: str, lang: str='en') -> Any:
    """
    The resume_repeating_order function resumes a previously paused repeating order and re-ringfences the necessary funds. It takes two parameters: repeating_order_id, which is the unique identifier of the repeating order to be resumed, and lang, which specifies the language to be used and defaults to English if not provided. The function checks if the order has expired, and if the payment method is Wallet, it recalculates the ringfence amount based on the remaining schedule and updates the user's wallet balance accordingly. If the user's balance is insufficient, it throws an error. Otherwise, it resumes the order, saves the changes, and returns a success message.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Resumes a repeating order and re-ringfences funds.
    trace context
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)

    # Check for expiration before resuming
    if ro.end_date and ro.end_date < datetime.now().date():
        frappe.throw(
            "This auto-order schedule has already ended and cannot be resumed."
        )

    if not ro.is_active and ro.payment_method == "Wallet":
        order_doc = frappe.get_doc("Order", ro.original_order)
        # Re-calculate based on remaining schedule (from now)
        now_str = datetime.now().strftime("%Y-%m-%d")
        new_ringfence = calculate_ringfence_amount(
            ro.cron_pattern, now_str, ro.end_date, order_doc.grand_total
        )

        user_doc = frappe.get_doc("User", ro.user)
        balance = user_doc.get("wallet_balance") or 0.0

        if balance < new_ringfence:
            frappe.throw(
                "Insufficient Wallet Balance to resume this schedule."
            )

        user_doc.set("wallet_balance", balance - new_ringfence)
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) + new_ringfence,
        )
        user_doc.save(ignore_permissions=True)

        ro.ringfenced_amount = new_ringfence

    ro.is_active = 1
    ro.save(ignore_permissions=True)
    return {"status": "success", "message": "Order resumed and funds reserved"}


@frappe.whitelist()
def delete_repeating_order(repeating_order_id: str, lang: str='en') -> Any:
    """
    The delete_repeating_order function is used to delete a repeating order and release any remaining ringfenced funds associated with it. It takes two parameters: repeating_order_id, which is a string representing the ID of the repeating order to be deleted, and lang, which is an optional string parameter that specifies the language, defaulting to 'en' if not provided. The function retrieves the repeating order document, checks if there are any ringfenced funds, and if so, updates the user's wallet balance and ringfenced balance accordingly before deleting the repeating order document.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Deletes a repeating order and releases any remaining ringfenced funds.
    trace context
    """
    ro = frappe.get_doc("Repeating Order", repeating_order_id)
    if ro.ringfenced_amount > 0 and ro.payment_method == "Wallet":
        user_doc = frappe.get_doc("User", ro.user)
        user_doc.set(
            "wallet_balance",
            (user_doc.get("wallet_balance") or 0.0) + ro.ringfenced_amount,
        )
        user_doc.set(
            "ringfenced_balance",
            (user_doc.get("ringfenced_balance") or 0.0) - ro.ringfenced_amount,
        )
        user_doc.save(ignore_permissions=True)

    frappe.delete_doc(
        "Repeating Order", repeating_order_id, ignore_permissions=True
    )
    return {"status": "success"}
