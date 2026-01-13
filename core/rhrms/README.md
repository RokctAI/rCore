# RHRMS (ROKCT HRMS Extension)

This module is an extension of the official `frappe/hrms` app.

## Purpose
It bridges the gap between the standard HRMS app and ROKCT's specific requirements, particularly regarding Lending integration and Employee Self Service (ESS).

## Contents
- **Setup**: Custom setup logic for Salary Slip fields and ESS permissions (`setup.py`).
- **Overrides**: Custom logic for `Employee` (ID validation, onboarding) and `Leave Application`.
- **Regional**: South Africa specific tax logic (if applicable).

## Usage
This module should be installed alongside `frappe/hrms`. It relies on the standard app for core functionality and injects custom business logic via overrides and hooks.
