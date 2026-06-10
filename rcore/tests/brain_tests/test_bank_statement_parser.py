# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import unittest
from rcore.utils.bank_statement_parser import BankStatementParser
from datetime import datetime


class TestBankStatementParser(unittest.TestCase):
    def test_parse_csv(self):
        csv_content = """Date,Description,Amount
2024-01-01,Salary,5000.00
2024-01-02,Rent,-1500.00
2024-01-03,Groceries,-200.00"""
        parser = BankStatementParser(csv_content, file_type="csv")
        metrics = parser.parse()

        self.assertEqual(len(parser.transactions), 3)
        self.assertEqual(metrics["total_income"], 5000.00)
        self.assertEqual(metrics["total_expenses"], 1700.00)
        self.assertEqual(metrics["transaction_count"], 3)

    def test_parse_text_ocr(self):
        ocr_text = """
        Statement for Account 123456789
        Bank Name: FNB
        Account Holder: JOHN DOE
        
        2024-01-01  Salary Payment  10000.00
        02/01/2024  ATM Withdrawal  -500.00
        2024-01-05  Overdraft Fee   -50.00
        """
        parser = BankStatementParser(ocr_text, file_type="text")
        metrics = parser.parse()

        # Test transactions
        self.assertEqual(len(parser.transactions), 3)
        self.assertEqual(parser.transactions[0]["amount"], 10000.00)
        self.assertEqual(parser.transactions[1]["amount"], -500.00)

        # Test metrics
        self.assertEqual(metrics["total_income"], 10000.00)
        self.assertEqual(metrics["overdraft_incidents"], 1)

        # Test bank details
        self.assertEqual(parser.bank_details["bank_name"], "FNB")
        self.assertEqual(parser.bank_details["bank_account_number"], "123456789")
        self.assertEqual(parser.bank_details["bank_account_holder"], "JOHN DOE")

    def test_bank_details_extraction_heuristics(self):
        text = (
            "Acc No: 987654321 Branch Code: 250655 Nedbank Statement Name: JANE SMITH"
        )
        parser = BankStatementParser(text, file_type="text")
        parser.parse()

        self.assertEqual(parser.bank_details["bank_name"], "Nedbank")
        self.assertEqual(parser.bank_details["bank_account_number"], "987654321")
        self.assertEqual(parser.bank_details["bank_branch_code"], "250655")
        self.assertEqual(parser.bank_details["bank_account_holder"], "JANE SMITH")

    def test_invalid_file_type(self):
        with self.assertRaises(NotImplementedError):
            BankStatementParser("content", file_type="pdf").parse()


if __name__ == "__main__":
    unittest.main()
