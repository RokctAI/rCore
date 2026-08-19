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

"""
Seed data for `Scoring Rule` / `Risk Profile`, translating the design doc
(polaris/docs/credit-risk-algorithm.md, "Where this plugs in — backend") into
the rows the decision engine consumes.

Run once per site after install/migrate, e.g.:

    bench --site <site> execute rcore.polaris.rlending.decision_engine.seeds.seed_scoring_config

Seeding is idempotent: existing rows (matched by metric_name / risk_level) are
left untouched so operator-tuned values are never overwritten.

IMPORTANT — two rules are seeded DISABLED on purpose:

* ``disposable_income`` (the mandatory NCA affordability floor,
  `minDisposableIncome`): the design doc names the gate but gives NO numeric
  value, and inventing one is prohibited. Until an operator sets a real
  threshold and enables the rule, the engine fail-honests every application to
  "Pending" rather than pretending an affordability assessment happened.
* ``first_loan_max_amount`` (the cold-start ceiling, `firstLoanMaxAmount`):
  same situation — doc mandates the cap, gives no number. Cold-start
  applicants stay "Pending" until it is configured.
"""

import frappe

from rcore.polaris.rlending.decision_engine.scorecard import (
    COMPONENT_WEIGHTS,
    DEFAULT_BANDS,
)

# The doc's seeding recipe: gates as knockouts, the four weighted components,
# plus the two named config values it requires but does not quantify.
#
# Component rows carry threshold=100 / "Greater Than or Equals" deliberately:
# the graduated scorecard ignores thresholds on weighted rows (it multiplies
# the pre-computed 0-100 sub-score by the weight), but if these rows were ever
# fed through the legacy binary ScoringEngine._apply_rules() a component would
# only earn its weight at a perfect sub-score — erring toward decline, never
# toward approval (CORRECTABLE_DEFAULT_COMPONENT_RULE_THRESHOLD).
SCORING_RULE_SEEDS = [
    {
        "metric_name": "kyc_complete",
        "condition": "Equals",
        "threshold": 1,
        "weight": 0,
        "is_knockout": 1,
        "enabled": 1,
        "description": "Hard gate 1: identity verification complete. "
        "Missing/failing KYC declines outright ('KYC verification "
        "incomplete') — no score can override it.",
    },
    {
        "metric_name": "has_active_loan",
        "condition": "Equals",
        "threshold": 0,
        "weight": 0,
        "is_knockout": 1,
        "enabled": 1,
        "description": "Hard gate 2: no concurrent active loan ('Existing "
        "active loan must be settled first').",
    },
    {
        "metric_name": "disposable_income",
        "condition": "Greater Than",
        "threshold": 0,
        "weight": 0,
        "is_knockout": 1,
        "enabled": 0,
        "description": "Hard gate 3: mandatory NCA affordability floor. "
        "Threshold is minDisposableIncome — NO value is specified in the "
        "design doc, so this ships DISABLED and the engine returns Pending "
        "until an operator sets a real threshold and enables it. Do not "
        "enable with an invented number.",
    },
    {
        "metric_name": "repayment_history_score",
        "condition": "Greater Than or Equals",
        "threshold": 100,
        "weight": COMPONENT_WEIGHTS["repayment_history_score"],
        "is_knockout": 0,
        "enabled": 1,
        "description": "Component 1 (weight 45): recency-weighted repayment "
        "track record, pre-computed 0-100 by LoanHistoryAnalyzer.",
    },
    {
        "metric_name": "affordability_ratio_score",
        "condition": "Greater Than or Equals",
        "threshold": 100,
        "weight": COMPONENT_WEIGHTS["affordability_ratio_score"],
        "is_knockout": 0,
        "enabled": 1,
        "description": "Component 2 (weight 30): repayment burden as a "
        "fraction of disposable income, pre-computed 0-100.",
    },
    {
        "metric_name": "amount_to_income_score",
        "condition": "Greater Than or Equals",
        "threshold": 100,
        "weight": COMPONENT_WEIGHTS["amount_to_income_score"],
        "is_knockout": 0,
        "enabled": 1,
        "description": "Component 3 (weight 15): requested amount relative "
        "to income, pre-computed 0-100.",
    },
    {
        "metric_name": "kyc_quality_score",
        "condition": "Greater Than or Equals",
        "threshold": 100,
        "weight": COMPONENT_WEIGHTS["kyc_quality_score"],
        "is_knockout": 0,
        "enabled": 1,
        "description": "Component 4 (weight 10): graduated data-quality "
        "score over optional-but-useful fields, pre-computed 0-100.",
    },
    {
        "metric_name": "first_loan_max_amount",
        "condition": "Less Than or Equals",
        "threshold": 0,
        "weight": 0,
        "is_knockout": 0,
        "enabled": 0,
        "description": "Config value, not a rule: cold-start ceiling "
        "(firstLoanMaxAmount). Threshold holds the amount. NO value is "
        "specified in the design doc, so this ships DISABLED and cold-start "
        "applicants stay Pending until an operator sets a real amount and "
        "enables it. Do not enable with an invented number.",
    },
]

#: Doc's score-to-outcome table (0-39 / 40-59 / 60-79 / 80-100).
RISK_PROFILE_SEEDS = [
    {
        "risk_level": band["risk_level"],
        "min_score": band["min_score"],
        "max_score": band["max_score"],
        "decision": band["decision"],
        "color": band["color"],
    }
    for band in DEFAULT_BANDS
]


def seed_scoring_config():
    """Idempotently insert the Scoring Rule / Risk Profile seed rows."""
    created = {"Scoring Rule": 0, "Risk Profile": 0}

    for row in SCORING_RULE_SEEDS:
        if not frappe.db.exists("Scoring Rule", {"metric_name": row["metric_name"]}):
            doc = frappe.get_doc(dict(row, doctype="Scoring Rule"))
            doc.insert(ignore_permissions=True)
            created["Scoring Rule"] += 1

    for row in RISK_PROFILE_SEEDS:
        if not frappe.db.exists("Risk Profile", {"risk_level": row["risk_level"]}):
            doc = frappe.get_doc(dict(row, doctype="Risk Profile"))
            doc.insert(ignore_permissions=True)
            created["Risk Profile"] += 1

    frappe.db.commit()
    return created
