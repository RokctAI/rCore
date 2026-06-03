# API Reference: generate_strategic_alignment_report

Source file: `rcore/api/plan_builder/generate_strategic_alignment_report.py`

## Whitelisted API Endpoints

### `def generate_strategic_alignment_report(instance_name, profile_type='life')`
Acts as the dynamic Orchestrator. Queries the live database (operational task/goal telemetry)
and compares it to the questions.md strategic baseline (SSOT), invoking ROK completions
to compile a premium Strategic Alignment & Accountability Report.
tenant context check.
