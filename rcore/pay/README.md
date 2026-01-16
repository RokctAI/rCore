# Pay

This module is an extension of the official `frappe/payments` app.

## Purpose
It contains custom payment gateway integrations and logic specific to ROKCT that are not present in the standard `frappe/payments` distribution.

## Contents
- **PayStack**: Custom integration for PayStack payments.
- **PayFast**: Custom integration for PayFast payments.

## Usage
These gateways leverage the base `PaymentGatewayController` from `frappe/payments` but are maintained here to preserve custom business logic and regional specificities.
