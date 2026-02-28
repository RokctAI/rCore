
import frappe
from frappe import _
from lending.loan_management.doctype.loan_application.loan_application import LoanApplication as BaseLoanApplication


class LoanApplication(BaseLoanApplication):
    """
    Custom Override for Loan Application.
    Adds:
    - KYC Validation (CRM Lead Check)
    - Ringfencing Rules (Mobile App Logic)
    - Auto-Disburse Feature
    """

    def validate(self):
        super().validate()
        self.set_ringfencing_rules()
        self.validate_kyc()

    def on_update(self):
        super().on_update()
        if self.status == "Approved" and self.get_db_value(
                "status") != "Approved":
            # Auto-disburse on approval
            from rcore.rlending.api.loan import disburse_loan
            disburse_loan(self.name)

    def set_ringfencing_rules(self):
        """
        Rules:
        - If is_from_mobile and skip_documents, it is automatically Ring-Fenced and NOT Withdrawable.
        - This ensures manual entries or documented mobile applications can still be withdrawable.
        """
        # Check if fields exist (they might not be in standard doctype yet if we deleted the custom one)
        # But we assume the official app + our property setters will add them.
        if self.get("is_from_mobile") and self.get("skip_documents"):
            self.is_ring_fenced = 1
            self.is_withdrawable = 0
        else:
            if not self.get("is_ring_fenced"):
                self.is_withdrawable = 1
                self.is_ring_fenced = 0
            else:
                self.is_withdrawable = 0

    def validate_kyc(self):
        """
        Withdrawable loans REQUIRE a Verified KYC Status.
        """
        if not self.get("is_withdrawable"):
            return

        # Check if there is a verified CRM Lead for this customer
        if self.applicant_type == "Customer":
            customer_email = frappe.db.get_value(
                "Customer", self.applicant, "email_id")
            customer_mobile = frappe.db.get_value(
                "Customer", self.applicant, "mobile_no")

            lead = None
            if customer_email:
                lead = frappe.db.get_value(
                    "CRM Lead", {"email": customer_email}, "name")
            if not lead and customer_mobile:
                lead = frappe.db.get_value(
                    "CRM Lead", {
                        "mobile_no": customer_mobile}, "name")

            if lead:
                kyc_status = frappe.db.get_value(
                    "CRM Lead", lead, "kyc_status")
                if kyc_status != "Verified":
                    frappe.throw(
                        _("KYC Verification is required for withdrawable loans. Current status: {0}").format(kyc_status))
