# API Reference: subscription_utils

Source file: `rcore/rhrms/subscription_utils.py`

## Documented Module Functions

### `def update_erpnext_access(user_input)`
Called from hooks after setup wizard completion, ignored if user has no hrms subscription
enables erpnext workspaces and roles if user has subscribed to both hrms and erpnext
disables erpnext workspaces and roles if user has subscribed to hrms but not erpnext
