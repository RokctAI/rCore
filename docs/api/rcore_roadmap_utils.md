# API Reference: utils

Source file: `rcore/roadmap/utils.py`

## Documented Module Functions

### `def get_prompts()`
Fetches prompts from Roadmap Settings.

### `def check_queue_status(api_key)`
Checks if there are any sessions in 'QUEUED' state.
Returns True if Safe (No Queue), False if Busy (Queue exists).

### `def construct_contextual_prompt(roadmap, feature, mode='Building')`
Constructs a prompt by replacing placeholders {stack}, {platform}, {dependency}, {feature_tags}
with actual values from the Roadmap and Feature documents.
Dynamically injects instructions based on tags.
