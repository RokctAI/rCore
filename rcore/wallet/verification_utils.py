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

import hashlib
import frappe


def generate_verification_code(order_id, amount, shop_id):
    """
    Generates a 5-digit verification code using SHA-256 and a shared secret.
    This logic MUST match the Flutter PayVerificationHelper implementation.
    """
    # Fetch shop-specific secret from DB, fallback to legacy if not set
    shared_secret = frappe.db.get_value("Shop", shop_id, "shared_secret")
    if not shared_secret:
        frappe.throw(
            f"Shop {shop_id} does not have a secure secret configured."
        )

    # Normalize amount to 2 decimal places as string
    normalized_amount = "{:.2f}".format(float(amount))

    # Create the raw string: "order_id|amount|shop_id|secret"
    raw_string = f"{order_id}|{normalized_amount}|{shop_id}|{shared_secret}"

    # Generate SHA-256 hash
    digest = hashlib.sha256(raw_string.encode("utf-8")).digest()

    # Take the first 4 bytes and convert to big-endian integer (matching
    # Flutter)
    hash_int = int.from_bytes(digest[:4], byteorder="big")

    # Use modulo and absolute value to get 5 digits, pad with zeros
    # Note: Python's int.from_bytes from big endian is always positive, but we
    # use abs for safety
    code = abs(hash_int) % 100000

    return str(code).zfill(5)
