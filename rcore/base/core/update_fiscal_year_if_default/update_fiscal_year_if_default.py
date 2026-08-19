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
import frappe
import os
import json
import pytz
import requests
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import validate_email_address, get_url, nowdate
from frappe.utils.data import add_days, getdate
from frappe.utils.install import complete_setup_wizard
from rcore.comms.tenant_utils import send_tenant_email
from rcore.tenant.api.helpers import *


def update_fiscal_year_if_default(start_date: Any) -> Any:
    """
    Updates the default fiscal year for the site's company. Setup and tenant context trace.
    """
    # --- Security Check ---
    # This function is intended to be called via `bench execute` from the control panel.
    # In this context, there are no request headers. The security is implicit because
    # only an admin with shell access to the control panel can trigger the
    # master script.
    if hasattr(frappe.local, "request"):
        api_secret = frappe.conf.get("api_secret")
        received_secret = frappe.local.request.headers.get("X-Rokct-Secret")
        if not received_secret or received_secret != api_secret:
            frappe.throw("Authentication failed.", frappe.AuthenticationError)

    if not start_date:
        frappe.throw(
            "`start_date` is a required parameter.", title="Missing Information"
        )

    try:
        # 1. Get the default company for the site.
        company_name = frappe.db.get_single_value("Global Defaults", "default_company")
        if not company_name:
            return {
                "status": "skipped",
                "message": "No default company set for this site.",
            }

        company = frappe.get_doc("Company", company_name)
        current_fiscal_year_name = company.default_fiscal_year

        if not current_fiscal_year_name:
            return {
                "status": "skipped",
                "message": f"Company '{company_name}' has no default fiscal year set.",
            }

        # 2. Check the start date of the current fiscal year.
        current_fy_doc = frappe.get_doc("Fiscal Year", current_fiscal_year_name)
        print(f"DEBUG: Current fiscal year is '{current_fiscal_year_name}' with start date {current_fy_doc.year_start_date}")

        # We identify the old, incorrect default by checking if the start date
        # is January 1st.
        if (
            current_fy_doc.year_start_date.month == 1
            and current_fy_doc.year_start_date.day == 1
        ):
            print(
                f"INFO: Current fiscal year starts on January 1st. Proceeding with correction."
            )
            # 3. Create the new, correct fiscal year.
            new_start_date = getdate(start_date)
            new_year = new_start_date.year
            new_year_name = f"FY {new_year}"
            new_year_end_date = add_days(new_start_date, 364)

            if not frappe.db.exists("Fiscal Year", new_year_name):
                frappe.get_doc(
                    {
                        "doctype": "Fiscal Year",
                        "year": new_year_name,
                        "year_start_date": new_start_date,
                        "year_end_date": new_year_end_date,
                    }
                ).insert(ignore_permissions=True)
                message = f"Created new fiscal year '{new_year_name}'."
            else:
                message = f"Fiscal year '{new_year_name}' already exists."

            # 4. Set the new fiscal year as the default.
            company.default_fiscal_year = new_year_name
            company.save(ignore_permissions=True)
            frappe.db.commit()

            return {
                "status": "success",
                "message": f"{message} Set '{new_year_name}' as default for company '{company_name}'.",
            }
        else:
            # The start date is not Jan 1st, so we assume the tenant has
            # customized it.
            return {
                "status": "skipped",
                "message": f"Fiscal year for '{company_name}' was not the default. No changes made.",
            }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "Fiscal Year Correction Failed")
        raise
