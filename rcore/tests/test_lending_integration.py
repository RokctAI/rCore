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

        # Mock Wallet existence check (returns None -> creates new)
        mock_get_value.return_value = None

        # Mock Wallet creation
        mock_wallet = MagicMock()
        mock_wallet.name = "WALLET-1"
        mock_wallet.balance = 0
        
        # Mock History creation
        mock_history = MagicMock()

        # Configure get_doc to return our mocks
        # First call creates Wallet, Second call creates History
        # We need side_effect to return different mocks
        mock_get_doc.side_effect = [mock_wallet, mock_history]

        # 2. Call the function
        credit_wallet_on_disbursement(mock_loan, "on_submit")

        # 3. Verify Interactions
        # Check if Wallet was created
        mock_get_doc.assert_any_call({
            "doctype": "Wallet",
            "customer": "Test Customer",
            "balance": 0
        })
        
        # Check if Balance was updated
        # 0 + 1000 = 1000. 
        # Note: Since it's a mock method, += might not update the property in a way assertEqual sees if not configured,
        # but we can check assignment.
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

        # Mock Wallet existence check (returns Existing Wallet)
        mock_get_value.return_value = "WALLET-EXISTING"

        # Mock Wallet retrieval
        mock_wallet = MagicMock()
        mock_wallet.name = "WALLET-EXISTING"
        mock_wallet.balance = 2000
        
        # Mock History creation
        mock_history = MagicMock()

        # Configure get_doc returns
        mock_get_doc.side_effect = [mock_wallet, mock_history]

        # 2. Call the function
        debit_wallet_on_repayment(mock_repayment, "on_submit")

        # 3. Verify
        # Should NOT create new wallet (as it exists)
        # Should Retrieve wallet
        mock_get_doc.assert_any_call("Wallet", "WALLET-EXISTING")

        # Check Balance Logic (2000 - 500 = 1500)
        self.assertEqual(mock_wallet.balance, 1500)
        
        mock_wallet.save.assert_called()
