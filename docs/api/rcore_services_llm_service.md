# API Reference: llm_service

Source file: `rcore/services/llm_service.py`

## Documented Module Functions

### `def dispatch_ai_task(queue_name, data, timeout=60)`
Dispatches a task to the Redis queue and waits for the result (Synchronous-ish).
For truly async background jobs, use 'fire_and_forget=True' (to be implemented).

:param queue_name: Which worker to target (BRAIN_QUEUE, etc.)
:param data: Dict containing task data (prompt, image_path, etc.)
:return: The result dict from the worker.

### `def _should_route_extensions(worker_type)`
Checks brain_config.json to see if we should route to Cloud/Jina
instead of the local Redis Queue.

### `def get_api_key(provider)`
Fetches API Key from 'Brain Settings' (in Control App) or Fallbacks.
Priority:
1. Brain Settings (DocType)
2. site_config.json (frappe.conf)
3. Environment Variable

### `def _call_jina_vision(data)`
Calls Jina.ai Reader API for Vision tasks.

### `def ask_brain(prompt, system=None, tools=None)`
Replacement for call_ollama. Routes directly to the active local ROK server (port 8642).

### `def embed_text(text)`
Generates a vector embedding for the given text using MiniLM.
Returns: List[float] (384 dimensions) or List[List[float]] if input is list.
