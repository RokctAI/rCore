# API Reference: paystack_settings

Source file: `rcore/pay/doctype/paystack_settings/paystack_settings.py`

## Classes

### class `PaystackSettings`

#### Documented Internal Methods
##### `get_payment_url(self, **kwargs)`
Creates an Integration Request and returns the URL for the Paystack checkout page.

## Whitelisted API Endpoints

### `def verify_transaction_and_get_auth(reference)`
Verifies a transaction using the reference from Paystack's frontend.
If successful, returns the authorization details. This is kept as a standalone
function because it's called directly from a whitelisted API, not from the controller instance.

:param reference: The transaction reference from Paystack.
:return: A dictionary with the result.
tenant context check.
