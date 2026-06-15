# API Reference: api

Source file: `tenant/api.py`

## Whitelisted API Endpoints

### `def report_client_error(title, error)`
Called by guest/client apps to report an exception.
Creates an API Error Log document, which is then automatically forwarded to the control panel.

### `def get_token_usage()`
Returns usage breakdown for Pro and Flash. Tenant context trace.

### `def get_subscription_details()`
A secure proxy API for the frontend to get subscription details.
Caches the response from the control panel.

### `def record_unique_visit(visitor_id, client_ip=None, user_id=None, app_version=None, os=None, os_version=None)`
Records a unique visit on the tenant side.
Deduplicates using visitor IP + visitor_id in a Redis Set.
Also logs user identification and device metadata.

## Documented Module Functions

### `def forward_error_to_control(doc, method)`
This function is called by a hook when a new API Error Log is created.
It enqueues a background job to send the error to the control panel.

### `def announce_ready_to_control()`
Called standardly via hooks (after_install) to announce that the tenant
container is healthy and ready to the Control Hub.
Reuses ROKCT_BOOTSTRAP_TOKEN (transient env) to authorize.

### `def sync_visitors_to_control()`
Scheduled task to sync yesterday's unique visitor counts to the control panel.
