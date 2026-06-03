# API Reference: tasks

Source file: `rcore/roadmap/tasks.py`

## Whitelisted API Endpoints

### `def discover_roadmap_context(roadmap_name)`
Auto-Discovery Task (On Demand)
1. Starts a Planning Session with Jules to analyze the codebase.
2. Asks for a Description and Classifications (Stack/Platform/Dependency).
3. Polls (briefly) for handling.
4. Returns the result and closes the session.

## Documented Module Functions

### `def populate_roadmap_with_ai_ideas()`
(Daily Task)
Initiates AI idea generation sessions via Brain Service.
Checks each Roadmap for a repo + key, and if no 'Ideas' are pending, generates new ones.

### `def process_pending_ai_sessions()`
(Hourly/Frequent Task)
POLLS pending AI Idea Sessions for results via Brain.

### `def process_building_queue()`
(Featured Task)
Process items in 'Idea Passed' and 'Bugs' by assigning them to Jules (Building Mode).

### `def jules_task_monitor()`
(Hourly Task)
Monitors Roadmap Features assigned to Jules (Push Flow).
Checks for PRs and Moves to Done.

### `def cleanup_archived_sessions()`
(Hourly Task)
Cleans up Jules sessions for items moved to 'Archived'.
Saves activity log to the document before deletion.

### `def _get_api_key()`
Helper to get the Global Jules API Key from Settings.

### `def _create_jules_session(api_key, source_repo, title, prompt)`
Helper to start a Jules Session (typically for one-off tasks like workflow setup).
