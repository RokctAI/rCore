# API Reference: commit_plan

Source file: `rcore/api/plan_builder/commit_plan.py`

## Whitelisted API Endpoints

### `def commit_plan(plan_data=None, profile_type=None, instance_name=None)`
Accepts either raw JSON payload from frontend (backward compatibility)
or profile_type + instance_name to parse compiled strategic markdown deliverables
and seed them directly to the database, ensuring files stop being used for operational work.
tenant context check.
