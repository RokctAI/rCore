# ROKCT: the erpnext test-suite base class resolves against the composed erp
# module (pay SDK's ERPNext port) instead of the separate erpnext app.
from rcore.erp.tests.utils import ERPNextTestSuite


class PaymentsTestSuite(ERPNextTestSuite):
	"""Class for creating Payments test records"""

	pass
