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

import frappe

# "rcore" is a template placeholder substituted at install time; resolve
# it dynamically so this file stays valid Python before rendering.
generate_verification_code = frappe.get_attr(
    "rcore.wallet.verification_utils.generate_verification_code"
)


def get_context(context):
    """
    Context generator for the /pay web page.
    Expects order_id, amount, and shop_id in query parameters.
    """
    order_id = frappe.form_dict.get("order_id")
    amount = frappe.form_dict.get("amount")
    shop_id = frappe.form_dict.get("shop_id")

    if not all([order_id, amount, shop_id]):
        context.error = "Invalid Payment Link. Please scan the QR code at the counter again."
        return

    try:
        # Generate the OTP that the customer should show the shop manager
        otp = generate_verification_code(order_id, amount, shop_id)

        context.otp = otp
        context.order_id = order_id
        context.amount = float(amount)
        context.shop_id = shop_id

        # Lookup shop name for better UX
        context.shop_name = (
            frappe.db.get_value("Shop", shop_id, "name_1")
            or "Spazafy Merchant"
        )

        context.status = "Success"

    except Exception as e:
        frappe.log_error(f"OTP Generation Error: {str(e)}", "Payment Verification")
        context.error = (
            "An error occurred while processing your verification code."
        )
