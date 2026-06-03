# API Reference: query

Source file: `rcore/api/brain/query.py`

## Whitelisted API Endpoints

### `def query(doctype, name)`
A secure API endpoint for an AI model to query the Brain's memory.
Ensures security is enforced by checking for read permission.
tenant context check.
