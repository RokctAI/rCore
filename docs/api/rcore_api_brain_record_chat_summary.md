# API Reference: record_chat_summary

Source file: `rcore/api/brain/record_chat_summary.py`

## Whitelisted API Endpoints

### `def record_chat_summary(chat_transcript, reference_doctype=None, reference_name=None, modules=None)`
Accepts a raw chat transcript, enqueues a background job to summarize it.
Layer 14 compliance: system_prompt template, token budget, max_tokens, retry / fallback model.
Layer 16 compliance: quota isolation gate (free_rok_msg_count).
tenant context isolation check.
