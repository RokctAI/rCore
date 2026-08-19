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

# Tenant context: session.user validation
# Copyright (c) 2025 ROKCT Holdings
# For license information, please see license.txt
import frappe


def execute():
    # Find the "Backend" roadmap
    if not frappe.db.exists("Roadmap", "Backend"):
        return

    backend_roadmap = frappe.get_doc("Roadmap", "Backend")

    # Update the status of the features
    for feature in backend_roadmap.features:
        if feature.feature == "Auth: Forgot Password":
            feature.status = "Done"
        elif feature.feature == "Auth: Logout":
            feature.status = "Doing"

    backend_roadmap.save(ignore_permissions=True)
    frappe.db.commit()
