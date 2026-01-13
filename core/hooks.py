import frappe

# Core App Hooks

app_name = "core"
app_title = "Core"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "mit"

# Scheduler Events
# ----------------

def get_scheduler_events():
	if not hasattr(frappe, "conf") or not frappe.conf:
		return {}

	events = {
		"all": ["core.roadmap.tasks.process_pending_ai_sessions"],
		"hourly": ["core.roadmap.tasks.jules_task_monitor"],
		"daily": ["core.roadmap.tasks.populate_roadmap_with_ai_ideas"]
	}

	return events

scheduler_events = get_scheduler_events()

# Whitelisted Methods (Public APIs)
whitelisted_methods = {
    # Tenant Auth
    "core.api.auth.login": "core.api.auth.login",
    # Setup
    "core.api.setup.update_naming_series": "core.api.setup.update_naming_series",
    # Plan Builder
    "core.api.plan_builder.commit_plan": "core.api.plan_builder.commit_plan",
}

# Uninstallation
# ------------
before_uninstall = [
    # Cleaned: Core no longer handles builds
]

# Conditional Hooks based on installed apps
# -----------------------------------------

import frappe
try:
    installed_apps = frappe.get_installed_apps()
except Exception:
    installed_apps = []

# --- CRM Hooks ---
if "crm" in installed_apps:
    after_install = ["core.rcrm.install.after_install"]

# --- HRMS Hooks ---
if "hrms" in installed_apps:
    # Append if already defined (which it is not, but good practice)
    if "after_install" not in locals(): after_install = []
    after_install.append("core.rhrms.install.after_install")

    on_migrate = [
        "core.rhrms.setup.update_select_perm_after_install",
        "core.rhrms.setup.add_non_standard_user_types",
    ]
    
    # Setup Wizard
    setup_wizard_complete = "core.rhrms.subscription_utils.update_erpnext_access"

    # Integration Hooks
    after_app_install = "core.rhrms.setup.after_app_install"
    before_app_uninstall = "core.rhrms.setup.before_app_uninstall"
    
    # Uninstallation
    if "before_uninstall" not in locals(): before_uninstall = []
    before_uninstall.append("core.rhrms.uninstall.before_uninstall")

    # HRMS Overrides
    override_doctype_class = {
        "Employee": "core.rhrms.overrides.employee_master.EmployeeMaster"
    }

    # HRMS Doc Events
    doc_events = {
        "User": {
            "validate": [
                "erpnext.setup.doctype.employee.employee.validate_employee_role",
                "core.rhrms.overrides.employee_master.update_approver_user_roles",
            ],
        },
        "Employee": {
            "validate": "core.rhrms.overrides.employee_master.validate_onboarding_process",
            "on_update": [
                "core.rhrms.overrides.employee_master.update_approver_role",
                "core.rhrms.overrides.employee_master.publish_update",
            ],
            "after_insert": "core.rhrms.overrides.employee_master.update_job_applicant_and_offer",
            "on_trash": "core.rhrms.overrides.employee_master.update_employee_transfer",
            "after_delete": "core.rhrms.overrides.employee_master.publish_update",
        }
    }

    # Extending accounting lists conditionally
    # Need to verify if accounting_dimension_doctypes is defined in locals/global scope often
    accounting_dimension_doctypes = [
        "Expense Claim",
        "Expense Claim Detail",
        "Expense Taxes and Charges",
        "Payroll Entry",
        "Leave Encashment",
    ]

# --- Lending Module Hooks ---
if "lending" in installed_apps:
    if "override_doctype_class" not in locals(): override_doctype_class = {}
    override_doctype_class.update({
        "Loan Application": "core.rlending.overrides.loan_application.LoanApplication"
    })
    
    if "doc_events" not in locals(): doc_events = {}
    doc_events.update({
        "Loan Disbursement": {
            "on_submit": "core.rlending.wallet_integration.credit_wallet_on_disbursement" 
        },
        "Loan Repayment": {
            "on_submit": "core.rlending.wallet_integration.debit_wallet_on_repayment" 
        }
    })
