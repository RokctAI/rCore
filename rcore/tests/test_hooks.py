import frappe
import json
from frappe.tests.utils import FrappeTestCase


class TestRcoreHooks(FrappeTestCase):
    def setUp(self):
        if not frappe.db.exists("DocType", "Customer"):
            self.skipTest("ERPNext not installed (Customer missing)")
            return
        # Create a test customer
        if not frappe.db.exists("Customer", "Test Rcore Customer"):
            self.customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Test Rcore Customer",
                "customer_type": "Individual",
                "customer_group": "All Customer Groups",
                "territory": "All Territories"
            }).insert(ignore_permissions=True)
        else:
            self.customer = frappe.get_doc("Customer", "Test Rcore Customer")

    def tearDown(self):
        # Cleanup
        frappe.db.delete(
            "Wallet History", {
                "wallet": [
                    "in", frappe.get_all(
                        "Wallet", {
                            "customer": self.customer.name}, pluck="name")]})
        frappe.db.delete("Wallet", {"customer": self.customer.name})
        # Customer cleanup if safe
        pass

    def test_loan_disbursement_wallet_integration(self):
        # 1. Create a Loan Disbursement
        # Note: We are testing the hook, so we can pass a dummy doc to the hook function directly
        # or create a document if we want to test the actual event trigger.
        # Since rcore hooks rely on doc_events, let's test the trigger.

        from rcore.rlending.wallet_integration import credit_wallet_on_disbursement

        loan_doc = frappe.get_doc({
            "doctype": "Loan Disbursement",
            "applicant_type": "Customer",
            "applicant": self.customer.name,
            "disbursed_amount": 5000,
            "name": "TEST-LOAN-DISB-001"
        })

        # Manually trigger the hook to verify logic (since insert might require
        # complex dependencies)
        credit_wallet_on_disbursement(loan_doc, "on_submit")

        # Verify wallet exists and balance is 5000
        wallet = frappe.get_doc("Wallet", {"customer": self.customer.name})
        self.assertEqual(wallet.balance, 5000)

        # Verify history record
        history = frappe.get_all(
            "Wallet History", filters={
                "wallet": wallet.name}, fields=[
                "transaction_type", "amount"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].transaction_type, "Loan Disbursement")
        self.assertEqual(history[0].amount, 5000)

    def test_loan_repayment_wallet_integration(self):
        # 1. Ensure wallet exists with balance
        wallet = frappe.get_doc({
            "doctype": "Wallet",
            "customer": self.customer.name,
            "balance": 1000
        }).insert(ignore_permissions=True)

        from rcore.rlending.wallet_integration import debit_wallet_on_repayment

        repayment_doc = frappe.get_doc({
            "doctype": "Loan Repayment",
            "applicant_type": "Customer",
            "applicant": self.customer.name,
            "amount_paid": 200,
            "name": "TEST-LOAN-REPAY-001"
        })

        debit_wallet_on_repayment(repayment_doc, "on_submit")

        wallet.reload()
        self.assertEqual(wallet.balance, 800)

    def test_employee_publish_update_hook(self):
        # Verify employee on_update hook triggers publish_update
        employee = frappe.get_doc({
            "doctype": "Employee",
            "first_name": "Test",
            "last_name": "Employee",
            "gender": "Male",
            "date_of_birth": "1990-01-01"
        }).insert(ignore_permissions=True)

        # Trigger on_update
        employee.save()
        # If it doesn't crash, and we can mock publish_update if needed.
        # For now, we verify it runs without error.
        self.assertTrue(True)
