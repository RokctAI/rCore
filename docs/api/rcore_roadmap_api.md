# API Reference: api

Source file: `rcore/roadmap/api.py`

## Whitelisted API Endpoints

### `def setup_github_workflow(roadmap_name)`
Checks if the GitHub workflow file exists in the repository. If not,
it delegates the task of creating the file to Jules via a new session.
