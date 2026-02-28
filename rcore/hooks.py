# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import frappe

# Core App Hooks

app_name = "rcore"
app_title = "Rcore"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "mit"
required_apps = ["payments"]

# Scheduler Events
# ----------------


def get_scheduler_events():
    if not hasattr(frappe, "conf") or not frappe.conf:
        return {}

    events = {
        "all": ["rcore.roadmap.tasks.process_pending_ai_sessions"],
        "hourly": ["rcore.roadmap.tasks.jules_task_monitor"],
        "daily": [
            "rcore.roadmap.tasks.populate_roadmap_with_ai_ideas",
            "rcore.roadmap.tasks.process_building_queue",
            "rcore.roadmap.tasks.cleanup_archived_sessions"
        ]
    }

    return events


scheduler_events = get_scheduler_events()

# Whitelisted Methods (Public APIs)
whitelisted_methods = {
    # Tenant Auth
    "rcore.api.auth.login": "rcore.api.auth.login",
    # Setup
    "rcore.api.setup.update_naming_series": "rcore.api.setup.update_naming_series",
    # Plan Builder
    "rcore.api.plan_builder.commit_plan": "rcore.api.plan_builder.commit_plan",
}

# Uninstallation
# ------------
before_uninstall = [
    # Cleaned: Core no longer handles builds
]

# Conditional Hooks based on installed apps
# -----------------------------------------

try:
    installed_apps = frappe.get_installed_apps()
except Exception:
    installed_apps = []

# --- CRM Hooks ---
if "crm" in installed_apps:
    after_install = ["rcore.rcrm.install.after_install"]

# --- HRMS Hooks ---
if "hrms" in installed_apps:
    # Append if already defined (which it is not, but good practice)
    if "after_install" not in locals():
        after_install = []
    after_install.append("rcore.rhrms.install.after_install")

    on_migrate = [
        "rcore.rhrms.setup.update_select_perm_after_install",
        "rcore.rhrms.setup.add_non_standard_user_types",
    ]

    # Setup Wizard
    setup_wizard_complete = "rcore.rhrms.subscription_utils.update_erpnext_access"

    # Integration Hooks
    after_app_install = "rcore.rhrms.setup.after_app_install"
    before_app_uninstall = "rcore.rhrms.setup.before_app_uninstall"

    # Uninstallation
    if "before_uninstall" not in locals():
        before_uninstall = []
    before_uninstall.append("rcore.rhrms.uninstall.before_uninstall")

    # HRMS Overrides
    override_doctype_class = {
        "Employee": "rcore.rhrms.overrides.employee_master.EmployeeMaster"
    }

    # HRMS Doc Events
    doc_events = {
        "User": {
            "validate": [
                "erpnext.setup.doctype.employee.employee.validate_employee_role",
                "rcore.rhrms.overrides.employee_master.update_approver_user_roles",
            ],
        },
        "Employee": {
            "validate": "rcore.rhrms.overrides.employee_master.validate_onboarding_process",
            "on_update": [
                "rcore.rhrms.overrides.employee_master.update_approver_role",
                "rcore.rhrms.overrides.employee_master.publish_update",
            ],
            "after_insert": "rcore.rhrms.overrides.employee_master.update_job_applicant_and_offer",
            "on_trash": "rcore.rhrms.overrides.employee_master.update_employee_transfer",
            "after_delete": "rcore.rhrms.overrides.employee_master.publish_update",
        }
    }

    # Extending accounting lists conditionally
    # Need to verify if accounting_dimension_doctypes is defined in
    # locals/global scope often
    accounting_dimension_doctypes = [
        "Expense Claim",
        "Expense Claim Detail",
        "Expense Taxes and Charges",
        "Payroll Entry",
        "Leave Encashment",
    ]

# --- Lending Module Hooks ---
if "lending" in installed_apps:
    if "override_doctype_class" not in locals():
        override_doctype_class = {}
    override_doctype_class.update({
        "Loan Application": "rcore.rlending.overrides.loan_application.LoanApplication"
    })

    if "doc_events" not in locals():
        doc_events = {}
    doc_events.update({
        "Loan Disbursement": {
            "on_submit": "rcore.rlending.wallet_integration.credit_wallet_on_disbursement"
        },
        "Loan Repayment": {
            "on_submit": "rcore.rlending.wallet_integration.debit_wallet_on_repayment"
        }
    })

# Fixtures
# --------
fixtures = [
    "Province", "Organ of State", "Role", "Custom Field",
    "Email Template"
]
