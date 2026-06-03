# API Reference: commit_onboarding_answers

Source file: `rcore/api/plan_builder/commit_onboarding_answers.py`

## Whitelisted API Endpoints

### `def commit_onboarding_answers(profile_type, instance_name, answers, milestones=None)`
Creates or updates the questions.md file for the given profile and instance name,
runs the StartupOS compiler to render downstream deliverables, and commits
the resulting plan to the database.
tenant context check.
