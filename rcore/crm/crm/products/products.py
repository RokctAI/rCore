# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

"""Platform product-rate API, ported from the standalone CRM Products child
controller onto the erp `Item` master (CRM Product dissolved into Item in the
CRM merge wave). The historic api.crm.products.get_product_rate_details cmd
alias keeps resolving here."""

import frappe


@frappe.whitelist()
def get_product_rate_details(product_code: str, deal: str | None = None) -> dict:
	"""Rate details for a product line.

	ERPNext price-list resolution is not part of this slice: the item's
	standard rate is always used.
	"""
	product = (
		frappe.db.get_value("Item", product_code, ["item_name", "standard_rate"], as_dict=True)
		or {}
	)
	return {"product_name": product.get("item_name"), "rate": product.get("standard_rate")}
