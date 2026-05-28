# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import redis
import json
import uuid
import time
import os
import requests
from frappe import _

# Queue Names match ai_manager.py
BRAIN_QUEUE = "rokct:brain_queue"
VISION_QUEUE = "rokct:vision_queue"
ROUTER_QUEUE = "rokct:router_queue"
EMBEDDING_QUEUE = "rokct:embedding_queue"

DEFAULT_TIMEOUT = 60

def dispatch_ai_task(queue_name, data, timeout=60):
    """
    Dispatches a task to the Redis queue and waits for the result (Synchronous-ish).
    For truly async background jobs, use 'fire_and_forget=True' (to be implemented).
    
    :param queue_name: Which worker to target (BRAIN_QUEUE, etc.)
    :param data: Dict containing task data (prompt, image_path, etc.)
    :return: The result dict from the worker.
    """
    try:
        # 0. Intercept for Hybrid Cloud Routing
        if queue_name == VISION_QUEUE:
            if _should_route_extensions("vision"):
                return _call_jina_vision(data)
        
        # 1. Connect to Redis (reuse connection if possible in future)
        r = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")
        
        # 2. Prepare Job
        job_id = str(uuid.uuid4())
        data['job_id'] = job_id
        data['site'] = frappe.local.site  # Inject Site Context for Global Worker
        
        # 3. Push to Queue
        r.rpush(queue_name, json.dumps(data))
        
        # 4. Wait for Result (Polling)
        # We poll the 'rokct:result:{job_id}' key
        start_time = time.time()
        while time.time() - start_time < timeout:
            result_raw = r.get(f"rokct:result:{job_id}")
            if result_raw:
                # Cleanup and Return
                r.delete(f"rokct:result:{job_id}")
                return json.loads(result_raw)
            
            time.sleep(0.1) # Short sleep to avoid CPU spinning
            
        raise TimeoutError(f"AI Worker timed out after {timeout}s")
        
    except Exception as e:
        frappe.log_error(f"AI Dispatch Error: {e}", "AI Service")
        return {"status": "error", "message": str(e)}

def _should_route_extensions(worker_type):
    """
    Checks brain_config.json to see if we should route to Cloud/Jina
    instead of the local Redis Queue.
    """
    try:
        config_path = frappe.get_site_path("..", "apps", "rcore", "rcore", "ai_config", "brain_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                # Default is "jina" (Cloud) for vision, "local" for others
                backend = config.get(f"{worker_type}_backend", "jina" if worker_type == "vision" else "local")
                return backend != "local"
    except Exception:
        return True # Default to Cloud/Jina on error for Vision
    return False

def get_api_key(provider):
    """
    Fetches API Key from 'Brain Settings' (in Control App) or Fallbacks.
    Priority:
    1. Brain Settings (DocType)
    2. site_config.json (frappe.conf)
    3. Environment Variable
    """
    key_field = f"{provider.lower()}_api_key"
    
    # 1. Try Brain Settings (Single DocType from Control App)
    try:
        # We access it loosely to avoid dependency errors if Control isn't installed
        settings = frappe.get_single("Brain Settings")
        if settings and hasattr(settings, key_field):
            key = getattr(settings, key_field)
            if key: return key
    except Exception:
        pass # DocType might not exist or be accessible
        
    # 2. Try Site Config
    conf_key = frappe.conf.get(key_field)
    if conf_key: return conf_key
    
    # 3. Try Environment
    env_key = os.environ.get(key_field.upper())
    if env_key: return env_key
    
    return None

def _call_jina_vision(data):
    """
    Calls Jina.ai Reader API for Vision tasks.
    """
    # 1. Get URL (Jina works best with URLs)
    file_url = data.get("file_url")
    if not file_url and data.get("file_path"):
        return {"status": "error", "message": "Jina Backend requires 'file_url'. Local file paths are not supported yet."}

    try:
        # 2. Prepare Headers (Auth)
        headers = {
            "Accept": "application/json"
        }
        
        # Check for API Key (Brain Settings -> Config -> Env)
        api_key = get_api_key("jina")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # 3. Call Jina
        jina_url = f"https://r.jina.ai/{file_url}"
        response = requests.get(jina_url, headers=headers, timeout=30)

        response.raise_for_status()
        
        # 3. Return Mocked Structure (to match VisionWorker output)
        return {
            "status": "success",
            "message": "Processed via Jina.ai",
            "ocr_text": response.text,
            "transaction_ids": [], # Jina doesn't insert into DB automatically yet
            "metrics": {}
        }
    except Exception as e:
        return {"status": "error", "message": f"Jina API Failed: {e}"}

# Wrapper for legacy compatibility (renamed from call_ollama)
def ask_brain(prompt, system=None, tools=None):
    """
    Replacement for call_ollama. Routes directly to the active local ROK server (port 8642).
    """
    try:
        url = "http://127.0.0.1:8642/v1/v1/chat/completions" if os.environ.get("ROK_API_URL") else "http://127.0.0.1:8642/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        
        # Build prompt messages
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "hermes-agent",
            "messages": messages,
            "stream": False
        }

        response = requests.post(url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        choices = result.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            return {"status": "success", "text": content}
            
        return {"status": "error", "message": "No response choice returned from ROK."}
    except Exception as e:
        frappe.log_error(f"ROK Direct ask_brain failed: {e}", "Brain Services")
        return {"status": "error", "message": str(e)}

def embed_text(text):
    """
    Generates a vector embedding for the given text using MiniLM.
    Returns: List[float] (384 dimensions) or List[List[float]] if input is list.
    """
    if not text or not (isinstance(text, str) or isinstance(text, list)):
        return None
        
    payload = {"text": text}
    result = dispatch_ai_task(EMBEDDING_QUEUE, payload)
    
    if result and result.get("status") == "success":
        return result.get("embedding")
        
    return None
