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


def block_second_company(doc, method=None):
    """Enforce the platform invariant of exactly one Company per tenant site.

    Provisioning creates the single Company for a tenant site
    (base.core.initial_setup), but the first tenant user holds System Manager,
    which the Company doctype grants create on. A second Company on the same
    site would be invisible to billing (one Company Subscription per site) and
    ignored by onboarding/plan logic, while ERPNext would still mix its data
    into site-wide reports. Wired as a before_insert doc_event on Company.
    """
    try:
        # Tenant sites are marked by app_role in site config; hub/control and
        # dev benches carry other roles (or none) and are never restricted.
        is_tenant_site = frappe.conf.get("app_role") == "tenant"
        company_exists = is_tenant_site and frappe.db.count("Company") > 0
    except Exception:
        # Fail open: a broken detection check must never block Company
        # creation (e.g. on non-tenant benches with unusual site config).
        frappe.log_error(
            f"Company guard could not determine site role: {frappe.get_traceback()}",
            "Company Guard Check Skipped",
        )
        return

    if not company_exists:
        # Covers non-tenant sites and the first (provisioning-time) Company.
        return

    frappe.throw(
        "This site already has a company, and each site supports exactly one. "
        "Creating another company here would not be covered by your "
        "subscription and is not supported. To run an additional company, "
        "please sign up for a separate site (plan) for it.",
        title="One Company Per Site",
    )
