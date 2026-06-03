# API Reference: utils

Source file: `rcore/tenant/utils.py`

## Documented Module Functions

### `def send_tenant_email(**kwargs)`
A centralized utility for sending emails from a tenant site.
It follows a specific fallback order:
1. Check for a default outgoing Email Account configured on the tenant site.
2. If none, attempt to relay the email through the control panel.
3. If relay is not configured or fails, the operation will fail.
