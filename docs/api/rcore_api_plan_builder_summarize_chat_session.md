# API Reference: summarize_chat_session

Source file: `rcore/api/plan_builder/summarize_chat_session.py`

## Whitelisted API Endpoints

### `def summarize_chat_session(session_id, messages)`
Summarizes a completed or long chat session via the ROK completions loop on Tenant with tracing and telemetry.
Layer 14 compliance: system_prompt template, token budget, max_tokens, retry / fallback model.
Layer 16 compliance: quota isolation gate (free_rok_msg_count).
