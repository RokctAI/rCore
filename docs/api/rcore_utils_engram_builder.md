# API Reference: engram_builder

Source file: `rcore/utils/engram_builder.py`

## Documented Module Functions

### `def get_document_title(doctype, name)`
Fetches the title of a document based on common title fields.

### `def _get_field_changes(doc)`
Compares the document with its state before saving to find changed fields.
Returns a human-readable string of the most important changes.

### `def _get_allowed_roles(doc)`
Returns a list of all roles that have read permission for the given document.
This includes roles with blanket permissions and roles from document shares.

### `def get_brain_module_doctypes()`
Fetches a list of all doctypes belonging to the 'Brain' module.
The result is cached for 24 hours to improve performance.

### `def get_excluded_doctypes_from_control()`
Fetches the list of excluded doctypes from the control panel.
Caches the result to avoid repeated API calls.

### `def process_event_in_realtime(doc, method)`
This is the main "storytelling engine". It's called by hooks and
instantly updates the Engram for a document in real-time.
