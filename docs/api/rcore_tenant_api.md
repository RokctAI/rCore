# API Reference: api

Source file: `rcore/tenant/api.py`

## Whitelisted API Endpoints

### `def get_token_usage()`
Returns usage breakdown for Pro and Flash. Tenant context trace.

### `def get_subscription_details()`
A secure proxy API for the frontend to get subscription details.
Caches the response from the control panel.

### `def record_unique_visit(visitor_id, client_ip=None, user_id=None)`
Records a unique visit on the tenant side.
Deduplicates using visitor IP + visitor_id in a Redis Set.
Also logs user identification if user_id is provided.

## Documented Module Functions

### `def announce_ready_to_control()`
Called standardly via hooks (after_install) to announce that the tenant
container is healthy and ready to the Control Hub.
Reuses ROKCT_BOOTSTRAP_TOKEN (transient env) to authorize.

### `def sync_visitors_to_control()`
Scheduled task to sync yesterday's unique visitor counts to the control panel.
