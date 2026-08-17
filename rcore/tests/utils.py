import frappe


def before_tests():
    """
    Setup required data before running tests.
    """
    create_warehouse_types()
    create_customer_groups()
    create_item_groups()
    create_territories()
    create_supplier_groups()
    create_sales_persons()
    create_test_company()
    create_test_warehouses()
    create_stock_entry_types()
    create_fiscal_year()
    create_gender()
    create_roles()
    create_user_custom_fields()
    frappe.db.commit()
    frappe.clear_cache()
    print("DEBUG: Fixtures Created. Stock Entry Types:",
          frappe.db.get_all("Stock Entry Type", pluck="name"))


def create_warehouse_types():
    if frappe.db.exists("DocType", "Warehouse Type"):
        if not frappe.db.exists("Warehouse Type", "Transit"):
            frappe.get_doc({
                "doctype": "Warehouse Type",
                "name": "Transit"
            }).insert(ignore_permissions=True)


def create_customer_groups():
    if frappe.db.exists("DocType", "Customer Group"):
        if not frappe.db.exists("Customer Group", "All Customer Groups"):
            frappe.get_doc({
                "doctype": "Customer Group",
                "customer_group_name": "All Customer Groups",
                "is_group": 1,
                "parent_customer_group": ""
            }).insert(ignore_permissions=True)


def create_item_groups():
    if frappe.db.exists("DocType", "Item Group"):
        if not frappe.db.exists("Item Group", "All Item Groups"):
            frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "All Item Groups",
                "is_group": 1,
                "parent_item_group": ""
            }).insert(ignore_permissions=True)


def create_territories():
    if frappe.db.exists("DocType", "Territory"):
        if not frappe.db.exists("Territory", "All Territories"):
            frappe.get_doc({
                "doctype": "Territory",
                "territory_name": "All Territories",
                "is_group": 1,
                "parent_territory": ""
            }).insert(ignore_permissions=True)


def create_supplier_groups():
    if frappe.db.exists("DocType", "Supplier Group"):
        if not frappe.db.exists("Supplier Group", "All Supplier Groups"):
            frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": "All Supplier Groups",
                "is_group": 1,
                "parent_supplier_group": ""
            }).insert(ignore_permissions=True)


def create_sales_persons():
    if frappe.db.exists("DocType", "Sales Person"):
        if not frappe.db.exists("Sales Person", "All Sales Persons"):
            frappe.get_doc({
                "doctype": "Sales Person",
                "sales_person_name": "All Sales Persons",
                "is_group": 1,
                "parent_sales_person": ""
            }).insert(ignore_permissions=True)


def create_test_company():
    if frappe.db.exists("DocType", "Company"):
        if not frappe.db.exists("Company", "_Test Company"):
            frappe.get_doc({
                "doctype": "Company",
                "company_name": "_Test Company",
                "abbr": "_TC",
                "default_currency": "INR",
                "country": "India"
            }).insert(ignore_permissions=True)


def create_test_warehouses():
    if not frappe.db.exists("DocType", "Warehouse"):
        return

    # 1. Warehouse Group
    if not frappe.db.exists("Warehouse", "_Test Warehouse Group - _TC"):
        frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "_Test Warehouse Group",
            "company": "_Test Company",
            "is_group": 1,
            "parent_warehouse": ""
        }).insert(ignore_permissions=True)

    # 2. Child Warehouse C1
    if not frappe.db.exists("Warehouse", "_Test Warehouse Group-C1 - _TC"):
        frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "_Test Warehouse Group-C1",
            "company": "_Test Company",
            "is_group": 0,
            "parent_warehouse": "_Test Warehouse Group - _TC"
        }).insert(ignore_permissions=True)

    # 3. Default Warehouse (linked to group for consistency?)
    # Keeping it simple as root or linked depending on previous needs
    if not frappe.db.exists("Warehouse", "_Test Warehouse - _TC"):
        frappe.get_doc({
            "doctype": "Warehouse",
            "warehouse_name": "_Test Warehouse",
            "company": "_Test Company",
            "is_group": 0,
            "parent_warehouse": "_Test Warehouse Group - _TC"  # Link it to group!
        }).insert(ignore_permissions=True)


def create_stock_entry_types():
    if frappe.db.exists("DocType", "Stock Entry Type"):
        for name, purpose in [
            ("Material Receipt", "Material Receipt"),
            ("Material Issue", "Material Issue"),
            ("Material Transfer", "Material Transfer")
        ]:
            if not frappe.db.exists("Stock Entry Type", name):
                frappe.get_doc({
                    "doctype": "Stock Entry Type",
                    "name": name,
                    "purpose": purpose,
                    "is_standard": 1
                }).insert(ignore_permissions=True)


def create_fiscal_year():
    if frappe.db.exists("DocType", "Fiscal Year"):
        if not frappe.db.exists("Fiscal Year", "_Test Fiscal Year 2026"):
            frappe.get_doc({
                "doctype": "Fiscal Year",
                "year": "_Test Fiscal Year 2026",
                "year_start_date": "2026-01-01",
                "year_end_date": "2026-12-31",
                "companies": [{"company": "_Test Company"}]
            }).insert(ignore_permissions=True)


def create_gender():
    for gender in ["Male", "Female", "Other"]:
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc({
                "doctype": "Gender",
                "gender": gender
            }).insert(ignore_permissions=True)


def create_user_custom_fields():
    """
    Creates custom fields for User DocType that are required by PaaS.
    """
    if not frappe.db.exists(
            "Custom Field", {
            "dt": "User", "fieldname": "ringfenced_balance"}):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "User",
            "fieldname": "ringfenced_balance",
            "fieldtype": "Currency",
            "label": "Ringfenced Balance",
            "default": "0"
        }).insert(ignore_permissions=True)


def create_roles():
    """
    Creates roles required by PaaS.
    """
    for role in ["PaaS User", "Seller", "user"]:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1
            }).insert(ignore_permissions=True)
