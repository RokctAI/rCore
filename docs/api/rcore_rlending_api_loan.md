# API Reference: loan

Source file: `rcore/rlending/api/loan.py`

## Whitelisted API Endpoints

### `def disburse_loan(loan_application)`
Creates a Loan Disbursement for an approved Loan Application.
This is triggered by the 'Withdraw' button in the Mobile App.
tenant context check.
