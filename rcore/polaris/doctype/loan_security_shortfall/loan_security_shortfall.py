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

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt

from frappe.model.document import Document


class LoanSecurityShortfall(Document):
    """
    Record-only shell forked from Frappe Lending's `Loan Security Shortfall`
    (Phase 5). Deliberately does NOT port `check_for_ltv_shortfall` - that
    logic depends on `Loan Security`, `Loan Security Type`, `Loan Security
    Price`, and `Loan Security Assignment` (pledged-collateral valuation and
    LTV-ratio tracking), none of which exist anywhere in this fork. Polaris's
    own "secured loan" concept (asset_realisation.py's pawn-asset seizure
    flow) is a single ad hoc pawned-asset value, not a formally valued,
    margined securities portfolio - there's no evidence for what an LTV
    shortfall would even mean in that model. See the Phase 5 report.
    """

    pass
