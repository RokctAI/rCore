# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import time
import json
import os
import signal
import sys
import multiprocessing
import redis
from frappe.utils import now
from rcore.services.llm_service import DEFAULT_TIMEOUT

# Queues
VISION_QUEUE = "rokct:vision_queue"
BRAIN_QUEUE = "rokct:brain_queue"
BRAIN_QUEUE = "rokct:brain_queue"
ROUTER_QUEUE = "rokct:router_queue"
EMBEDDING_QUEUE = "rokct:embedding_queue"

# Model Paths (Configurable via site config)
MODEL_ROOT = frappe.conf.get("ai_model_path", "/opt/rokct_models")


def start_ai_engine():
    """
    Main entry point for the AI Supervisor.
    This should be called from a management command or supervisor process.
    """
    print(f"🚀 ROKCT AI Engine Starting... (Models at {MODEL_ROOT})")

    # 1. Redis Connection
    try:
        r = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")
        r.ping()
        print("✅ Connected to Redis.")
    except Exception as e:
        print(f"❌ Redis Connection Failed: {e}")
        return

    # 2. Worker Definition
    workers = []

    # Read Brain Config
    brain_config_path = frappe.get_site_path(
        "..", "apps", "rcore", "rcore", "ai_config", "brain_config.json"
    )
    config = {}

    try:
        if os.path.exists(brain_config_path):
            with open(brain_config_path, "r") as f:
                config = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read brain_config.json: {e}")

    # Vision Worker
    if config.get("vision_backend", "jina") == "local":
        print("👁️ Strategy: Starting VisionWorker (Local)")
        workers.append(
            multiprocessing.Process(
                name="VisionWorker", target=run_vision_worker, args=(r,)
            )
        )
    else:
        print("👁️ Strategy: Skipping VisionWorker (Remote/Jina Mode)")

    # Brain Worker
    if config.get("brain_backend", "local") == "local":
        print("🧠 Strategy: Starting BrainWorker (Local)")
        workers.append(
            multiprocessing.Process(
                name="BrainWorker", target=run_brain_worker, args=(r,)
            )
        )
    else:
        print("🧠 Strategy: Skipping BrainWorker (Remote Mode)")

    # Router Worker
    if config.get("router_backend", "local") == "local":
        print("🚦 Strategy: Starting RouterWorker (Local)")
        workers.append(
            multiprocessing.Process(
                name="RouterWorker", target=run_router_worker, args=(r,)
            )
        )
    else:
        print("🚦 Strategy: Skipping RouterWorker (Remote Mode)")

    # Embedding Worker (Always Local for now as it's lightweight)
    print("🧬 Strategy: Starting EmbeddingWorker (Local)")
    workers.append(
        multiprocessing.Process(
            name="EmbeddingWorker", target=run_embedding_worker, args=(r,)
        )
    )

    # 3. Start Workers
    for w in workers:
        w.start()
        print(f"✅ Started {w.name} (PID: {w.pid})")

    # 4. Monitor Loop
    try:
        while True:
            time.sleep(5)
            for w in workers:
                if not w.is_alive():
                    print(f"⚠️ {w.name} died. Restarting...")
                    # Re-instantiate and start (simplified for brevity, robust implementation would handle limits)
                    # For this MVP, we log and exit to let Supervisor handle full restart
                    sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping AI Engine...")
        for w in workers:
            w.terminate()
            w.join()
        print("Bye.")


# --- WORKER FUNCTIONS (Isolate Memory) ---


def run_vision_worker(redis_client):
    """
    Worker for HunyuanOCR / Vision tasks.
    Watches: rokct:vision_queue
    """
    print("👁️ Vision Worker Loading Models...")
    # Lazy imports to save RAM in parent process
    # import torch
    # from transformers import ...
    # Placeholder for actual model loading (Hunyuan is heavy)

    # Mocking loading for MVP structure
    time.sleep(2)
    print("👁️ Vision Worker Ready.")

    while True:
        # Blocking pop for efficiency
        task = redis_client.blpop(VISION_QUEUE, timeout=5)
        if not task:
            continue

        _, job_data_str = task
        job_data = json.loads(job_data_str)
        job_id = job_data.get("job_id")

        try:
            print(f"👁️ Processing Job {job_id}...")

            # --- MULTI-TENANT CONTEXT SWITCH ---
            site = job_data.get("site")
            if site:
                try:
                    frappe.init(site=site)
                    frappe.connect()
                    print(f"🌍 Connected to site: {site}")
                except Exception as e:
                    print(f"❌ Failed to connect to site {site}: {e}")
                    continue  # Skip this job if we can't connect to the tenant DB
            # -----------------------------------

            # 1. Validations
            file_path = job_data.get("file_path")
            customer = job_data.get("customer")

            if not file_path or not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")

            # 2. Load Model (Lazy Loading to save RAM until needed)
            model_path = os.path.join(MODEL_ROOT, "got_ocr")

            # Only load if not already loaded (Optimization)
            # CAUTION: 'multiprocessing' makes global vars tricky, but we are inside a dedicated process loop.
            # We can use a local 'cache' variable outside the loop if we want to keep it in memory.
            # For this implementation, we assume the worker keeps running.

            if "vision_model" not in locals():
                print(f"👁️ Loading GOT-OCR2_0 from {model_path}...")
                import torch
                from transformers import AutoModel, AutoTokenizer

                tokenizer = AutoTokenizer.from_pretrained(
                    model_path, trust_remote_code=True
                )
                vision_model = AutoModel.from_pretrained(
                    model_path,
                    trust_remote_code=True,
                    low_cpu_mem_usage=True,
                    device_map="cuda" if torch.cuda.is_available() else "cpu",
                    use_safetensors=True,
                )
                vision_model = (
                    vision_model.eval().cuda()
                    if torch.cuda.is_available()
                    else vision_model.eval()
                )
                print("👁️ Model Loaded.")

            # 3. Inference (OCR)
            # GOT-OCR2_0 API: res = model.chat(tokenizer, image_file, ocr_type='ocr')
            # catch any specific model errors

            print(f"👁️ Running Inference on {file_path}...")
            res = vision_model.chat(tokenizer, file_path, ocr_type="ocr")

            # res is usually a text string containing the content
            print(f"👁️ Model Output (First 100 chars): {res[:100]}...")

            # 4. Parse Extracted Text
            # We use the updated BankStatementParser which now accepts 'text'
            from rcore.utils.bank_statement_parser import BankStatementParser

            parser = BankStatementParser(res, file_type="text")
            metrics = parser.parse()  # Helper that calculates metrics
            transactions = parser.transactions

            print(f"👁️ Parsed {len(transactions)} transactions.")

            # 5. Extract Bank Details & Verify Name (New)
            bank_details = parser.bank_details
            if bank_details:
                print(f"👁️ Extracted Bank Details: {bank_details}")
                source_doctype = job_data.get("source_doctype")
                source_name = job_data.get("source_doc_name")

                if source_doctype == "Loan Application" and source_name:
                    app_doc = frappe.get_doc("Loan Application", source_name)

                    # Store details
                    app_doc.bank_name = bank_details.get("bank_name")
                    app_doc.bank_account_number = bank_details.get(
                        "bank_account_number"
                    )
                    app_doc.bank_branch_code = bank_details.get("bank_branch_code")
                    app_doc.bank_account_holder = bank_details.get(
                        "bank_account_holder"
                    )

                    # Name Matching Verification
                    if app_doc.bank_account_holder and app_doc.applicant_name:
                        if not _verify_name_match(
                            app_doc.applicant_name, app_doc.bank_account_holder
                        ):
                            print(
                                f"❌ Name Mismatch Detected: {app_doc.applicant_name} vs {app_doc.bank_account_holder}"
                            )
                            app_doc.status = "Rejected"
                            app_doc.description = f"Bank account holder name mismatch. Statement belongs to: {app_doc.bank_account_holder}"

                    app_doc.save(ignore_permissions=True)
                    frappe.db.commit()

            # 6. Persist to Database
            saved_ids = []
            if customer:
                for txn in transactions:
                    # Basic category prediction (Rule based for now, could use Phi-3.5 later for better tagging)
                    category = "Unclassified"
                    desc_lower = txn["description"].lower()
                    if "salary" in desc_lower:
                        category = "Income"
                    elif "betway" in desc_lower or "lotto" in desc_lower:
                        category = "Gambling"
                    elif "spar" in desc_lower or "checkers" in desc_lower:
                        category = "Groceries"

                    doc = frappe.get_doc(
                        {
                            "doctype": "Bank Statement Transaction",
                            "customer": customer,
                            "date": txn["date"],
                            "description": txn["description"],
                            "amount": txn["amount"],
                            "category": category,
                            "source_document": job_data.get("source_doc_name"),
                            "reference_doctype": job_data.get("source_doctype"),
                            "reference_name": job_data.get("source_doc_name"),
                        }
                    )
                    doc.insert(ignore_permissions=True)
                    saved_ids.append(doc.name)

            result = {
                "status": "success",
                "message": f"Processed {len(transactions)} transactions.",
                "ocr_text": res,
                "transaction_ids": saved_ids,
                "metrics": metrics,
            }

            # Write Result to Redis for polling
            redis_client.setex(
                f"rokct:result:{job_id}", 3600, json.dumps(result, default=str)
            )

        except Exception as e:
            print(f"❌ Vision Error: {e}")
            import traceback

            traceback.print_exc()
            redis_client.setex(
                f"rokct:result:{job_id}",
                3600,
                json.dumps({"status": "error", "message": str(e)}),
            )


def _verify_name_match(applicant_name, holder_name):
    """
    Normalizes and checks if the applicant's name reasonably matches the bank account holder's name.
    """
    import re

    def normalize(name):
        # Lowercase
        name = name.lower()
        # Remove titles
        name = re.sub(r"\b(mr|mrs|ms|miss|dr|prof|sir)\b", "", name)
        # Replace special chars with space instead of removing
        name = re.sub(r"[^a-z0-9\s]", " ", name)
        # Split by whitespace to get parts
        return set(name.split())

    applicant_parts = normalize(applicant_name)
    holder_parts = normalize(holder_name)

    if not applicant_parts or not holder_parts:
        return False

    # Check if at least the major parts of the applicant name exist in the holder string
    # E.g. "John Smith" should match "MR JOHN SIMON SMITH"
    matches = applicant_parts.intersection(holder_parts)

    # If we have at least 2 matching words or 100% of short names, count as match
    if len(matches) >= 2:
        return True
    if len(applicant_parts) == 1 and len(matches) == 1:
        return True

    return False


def run_brain_worker(redis_client):
    """
    Worker for Phi-3.5 / Logic tasks.
    Watches: rokct:brain_queue
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

    model_path = os.path.join(MODEL_ROOT, "phi3.5")

    print(f"🧠 Brain Worker Loading Phi-3.5 from {model_path}...")

    try:
        # Check if model path exists, else fallback or wait
        if not os.path.exists(model_path):
            print(
                f"⚠️ Model path {model_path} not found. Brain worker will fail on tasks."
            )

        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="cuda" if torch.cuda.is_available() else "cpu",
            torch_dtype="auto",
            trust_remote_code=True,
        )

        # Create pipeline for easier generation
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )
        print("🧠 Brain Worker Ready.")
    except Exception as e:
        print(f"❌ Failed to load Brain Model: {e}")
        # Proceed loop anyway to consume messages and return errors
        pipe = None

    while True:
        task = redis_client.blpop(BRAIN_QUEUE, timeout=5)
        if not task:
            continue

        _, job_data_str = task
        job_data = json.loads(job_data_str)
        job_id = job_data.get("job_id")

        try:
            print(f"🧠 Thinking about Job {job_id}...")

            if not pipe:
                raise RuntimeError("Brain Model not loaded.")

            prompt = job_data.get("prompt")
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful financial assistant called Juvo.",
                },
                {"role": "user", "content": prompt},
            ]

            generation_args = {
                "max_new_tokens": 500,
                "return_full_text": False,
                "temperature": 0.0,
                "do_sample": False,
            }

            output = pipe(messages, **generation_args)
            generated_text = output[0]["generated_text"]

            print(f"🧠 Response: {generated_text[:50]}...")

            # Write Result
            redis_client.setex(
                f"rokct:result:{job_id}",
                3600,
                json.dumps({"status": "success", "text": generated_text}),
            )

        except Exception as e:
            print(f"❌ Brain Error: {e}")
            redis_client.setex(
                f"rokct:result:{job_id}",
                3600,
                json.dumps({"status": "error", "message": str(e)}),
            )


def run_router_worker(redis_client):
    """
    Worker for Headless Classification (WhatsApp/Email).
    Watches: rokct:router_queue
    """
    import torch
    from transformers import pipeline

    model_path = os.path.join(MODEL_ROOT, "router")
    print(f"traffic_light: Router Worker Loading DeBERTa from {model_path}...")

    try:
        if not os.path.exists(model_path):
            print(
                f"⚠️ Model path {model_path} not found. Router worker will fail on tasks."
            )

        # DeBERTa is usually a Zero-Shot or Text-Classification pipeline
        # setup_ai.py downloads 'cross-encoder/nli-deberta-v3-xsmall' which is NLI
        # We use it for Zero-Shot Classification

        router_pipe = pipeline(
            "zero-shot-classification",
            model=model_path,
            device_map="cuda" if torch.cuda.is_available() else "cpu",
        )
        print("🚦 Router Worker Ready.")
    except Exception as e:
        print(f"❌ Failed to load Router Model: {e}")
        router_pipe = None

    while True:
        task = redis_client.blpop(ROUTER_QUEUE, timeout=5)
        if not task:
            continue

        _, job_data_str = task
        job_data = json.loads(job_data_str)
        job_id = job_data.get("job_id")

        try:
            print(f"🚦 Routing Job {job_id}...")

            if not router_pipe:
                raise RuntimeError("Router Model not loaded.")

            text = job_data.get("text")
            # Define candidate labels for the router
            candidate_labels = [
                "Loan Application",
                "Repayment Query",
                "General Support",
                "Spam",
            ]

            output = router_pipe(text, candidate_labels)
            # output format: {'sequence': '...', 'labels': ['...'], 'scores': [...]}

            top_label = output["labels"][0]
            confidence = output["scores"][0]

            print(f"🚦 Intent: {top_label} ({confidence:.2f})")

            result = {
                "status": "success",
                "intent": top_label,
                "confidence": confidence,
                "full_output": output,
            }

            redis_client.setex(f"rokct:result:{job_id}", 3600, json.dumps(result))

        except Exception as e:
            print(f"❌ Router Error: {e}")
            redis_client.setex(
                f"rokct:result:{job_id}",
                3600,
                json.dumps({"status": "error", "message": str(e)}),
            )


def run_embedding_worker(redis_client):
    """
    Worker for Generating Embeddings (MiniLM).
    Watches: rokct:embedding_queue
    """
    from sentence_transformers import SentenceTransformer
    import torch

    model_path = os.path.join(MODEL_ROOT, "minilm")
    print(f"🧬 Embedding Worker Loading MiniLM from {model_path}...")

    try:
        # Check local path, else use hub name (though setup_ai downloads it)
        if os.path.exists(model_path):
            model = SentenceTransformer(model_path)
        else:
            print(f"⚠️ Local MiniLM not found at {model_path}. Downloading from Hub...")
            model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # Use GPU if available
        if torch.cuda.is_available():
            model = model.to("cuda")

        print("🧬 Embedding Worker Ready.")
    except Exception as e:
        print(f"❌ Failed to load Embedding Model: {e}")
        model = None

    while True:
        task = redis_client.blpop(EMBEDDING_QUEUE, timeout=5)
        if not task:
            continue

        _, job_data_str = task
        job_data = json.loads(job_data_str)
        job_id = job_data.get("job_id")

        try:
            # print(f"🧬 Embedding Job {job_id}...") # Verbose

            if not model:
                raise RuntimeError("Embedding Model not loaded.")

            text = job_data.get("text")

            # Generate Embedding
            # encode returns numpy array, convert to list for JSON
            embedding = model.encode(text).tolist()

            result = {"status": "success", "embedding": embedding}

            redis_client.setex(f"rokct:result:{job_id}", 3600, json.dumps(result))

        except Exception as e:
            print(f"❌ Embedding Error: {e}")
            redis_client.setex(
                f"rokct:result:{job_id}",
                3600,
                json.dumps({"status": "error", "message": str(e)}),
            )


if __name__ == "__main__":
    start_ai_engine()
