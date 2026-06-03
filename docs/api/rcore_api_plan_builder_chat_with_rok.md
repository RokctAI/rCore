# API Reference: chat_with_rok

Source file: `rcore/api/plan_builder/chat_with_rok.py`

## Whitelisted API Endpoints

### `def chat_with_rok(message, session_id=None, model=None)`
Secure gateway proxy for Next.js (Vercel) to chat with ROK agent on the Tenant VPS.
Propagates X-Trace-Id across the distributed hops and emits structured logs to stderr.
