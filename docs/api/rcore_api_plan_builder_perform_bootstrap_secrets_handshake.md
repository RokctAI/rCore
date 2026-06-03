# API Reference: perform_bootstrap_secrets_handshake

Source file: `rcore/api/plan_builder/perform_bootstrap_secrets_handshake.py`

## Documented Module Functions

### `def perform_bootstrap_secrets_handshake()`
Performs secure single-use bootstrap handshake.
Exchanges the transient ROKCT_BOOTSTRAP_TOKEN for AI credentials,
loads them strictly in-memory, and immediately deletes the token.
