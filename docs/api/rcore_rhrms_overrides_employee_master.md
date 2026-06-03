# API Reference: employee_master

Source file: `rcore/rhrms/overrides/employee_master.py`

## Classes

### class `EmployeeMaster`

## Documented Module Functions

### `def validate_onboarding_process(doc, method=None)`
Validates Employee Creation for linked Employee Onboarding

### `def update_job_applicant_and_offer(doc, method=None)`
Updates Job Applicant and Job Offer status as 'Accepted' and submits them

### `def update_approver_role(doc, method=None)`
Adds relevant approver role for the user linked to Employee. Tenant context trace.

### `def update_approver_user_roles(doc, method=None)`
Updates roles for approver users. Tenant context trace.

### `def update_employee_transfer(doc, method=None)`
Unsets Employee ID in Employee Transfer if doc is deleted
