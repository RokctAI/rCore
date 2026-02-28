import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.desk.page.setup_wizard.install_fixtures import _


def after_install():
    """
    This hook runs after the app is installed.
    We use it to apply our Custom Extensions on top of the standard HRMS.
    """
    create_salary_slip_loan_fields()

    # If Lending is already installed, patch ESS immediately
    if "lending" in frappe.get_installed_apps():
        update_ess_for_lending()


def after_app_install(app_name):
    """Set up loan integration with payroll when Lending app is installed"""
    if app_name != "lending":
        return

    print("Updating payroll setup for loans")
    create_salary_slip_loan_fields()
    update_ess_for_lending()


def before_app_uninstall(app_name):
    """Clean up loan integration with payroll when Lending app is uninstalled"""
    if app_name != "lending":
        return

    print("Cleaning up payroll setup for loans")
    delete_custom_fields(get_salary_slip_loan_fields())
    remove_lending_docperms_from_ess()


def create_salary_slip_loan_fields():
    if "lending" in frappe.get_installed_apps():
        if frappe.db.exists("DocType", "Salary Slip"):
            create_custom_fields(
                get_salary_slip_loan_fields(),
                ignore_validate=True)
        else:
            print(
                "Skipping Salary Slip custom fields as DocType 'Salary Slip' is not found.")


def get_salary_slip_loan_fields():
    """Custom fields for Lending integration on Salary Slip"""
    return {
        "Salary Slip": [
            {
                "fieldname": "loan_repayment_sb_1",
                "fieldtype": "Section Break",
                "label": _("Loan Repayment"),
                "depends_on": "total_loan_repayment",
                "insert_after": "base_total_deduction",
            },
            {
                "fieldname": "loans",
                "fieldtype": "Table",
                "label": _("Employee Loan"),
                "options": "Salary Slip Loan",
                "print_hide": 1,
                "insert_after": "loan_repayment_sb_1",
            },
            {
                "fieldname": "loan_details_sb_1",
                "fieldtype": "Section Break",
                "depends_on": "eval:doc.docstatus != 0",
                "insert_after": "loans",
            },
            {
                "fieldname": "total_principal_amount",
                "fieldtype": "Currency",
                "label": _("Total Principal Amount"),
                "default": "0",
                "options": "Company:company:default_currency",
                "read_only": 1,
                "insert_after": "loan_details_sb_1",
            },
            {
                "fieldname": "total_interest_amount",
                "fieldtype": "Currency",
                "label": _("Total Interest Amount"),
                "default": "0",
                "options": "Company:company:default_currency",
                "read_only": 1,
                "insert_after": "total_principal_amount",
            },
        ]
    }


def delete_custom_fields(custom_fields: dict):
    for doctype, fields in custom_fields.items():
        frappe.db.delete(
            "Custom Field",
            {
                "fieldname": ("in", [field["fieldname"] for field in fields]),
                "dt": doctype,
            },
        )
        frappe.clear_cache(doctype=doctype)


def update_ess_for_lending():
    """Inject Lending permissions into Employee Self Service"""
    if not frappe.db.exists("User Type", "Employee Self Service"):
        return

    doc = frappe.get_doc("User Type", "Employee Self Service")
    loan_docperms = get_lending_docperms_for_ess()

    append_docperms_to_user_type(loan_docperms, doc)

    doc.flags.ignore_links = True
    doc.save(ignore_permissions=True)


def remove_lending_docperms_from_ess():
    if not frappe.db.exists("User Type", "Employee Self Service"):
        return

    doc = frappe.get_doc("User Type", "Employee Self Service")
    loan_docperms = get_lending_docperms_for_ess()

    original_len = len(doc.user_doctypes)

    # Filter out the lending doctypes
    doc.user_doctypes = [
        row for row in doc.user_doctypes
        if row.document_type not in loan_docperms
    ]

    if len(doc.user_doctypes) != original_len:
        doc.flags.ignore_links = True
        doc.save(ignore_permissions=True)


def get_lending_docperms_for_ess():
    return {
        "Loan": ["read"],
        "Loan Application": ["read", "write", "create", "delete", "submit"],
        "Loan Product": ["read"],
    }


def append_docperms_to_user_type(docperms, doc):
    existing_doctypes = [d.document_type for d in doc.user_doctypes]

    for doctype, perms in docperms.items():
        if doctype in existing_doctypes:
            continue

        # Check if DocType exists before trying to add permissions
        if not frappe.db.exists("DocType", doctype):
            print(f"Skipping permission setup for missing DocType: {doctype}")
            continue

        args = {"document_type": doctype}
        for perm in perms:
            args[perm] = 1

        doc.append("user_doctypes", args)


def update_select_perm_after_install():
    # Retaining this small utility hook if it's still needed,
    # though it seems like generic cleanup logic.
    # Decisions: Keep it safe.
    if not frappe.flags.update_select_perm_after_migrate:
        return

    frappe.flags.ignore_select_perm = False
    # Only touching custom types to be safe
    for row in frappe.get_all("User Type", filters={"is_standard": 0}):
        # print("Updating user type :- ", row.name)
        try:
            doc = frappe.get_doc("User Type", row.name)
            doc.flags.ignore_links = True
            doc.save()
        except Exception:
            pass

    frappe.flags.update_select_perm_after_migrate = False
