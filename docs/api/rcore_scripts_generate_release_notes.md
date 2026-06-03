# API Reference: generate_release_notes

Source file: `rcore/scripts/generate_release_notes.py`

## Documented Module Functions

### `def generate_release_notes(commit_log, version_name='vNext')`
Generates AI-written release notes using Groq (Llama 3) for the provided commit log.
This function is designed to be called via API.

:param commit_log: String containing the raw git log
:param version_name: String version identifier
:return: String containing the Markdown release notes
