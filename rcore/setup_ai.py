# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import subprocess
import os
import shutil
import sys


def setup_ai_infrastructure():
    """
    Automates the setup of the Hybrid AI infrastructure.
    1. Cleanup: Stops and Disables 'ollama' to free resources.
    2. Environment: Checks for CUDA/GPU availability.
    3. Models: Downloads necessary models to /opt/rokct_models.
    """
    print("\n\n--- 🧠 Setting up ROKCT Hybrid AI Infrastructure ---")

    _cleanup_legacy_ai_services()
    _install_python_dependencies()
    _setup_model_directory()
    _download_models()

    print("--- 🧠 AI Infrastructure Setup Complete ---\n")


def _cleanup_legacy_ai_services():
    """Stops, disables, and REMOVES legacy AI services like Ollama."""
    print("--- 🧹 Cleanup: Checking for legacy AI services ---")

    # 1. Check if Ollama exists
    ollama_path = shutil.which("ollama")
    service_path = "/etc/systemd/system/ollama.service"

    if not ollama_path and not os.path.exists(service_path):
        print("✅ Ollama is not installed. Skipping cleanup.")
        return

    # 2. Stop and Disable Ollama
    try:
        print("Found Ollama. Stopping service...")
        subprocess.run(
            ["sudo", "systemctl", "stop", "ollama"], check=False, capture_output=True
        )
        subprocess.run(
            ["sudo", "systemctl", "disable", "ollama"], check=False, capture_output=True
        )
        print("✅ 'ollama' service stopped and disabled.")

        # 3. Remove Binary and Service File
        if ollama_path:
            print(f"Removing binary: {ollama_path}")
            subprocess.run(["sudo", "rm", ollama_path], check=True)

        if os.path.exists(service_path):
            print(f"Removing service file: {service_path}")
            subprocess.run(["sudo", "rm", service_path], check=True)
            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)

        print("✅ Ollama completely removed.")

        # 4. Remove Nginx Config
        nginx_conf = "/etc/nginx/conf.d/ollama.conf"
        if os.path.exists(nginx_conf):
            print(f"Removing obsolete Nginx config: {nginx_conf}")
            subprocess.run(["sudo", "rm", nginx_conf], check=True)
            subprocess.run(["sudo", "systemctl", "reload", "nginx"], check=True)
            print("✅ Nginx config removed and service reloaded.")

    except Exception as e:
        print(f"⚠️ Could not cleanup ollama/nginx: {e}")


def _install_python_dependencies():
    """Ensures critical AI libraries are installed."""
    print("--- 📦 Dependencies: Verifying Python AI libraries ---")
    # This is mostly handled by bench/pip, but we verify here.
    try:
        import torch

        print(f"✅ PyTorch available. CUDA Available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("⚠️ PyTorch not found! It should be installed via requirements.txt.")


def _setup_model_directory():
    """Creates the persistent directory for AI models."""
    model_dir = "/opt/rokct_models"
    print(f"--- 📂 Storage: Preparing {model_dir} ---")

    if not os.path.exists(model_dir):
        try:
            # We use sudo because /opt usually requires root
            # Assuming 'frappe' user has passwordless sudo for specific commands or use python 'os' if permission allows
            # If we are running as 'frappe' user, we might not have write access to /opt
            # Fallback to user home if /opt fails
            try:
                subprocess.run(["sudo", "mkdir", "-p", model_dir], check=True)
                subprocess.run(
                    [
                        "sudo",
                        "chown",
                        "-R",
                        f"{os.environ.get('USER')}:{os.environ.get('USER')}",
                        model_dir,
                    ],
                    check=True,
                )
                print(f"✅ Created {model_dir}")
            except subprocess.CalledProcessError:
                print(
                    f"⚠️ Could not create {model_dir} (Permission Denied). Falling back to ~/rokct_models."
                )
                model_dir = os.path.expanduser("~/rokct_models")
                os.makedirs(model_dir, exist_ok=True)
                print(f"✅ Created {model_dir}")

            # Set this path in site config so ai_manager knows where to look
            from frappe.installer import update_site_config

            update_site_config("ai_model_path", model_dir)

        except Exception as e:
            frappe.log_error(f"Failed to create model directory: {e}")
            raise


def _download_models():
    """Downloads OR Removes models based on brain_config.json."""
    print("--- ⬇️ Models: Synchronizing AI Models ---")

    model_dir = frappe.conf.get("ai_model_path") or "/opt/rokct_models"
    if not os.path.exists(model_dir):
        model_dir = os.path.expanduser("~/rokct_models")

    # Read Config
    import json

    # Use config from the app source which is the source of truth for defaults
    try:
        brain_config_path = frappe.get_app_path(
            "rcore", "ai_config", "brain_config.json"
        )
    except Exception:
        # Fallback for weird path issues
        brain_config_path = os.path.join(
            os.path.dirname(__file__), "ai_config", "brain_config.json"
        )
    config = {}
    try:
        if os.path.exists(brain_config_path):
            with open(brain_config_path, "r") as f:
                config = json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to read brain_config.json: {e}")

    # Define tasks with their config keys and model repos
    tasks = [
        {
            "name": "Vision (GOT-OCR)",
            "config_key": "vision_backend",
            "repo": "stepfun-ai/GOT-OCR2_0",
            "dir": "got_ocr",
        },
        {
            "name": "Brain (Phi-3.5)",
            "config_key": "brain_backend",
            "repo": "microsoft/Phi-3.5-mini-instruct",
            "dir": "phi3.5",
        },
        {
            "name": "Router (DeBERTa)",
            "config_key": "router_backend",
            "repo": "cross-encoder/nli-deberta-v3-xsmall",
            "dir": "router",
        },
    ]

    try:
        from huggingface_hub import snapshot_download

        for task in tasks:
            backend = config.get(
                task["config_key"], "local"
            )  # Default to local if missing
            local_path = os.path.join(model_dir, task["dir"])

            if backend == "local":
                # Install / Update
                print(f"📥 {task['name']}: Backend is LOCAL. Verifying/Downloading...")
                try:
                    snapshot_download(
                        repo_id=task["repo"],
                        local_dir=local_path,
                        local_dir_use_symlinks=False,
                    )
                    print(f"   ✅ {task['name']} is ready at {local_path}")
                except Exception as e:
                    print(f"   ❌ Failed to download {task['name']}: {e}")
            else:
                # Cleanup / Remove
                if os.path.exists(local_path):
                    print(
                        f"🧹 {task['name']}: Backend is {backend.upper()}. Cleaning up local model..."
                    )
                    try:
                        shutil.rmtree(local_path)
                        print(f"   ✅ Removed {local_path}")
                    except Exception as e:
                        print(f"   ⚠️ Failed to remove {local_path}: {e}")
                else:
                    print(
                        f"✨ {task['name']}: Backend is {backend.upper()}. No local files to clean."
                    )

        # Always ensure Embeddings (small, useful utility)
        embed_path = os.path.join(model_dir, "minilm")
        print("📥 Embeddings: Verifying...")
        snapshot_download(
            repo_id="sentence-transformers/all-MiniLM-L6-v2",
            local_dir=embed_path,
            local_dir_use_symlinks=False,
        )

    except ImportError:
        print("⚠️ huggingface_hub library not found. Skipping model sync.")
    except Exception as e:
        print(f"❌ Error during model sync: {e}")
