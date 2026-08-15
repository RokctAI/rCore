# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

app_name = "rcore"
app_title = "Rcore"
app_publisher = "ROKCT INTELLIGENCE (PTY) LTD"
app_description = "Core business logic and utilities"
app_email = "admin@rokct.ai"
app_license = "mit"

# Whitelisted Methods (Public APIs)
whitelisted_methods = {
    # The two universal entry points for the platform
    "rokct.platform.api.tenant": "rcore.platform.api.execute_tenant",
    "rokct.platform.api.control": "rcore.platform.api.execute_control",
}

# Frappe's dispatcher resolves aliases from this hook (see frappe.override_whitelisted_method)
override_whitelisted_methods = {
    "rokct.platform.api.tenant": "rcore.platform.api.execute_tenant",
    "rokct.platform.api.control": "rcore.platform.api.execute_control",
}
