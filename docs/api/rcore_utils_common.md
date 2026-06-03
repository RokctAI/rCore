# API Reference: common

Source file: `rcore/utils/common.py`

## Documented Module Functions

### `def call_control(method, data=None)`
Centralized utility to make secure API calls from a tenant to the control panel.
Requires 'control_plane_url' and 'api_secret' in site_config.json.

### `def is_ai_action()`
Checks if the current Frappe request was initiated by the AI agent
by looking for a specific HTTP header.

### `def inject_trace_context(doc, method=None)`
Wildcard doc event hook handler that captures the current active request's Trace ID
and automatically injects it into any document that implements a 'trace_id' field.
