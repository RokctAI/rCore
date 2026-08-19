# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

# ROKCT: cross-module imports into the composed erp module are resolved from
# __name__ — the composer's app-name token must not appear in doctype-tree
# .py files (designer design_system.py precedent), and the erp SDK module
# composes as a sibling package of this crm module.
from importlib import import_module as _import_module


def _erp_import(path):
	"""Import '<app>.erp.<path>' relative to this module's composed app."""
	return _import_module(__name__.split(".crm.doctype.", 1)[0] + ".erp." + path)

_utils_mod = _erp_import("tests.utils")
ERPNextTestSuite = _utils_mod.ERPNextTestSuite


class TestMarketSegment(ERPNextTestSuite):
	pass
