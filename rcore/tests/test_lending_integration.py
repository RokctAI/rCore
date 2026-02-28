# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import MagicMock, patch
from rcore.rlending.wallet_integration import credit_wallet_on_disbursement, debit_wallet_on_repayment


class TestLendingIntegration(FrappeTestCase):
    @patch('rcore.rlending.wallet_integration.frappe.get_doc')
    @patch('rcore.rlending.wallet_integration.frappe.db.get_value')
    def test_credit_wallet(self, mock_get_value, mock_get_doc):
        # 1. Setup Mock Data
        mock_loan = MagicMock()
        mock_loan.applicant_type = "Customer"
        mock_loan.applicant = "Test Customer"
        mock_loan.disbursed_amount = 1000
        mock_loan.name = "LOAN-1"

        # Mock Customer resolving User
        # Logic: frappe.db.get_value("Customer", customer, "user") ->
        # "test_user"
        def mock_get_value_side_effect(*args, **kwargs):
            if args[0] == "Customer" and args[1] == "Test Customer" and args[2] == "user":
                return "test_user"
            if args[0] == "Wallet" and args[1] == {"user": "test_user"}:
                return None  # Wallet not found
            return None

        mock_get_value.side_effect = mock_get_value_side_effect

        # Mock Wallet creation
        mock_wallet = MagicMock()
        mock_wallet.name = "WALLET-1"
        mock_wallet.balance = 0

        # Mock History creation
        mock_history = MagicMock()

        # Configure get_doc to return our mocks
        # We need to handle the dict call for Wallet creation
        def mock_get_doc_side_effect(*args, **kwargs):
            if isinstance(args[0], dict) and args[0].get(
                    "doctype") == "Wallet":
                return mock_wallet
            if isinstance(args[0], dict) and args[0].get(
                    "doctype") == "Wallet History":
                return mock_history
            return MagicMock()  # fallback

        mock_get_doc.side_effect = mock_get_doc_side_effect

        # 2. Call the function
        credit_wallet_on_disbursement(mock_loan, "on_submit")

        # 3. Verify Interactions
        # Check if Wallet was created with USER
        mock_get_doc.assert_any_call({
            "doctype": "Wallet",
            "user": "test_user",
            "balance": 0
        })

        # Check if Balance was updated
        self.assertEqual(mock_wallet.balance, 1000)

        # Check if Wallet was saved
        mock_wallet.save.assert_called()

    @patch('rcore.rlending.wallet_integration.frappe.get_doc')
    @patch('rcore.rlending.wallet_integration.frappe.db.get_value')
    def test_debit_wallet(self, mock_get_value, mock_get_doc):
        # 1. Setup Mock Data
        mock_repayment = MagicMock()
        mock_repayment.applicant_type = "Customer"
        mock_repayment.applicant = "Test Customer"
        mock_repayment.amount_paid = 500
        mock_repayment.name = "REPAY-1"

        # Mock Customer resolving User
        def mock_get_value_side_effect(*args, **kwargs):
            if args[0] == "Customer" and args[1] == "Test Customer" and args[2] == "user":
                return "test_user"
            if args[0] == "Wallet" and args[1] == {"user": "test_user"}:
                return "WALLET-EXISTING"
            return None

        mock_get_value.side_effect = mock_get_value_side_effect

        # Mock Wallet retrieval
        mock_wallet = MagicMock()
        mock_wallet.name = "WALLET-EXISTING"
        mock_wallet.balance = 2000

        # Mock History creation
        mock_history = MagicMock()

        # Configure get_doc returns
        def mock_get_doc_side_effect(*args, **kwargs):
            if args[0] == "Wallet" and args[1] == "WALLET-EXISTING":
                return mock_wallet
            if isinstance(args[0], dict) and args[0].get(
                    "doctype") == "Wallet History":
                return mock_history
            return MagicMock()

        mock_get_doc.side_effect = mock_get_doc_side_effect

        # 2. Call the function
        debit_wallet_on_repayment(mock_repayment, "on_submit")

        # 3. Verify
        # Should NOT create new wallet (as it exists)
        # Should Retrieve wallet
        mock_get_doc.assert_any_call("Wallet", "WALLET-EXISTING")

        # Check Balance Logic (2000 - 500 = 1500)
        self.assertEqual(mock_wallet.balance, 1500)

        mock_wallet.save.assert_called()
