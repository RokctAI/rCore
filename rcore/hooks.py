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
    # The single universal entry point for the platform (routes by site role)
    "rokct.platform.api": "rcore.platform.api.execute",
}

# Frappe's dispatcher resolves aliases from this hook (see frappe.override_whitelisted_method)
override_whitelisted_methods = {
    "rokct.platform.api": "rcore.platform.api.execute",
}
