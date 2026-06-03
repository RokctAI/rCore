# API Reference: setup

Source file: `rcore/rhrms/setup.py`

## Documented Module Functions

### `def after_install()`
This hook runs after the app is installed.
We use it to apply our Custom Extensions on top of the standard HRMS.

### `def after_app_install(app_name)`
Set up loan integration with payroll when Lending app is installed

### `def before_app_uninstall(app_name)`
Clean up loan integration with payroll when Lending app is uninstalled
