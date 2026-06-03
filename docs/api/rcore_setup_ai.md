# API Reference: setup_ai

Source file: `rcore/setup_ai.py`

## Documented Module Functions

### `def setup_ai_infrastructure()`
Automates the setup of the Hybrid AI infrastructure.
1. Cleanup: Stops and Disables 'ollama' to free resources.
2. Environment: Checks for CUDA/GPU availability.
3. Models: Downloads necessary models to /opt/rokct_models.
