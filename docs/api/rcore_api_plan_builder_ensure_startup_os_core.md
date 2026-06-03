# API Reference: ensure_startup_os_core

Source file: `rcore/api/plan_builder/ensure_startup_os_core.py`

## Documented Module Functions

### `def ensure_startup_os_core()`
Ensures that the compiler.py and parser.py are available for the plan builder API.
Resolves the StartupOS path dynamically. Always uses the site-specific StartupOS folder
to ensure clean isolation and prevent workspace cluttering. If files are missing, 
fetches them from raw GitHub.
