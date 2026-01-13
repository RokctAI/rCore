# RLending (ROKCT Lending Extension)

This module is an extension of the official `frappe/lending` app.

## Purpose
It houses custom logic for ROKCT's lending operations, separating it from the standard lending framework to allow for safe upgrades.

## Contents
- **API**: Custom endpoints for Credit Scoring (`api/decision.py`), Disbursement (`api/loan.py`), and Product Listings (`api/product.py`).
- **Overrides**: Custom logic for `Loan Application` (KYC, Ringfencing) and `Wallet Integration`.
- **Assets**: Custom asset realisation logic.

## Usage
This module functions as a layer on top of `frappe/lending`. The frontend interacts with `core.rlending.api` for custom flows, while standard background processes are handled by the core app.
