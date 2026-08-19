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
from frappe.utils import nowdate


class PledgedAsset(Document):
    """
    Single physical asset pledged against a Loan (secured-lending-brief.md).
    Deliberately not a portfolio/multi-asset structure - one Pledged Asset
    per Loan (enforced via the `loan` field's unique constraint), no LTV,
    no revaluation. See the doctype's own description for why status
    history uses track_changes + add_comment() rather than a bespoke log.
    """

    def validate(self):
        if not self.description:
            frappe.throw(_("Description is mandatory"))
        if not frappe.db.exists("Loan", self.loan):
            frappe.throw(_("Loan {0} does not exist").format(self.loan))


def create_from_application(loan_name, loan_application_name):
    """
    Called from api/loan.py's disburse_loan() when a secured loan is
    disbursed. Copies the collateral description captured at application
    time (RokctAI_frontend/app/handson/all/lending/application/new/page.tsx's
    `description` field - confirmed by reading that page directly, not
    guessed) onto a new Pledged Asset linked to the resulting Loan.
    Idempotent - returns the existing record if one already exists for this
    loan rather than erroring or duplicating.
    """
    existing = frappe.db.get_value("Pledged Asset", {"loan": loan_name}, "name")
    if existing:
        return existing

    app_doc = frappe.get_doc("Loan Application", loan_application_name)
    if not app_doc.get("description"):
        frappe.throw(
            _(
                "Loan Application {0} is marked as a secured loan but has no collateral "
                "description - cannot create the Pledged Asset record."
            ).format(loan_application_name)
        )

    asset = frappe.new_doc("Pledged Asset")
    asset.loan = loan_name
    asset.loan_application = loan_application_name
    asset.applicant_type = app_doc.applicant_type
    asset.applicant = app_doc.applicant
    asset.description = app_doc.description
    asset.declared_value = app_doc.get("declared_asset_value")
    asset.status = "Pledged"
    asset.pledged_date = nowdate()
    asset.insert(ignore_permissions=True)
    return asset.name


def trigger_repossession_flag(loan_name):
    """
    Called from process_loan_classification.py's update_loan_classification()
    when a secured loan becomes NPA. Signal only - does NOT execute
    repossession and does NOT touch the loan's financials. A human must
    separately call realise_pawn_asset() (asset_realisation.py) to actually
    execute repossession - see secured-lending-brief.md's explicit "don't
    make it silently automatic" instruction. No-op if there's no Pledged
    Asset for this loan, or it's already past the "Pledged" stage.
    """
    asset_name = frappe.db.get_value("Pledged Asset", {"loan": loan_name, "status": "Pledged"}, "name")
    if not asset_name:
        return

    asset = frappe.get_doc("Pledged Asset", asset_name)
    asset.db_set("status", "Repossession Triggered")
    asset.db_set("repossession_triggered_date", nowdate())
    asset.add_comment(
        "Info",
        _(
            "Repossession triggered automatically: Loan {0} moved to NPA status. This is a "
            "signal only - no action has been taken yet. A Loan Manager must confirm actual "
            "repossession via the Asset Realisation flow."
        ).format(loan_name),
    )


def release_asset(loan_name):
    """
    The real implementation releaseSecurity() (RokctAI_frontend's loan.ts)
    needs - see asset_realisation.py's release_security() wrapper. Verifies
    the loan is genuinely fully paid off rather than trusting the caller.
    """
    from importlib import import_module

    # Doctype trees compose verbatim; derive the "<app>.polaris" root from __name__.
    get_pending_principal_amount = import_module(
        __name__.split(".doctype.")[0] + ".doctype.loan_repayment.loan_repayment"
    ).get_pending_principal_amount

    asset_name = frappe.db.get_value("Pledged Asset", {"loan": loan_name}, "name")
    if not asset_name:
        frappe.throw(_("No Pledged Asset found for Loan {0}").format(loan_name))

    asset = frappe.get_doc("Pledged Asset", asset_name)
    if asset.status == "Released":
        return asset.name
    if asset.status == "Repossessed":
        frappe.throw(
            _("The asset for Loan {0} has already been repossessed - it cannot be released.").format(loan_name)
        )

    loan = frappe.get_doc("Loan", loan_name)
    if get_pending_principal_amount(loan) > 0:
        frappe.throw(_("Loan {0} is not fully paid off yet - cannot release the pledged asset.").format(loan_name))

    asset.db_set("status", "Released")
    asset.db_set("released_date", nowdate())
    asset.add_comment("Info", _("Asset released: Loan {0} confirmed fully paid off.").format(loan_name))
    return asset.name


def mark_repossessed(loan_name, loan_write_off_name):
    """
    Called as a side effect from asset_realisation.py's realise_pawn_asset()
    after the actual Loan Write Off has been created and submitted - i.e.
    only after a human has actually executed repossession, never automatic.
    """
    asset_name = frappe.db.get_value("Pledged Asset", {"loan": loan_name}, "name")
    if not asset_name:
        return

    asset = frappe.get_doc("Pledged Asset", asset_name)
    if asset.status == "Repossessed":
        return
    asset.db_set("status", "Repossessed")
    asset.db_set("repossessed_date", nowdate())
    asset.db_set("loan_write_off", loan_write_off_name)
