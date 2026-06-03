# API Reference: jules_service

Source file: `rcore/services/jules_service.py`

## Classes

### class `JulesClient`

#### Documented Internal Methods
##### `create_session(self, api_key, prompt, source_repo, automation_mode='AUTO_CREATE_PR', require_approval=False, title=None, branch='main')`
Creates a new Jules session.

##### `get_session(self, api_key, session_id)`
Gets full session details (including status and outputs).

##### `delete_session(self, api_key, session_id)`
Deletes a session (cleanup).

##### `get_activities(self, api_key, session_id)`
Fetches activity log for the session.

##### `get_sessions(self, api_key)`
Fetches all sessions.

##### `get_sources(self, api_key)`
Fetches available repositories.

##### `approve_plan(self, api_key, session_id)`
Approves a plan for the session.

##### `send_message(self, api_key, session_id, message)`
Sends a message to the session.
