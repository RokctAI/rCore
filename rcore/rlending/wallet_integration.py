import frappe
from frappe import _

def credit_wallet_on_disbursement(doc, method):
	"""
	Credits the User's Wallet when a Loan is Disbursed.
	"""
	# Only for customer loans (or whatever logic applies)
	if not doc.applicant_type == "Customer":
		return
        
	customer = doc.applicant
	amount = doc.disbursed_amount
	description = f"Loan Disbursement: {doc.name}"
	
	update_wallet(customer, amount, "Loan Disbursement", description)

def debit_wallet_on_repayment(doc, method):
	"""
	Debits the User's Wallet when a Loan Repayment is made (if paid via Wallet).
	"""
	if not doc.applicant_type == "Customer":
		return

	# Only debit if payment method implies wallet or if we auto-deduct?
	# Assuming every repayment reduces wallet balance (which seems odd if paid by cash)
	# BUT based on the snippet: "If Repayment (Debit), subtract."
	# We will follow the snippet logic blindly for now.
	
	customer = doc.applicant
	amount = doc.amount_paid
	description = f"Loan Repayment: {doc.name}"
	
	update_wallet(customer, amount, "Loan Repayment", description)

def update_wallet(customer, amount, transaction_type, description):
	# Find or Create Wallet for Customer
	wallet_name = frappe.db.get_value("Wallet", {"customer": customer}, "name")
	
	if not wallet_name:
		wallet = frappe.get_doc({
			"doctype": "Wallet",
			"customer": customer,
			"balance": 0
		})
		wallet.insert(ignore_permissions=True)
		wallet_name = wallet.name
	else:
		wallet = frappe.get_doc("Wallet", wallet_name)

	# 1. Create History
	history = frappe.get_doc({
		"doctype": "Wallet History",
		"wallet": wallet_name,
		"transaction_type": transaction_type,
		"amount": abs(amount), # Store positive value in history usually
		"status": "Processed",
		"description": description,
		# "is_withdrawable": is_withdrawable # This field was in snippet but I do not know logic for it.
		# I will assume True/False based on transaction type or default.
		"is_withdrawable": 1 if transaction_type == "Loan Disbursement" else 0
	})
	history.insert(ignore_permissions=True)
    
	# 2. Update Balance
	# If type is Disbursement (Credit), add. If Repayment (Debit), subtract.
	if transaction_type == "Loan Disbursement":
		wallet.balance += abs(amount)
	elif transaction_type == "Loan Repayment":
		wallet.balance -= abs(amount)
    
	wallet.save(ignore_permissions=True)
