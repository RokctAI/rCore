# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import csv
import io
from datetime import datetime


class BankStatementParser:
    """
    A service to parse uploaded bank statements (CSV format) and extract key financial metrics.
    """

    def __init__(self, file_content, file_type="csv"):
        self.file_content = file_content
        self.file_type = file_type
        self.transactions = []
        self.metrics = {}
        self.bank_details = {}

    def parse(self):
        """
        Main method to trigger the parsing process based on the file type.
        """
        if self.file_type == "csv":
            self._parse_csv()
        elif self.file_type == "text":
            self._parse_text()
        else:
            raise NotImplementedError(
                f"File type '{self.file_type}' is not supported yet."
            )

        self._calculate_metrics()
        self._extract_bank_details()
        return self.metrics

    def _parse_text(self):
        """
        Parses raw text content (e.g., from OCR).
        This is a heuristic-based parser that looks for date/description/amount patterns.
        """
        import re

        lines = self.file_content.split("\n")
        # Regex for Date (YYYY-MM-DD or DD/MM/YYYY), Description, Amount (Currency)
        # This is a basic implementation to start with.
        # 2024-01-01  Salary  25000.00
        pattern = re.compile(
            r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d+\.\d{2})"
        )

        for line in lines:
            match = pattern.search(line)
            if match:
                date_str, desc, amount_str = match.groups()
                try:
                    # Normalizing Date
                    if "-" in date_str:
                        dt = datetime.strptime(date_str, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(date_str, "%d/%m/%Y")

                    self.transactions.append(
                        {
                            "date": dt,
                            "description": desc.strip(),
                            "amount": float(amount_str),
                        }
                    )
                except ValueError:
                    continue

    def _parse_csv(self):
        """
        Parses a CSV file and loads transaction data.
        Assumes a standard format: Date, Description, Amount
        """
        try:
            # Use io.StringIO to treat the string content as a file
            csv_file = io.StringIO(self.file_content)
            reader = csv.reader(csv_file)

            # Skip header row
            next(reader, None)

            for row in reader:
                if len(row) == 3:
                    self.transactions.append(
                        {
                            "date": datetime.strptime(row[0], "%Y-%m-%d"),
                            "description": row[1],
                            "amount": float(row[2]),
                        }
                    )
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}")

    def _calculate_metrics(self):
        """
        Calculates key financial metrics from the parsed transaction data.
        """
        total_income = sum(t["amount"] for t in self.transactions if t["amount"] > 0)
        total_expenses = sum(t["amount"] for t in self.transactions if t["amount"] < 0)

        # Simple overdraft check: count transactions that made the balance negative
        # This requires a running balance, which is more complex.
        # For now, we count negative transactions as a proxy for expenses.
        overdrafts = sum(
            1
            for t in self.transactions
            if t["amount"] < 0 and "overdraft" in t["description"].lower()
        )

        self.metrics = {
            "total_income": total_income,
            "total_expenses": abs(total_expenses),
            "net_flow": total_income + total_expenses,
            "transaction_count": len(self.transactions),
            "overdraft_incidents": overdrafts,
        }

    def _extract_bank_details(self):
        """
        Extracts bank account details using regex heuristics from raw text.
        """
        import re

        if self.file_type != "text":
            return

        text = self.file_content

        # Heuristics for common South African and International bank statements
        # 1. Account Number
        acc_pattern = re.compile(
            r"(?:Statement for Account|Account Number|Acc No|Acc Number|Account No|Account)[\s:]+(\d{7,13})",
            re.IGNORECASE,
        )
        acc_match = acc_pattern.search(text)
        if acc_match:
            self.bank_details["bank_account_number"] = acc_match.group(1)

        # 2. Branch Code
        branch_pattern = re.compile(
            r"(?:Branch Code|Branch No|Sort Code)[\s:]+(\d{5,6})", re.IGNORECASE
        )
        branch_match = branch_pattern.search(text)
        if branch_match:
            self.bank_details["bank_branch_code"] = branch_match.group(1)

        # 3. Bank Name
        banks = [
            "Absa",
            "Standard Bank",
            "FNB",
            "Nedbank",
            "Capitec",
            "Investec",
            "Discovery Bank",
            "TymeBank",
        ]
        for bank in banks:
            if re.search(r"\b" + bank + r"\b", text, re.IGNORECASE):
                self.bank_details["bank_name"] = bank
                break

        # 4. Account Holder (Usually near the top, often after 'Name' or 'Holder')
        holder_pattern = re.compile(
            r"(?:Account Holder|Name|Customer Name)[\s:]+([A-Z ]{5,})", re.IGNORECASE
        )
        holder_match = holder_pattern.search(text)
        if holder_match:
            # Basic cleanup: take first line, strip
            self.bank_details["bank_account_holder"] = (
                holder_match.group(1).split("\n")[0].strip()
            )
