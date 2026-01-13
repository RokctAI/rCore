# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, flt, getdate
from collections import defaultdict

class PaasOrderAnalyzer:
    """
    A service to analyze a customer's PaaS wallet history from the ERPNext system
    and calculate key metrics.
    """
    def __init__(self, customer_id):
        self.customer_id = customer_id
        self.transactions = []
        self.metrics = {}

    def analyze(self):
        """
        Main method to trigger the analysis process.
        """
        self._fetch_wallet_history()
        self._calculate_metrics()
        return self.metrics

    def _fetch_wallet_history(self):
        """
        Fetches the customer's wallet history from the database.
        Assumes 'Wallet' and 'Wallet History' DocTypes exist (PaaS installed).
        """
        if not frappe.db.exists("DocType", "Wallet"):
             return 

        wallet = frappe.get_value("Wallet", {"user": self.customer_id}, "name")
        if wallet:
            self.transactions = frappe.get_all(
                "Wallet History",
                filters={"wallet": wallet},
                fields=["name", "type", "price", "status", "creation"]
            )

    def _calculate_metrics(self):
        """
        Calculates key metrics from the fetched wallet history data.
        """
        if not self.transactions:
            self.metrics = {
                'total_transactions': 0,
                'total_spent': 0,
                'average_transaction_value': 0,
                'transaction_frequency_days': 0,
                'paid_transaction_rate': 0
            }
            return

        total_transactions = len(self.transactions)

        # Spending transactions are those that are not top-ups or disbursements.
        spending_transactions = [t for t in self.transactions if t.type not in ["Topup", "Loan Disbursement"]]

        total_spent = sum(abs(t.price) for t in spending_transactions if t.price < 0)
        average_transaction_value = total_spent / len(spending_transactions) if spending_transactions else 0

        # Transaction frequency
        if total_transactions > 1:
            sorted_transactions = sorted(self.transactions, key=lambda t: t.creation)
            first_transaction_date = getdate(sorted_transactions[0].creation)
            last_transaction_date = getdate(sorted_transactions[-1].creation)
            days_diff = (last_transaction_date - first_transaction_date).days
            transaction_frequency_days = days_diff / (total_transactions - 1) if total_transactions > 1 else 0
        else:
            transaction_frequency_days = 0

        # Paid transaction rate
        paid_transactions = sum(1 for t in self.transactions if t.status == 'Paid')
        paid_transaction_rate = (paid_transactions / total_transactions) * 100 if total_transactions > 0 else 0

        self.metrics = {
            'total_transactions': total_transactions,
            'total_spent': total_spent,
            'average_transaction_value': average_transaction_value,
            'transaction_frequency_days': transaction_frequency_days,
            'paid_transaction_rate': paid_transaction_rate
        }
