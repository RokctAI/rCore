# API Reference: vote_on_plan

Source file: `rcore/api/brain/vote_on_plan.py`

## Whitelisted API Endpoints

### `def vote_on_plan(session_id, action, api_key=None)`
Register a vote (approval) for a plan via the Jules service.
This function contacts the Jules API to approve a plan given a session ID and optional API key.
