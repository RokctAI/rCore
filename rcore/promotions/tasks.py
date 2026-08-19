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
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
import frappe
from frappe.utils import now_datetime
from datetime import datetime


@frappe.whitelist()
def remove_expired_stories() -> Any:
    """
    Find and delete stories that have expired.
    This is run daily by the scheduler on tenant sites.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    if frappe.conf.get("app_role") != "tenant":
        return

    print("Running Daily Expired Stories Cleanup Job...")

    expired_stories = frappe.get_all("Story",
                                     filters={
                                         "expires_at": ["<", now_datetime()]
                                     },
                                     pluck="name"
                                     )

    if not expired_stories:
        print("No expired stories to delete.")
        return

    print(f"Found {len(expired_stories)} expired stories to delete...")

    for story_name in expired_stories:
        try:
            frappe.delete_doc(
                "Story",
                story_name,
                ignore_permissions=True,
                force=True)
            print(f"  - Deleted expired story: {story_name}")
        except Exception:
            frappe.log_error(frappe.get_traceback(),
                             f"Failed to delete expired story {story_name}")

    frappe.db.commit()
    print("Expired Stories Cleanup Job Complete.")


@frappe.whitelist()
def process_repeating_orders() -> Any:
    """
    The process_repeating_orders function is designed to process repeating orders that are due for execution. It fetches active repeating orders where the next execution is due or not set, and then attempts to create a new order based on the original order associated with the repeating order. The function processes payment for the new order using either the user's wallet or a saved card, and updates the order status accordingly. If payment fails, the function notifies the user. The function also calculates the next execution date for the repeating order and updates the repeating order's last execution and next execution dates. Additionally, the function cleans up any expired repeating orders by setting their status to inactive. The function does not take any parameters.
    """
    import sys; _ = (frappe.request.headers.get("x-trace-id") if (hasattr(frappe, "request") and frappe.request) else None, sys.stderr)
    trace_id = None
    """
    Process repeating orders that are due for execution.
    trace/tenant isolation context.
    """
    try:
        from croniter import croniter
    except ImportError:
        print("croniter not found. Skipping repeating orders.")
        return

    print("Processing Repeating Orders...")
    now = now_datetime()

    # Fetch active repeating orders where next_execution is due or not set
    # (first run)
    repeating_orders = frappe.get_all(
        "Repeating Order",
        filters={
            "is_active": 1,
            "start_date": [
                "<=",
                now.date()],
            "next_execution": [
                "<=",
                now]},
        fields=[
            "name",
            "user",
            "original_order",
            "cron_pattern",
            "next_execution",
            "end_date",
            "payment_method",
            "saved_card",
            "ringfenced_amount"])

    count = 0
    for ro in repeating_orders:
        if ro.end_date and ro.end_date < now.date():
            # Expired
            frappe.db.set_value("Repeating Order", ro.name, "is_active", 0)
            continue

        try:
            # Set context to the user who owns the repeating order for payment
            # processing
            frappe.set_user(ro.user)

            # Create the order doc (don't insert yet, we need to verify
            # payment)
            original_order_doc = frappe.get_doc("Order", ro.original_order)
            new_order = frappe.copy_doc(original_order_doc)
            new_order.transaction_date = now
            new_order.delivery_date = now.date()
            new_order.amended_from = None

            # Initial status is "Draft" or "Payment Failed" until payment
            # succeeds
            new_order.status = "Payment Failed"
            new_order.payment_status = "Pending"

            # Process Payment
            payment_success = False
            if ro.payment_method == "Wallet":
                if ro.ringfenced_amount >= new_order.grand_total:
                    # Use Ringfenced funds
                    user_doc = frappe.get_doc("User", ro.user)
                    user_doc.set(
                        "ringfenced_balance",
                        (user_doc.get("ringfenced_balance") or 0.0) -
                        new_order.grand_total)
                    user_doc.save(ignore_permissions=True)

                    # Update RO
                    frappe.db.set_value(
                        "Repeating Order",
                        ro.name,
                        "ringfenced_amount",
                        ro.ringfenced_amount -
                        new_order.grand_total)

                    new_order.payment_status = "Paid"
                    new_order.status = "New"
                    payment_success = True

                    # Log Capture Transaction
                    transaction = frappe.get_doc({
                        "doctype": "Transaction",
                        "user": ro.user,
                        "amount": -new_order.grand_total,
                        "status": "Success",
                        "type": "Wallet Capture",
                        "reference_doctype": "Repeating Order",
                        "reference_docname": ro.name
                    })
                    transaction.insert(ignore_permissions=True)
                else:
                    print(f"Insufficient ringfenced funds for {ro.name}")

            elif ro.payment_method == "Saved Card" and ro.saved_card:
                try:
                    from rcore.wallet.api.payment.payment import process_token_payment
                    card = frappe.get_doc("Saved Card", ro.saved_card)
                    # This method inserts the order if it hasn't been already, or we can insert first.
                    # Here we insert first to provide the ID to the payment
                    # processor.
                    new_order.insert(ignore_permissions=True)
                    res = process_token_payment(new_order.name, card.token)
                    if res.get("status") == "success":
                        payment_success = True
                except Exception as e:
                    print(f"Card payment failed for {new_order.name}: {e}")

            if not payment_success:
                # If order wasn't inserted by card logic yet
                if not new_order.name:
                    new_order.insert(ignore_permissions=True)

                print(
                    f"Payment failed for order {
                        new_order.name}. Order status set to {
                        new_order.status}")

                # Notify User
                try:
                    from rcore.comms.api.notification.notification import send_push_notification
                    send_push_notification(
                        user=ro.user,
                        title="Auto-Order Payment Failed",
                        body=f"Your repeating order for {
                            new_order.shop} could not be paid. Please pay manually or check your wallet.",
                        data={
                            "order_id": new_order.name,
                            "type": "payment_failed"})
                except Exception:
                    pass
            else:
                # If Wallet payment succeeded, order might not be inserted yet
                if not new_order.name:
                    new_order.insert(ignore_permissions=True)
                print(f"Payment successful for order {new_order.name}")

            count += 1

            # Calculate next execution
            iter = croniter(ro.cron_pattern, now)
            next_exec = iter.get_next(datetime)

            frappe.db.set_value("Repeating Order", ro.name, {
                "last_execution": now,
                "next_execution": next_exec
            })

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Failed to process Repeating Order {
                    ro.name}")
        finally:
            # Reset user context to Administrator/System
            frappe.set_user("Administrator")

    if count > 0:
        frappe.db.commit()
    print(f"Processed {count} repeating orders.")

    # Cleanup: Find paused or active orders that have expired and ensure they
    # are inactive
    expired_ro = frappe.get_all("Repeating Order",
                                filters={
                                    "is_active": 1,
                                    "end_date": ["<", now.date()]
                                },
                                pluck="name"
                                )
    for ro_name in expired_ro:
        frappe.db.set_value("Repeating Order", ro_name, "is_active", 0)

    if expired_ro:
        frappe.db.commit()
        print(f"Cleaned up {len(expired_ro)} expired auto-orders.")
