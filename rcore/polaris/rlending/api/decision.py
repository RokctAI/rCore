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


import re

import frappe

from rcore.polaris.rlending.decision_engine.analyzers.loan_history_analyzer import (
    LoanHistoryAnalyzer,
)
from rcore.polaris.rlending.decision_engine.analyzers.paas_analyzer import (
    PaasOrderAnalyzer,
)
from rcore.polaris.rlending.decision_engine.scorecard import (
    COMPONENT_WEIGHTS,
    DEFAULT_BANDS,
    derive_cold_start_weights,
    evaluate_application,
)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\+?\d{9,15}$")


@frappe.whitelist()
def get_credit_score(loan_application: str) -> dict:
    """
    Calculates the credit score for a given Loan Application per
    polaris/docs/credit-risk-algorithm.md: regulatory hard gates first, then
    the 45/30/15/10 weighted scorecard, mapped to the 0-39 / 40-59 / 60-79 /
    80-100 outcome bands. Integrates standard application metrics and PaaS
    alternative data (if available).

    Fail-honest: if a required input or config value is missing (unset income,
    unseeded minDisposableIncome, uncomputable repayment burden) the decision
    is an explicit "Pending" with machine-readable `reasons` — never a
    fabricated score.
    tenant context check.
    """
    trace_id = frappe.form_dict.get("trace_id") or "get-credit-score-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] get_credit_score called for {loan_application}\n")
    if not loan_application:
        frappe.throw("Loan Application is required")

    app_doc = frappe.get_doc("Loan Application", loan_application)

    history_metrics = LoanHistoryAnalyzer(app_doc.applicant).analyze()
    paas_metrics = PaasOrderAnalyzer(app_doc.applicant).analyze()

    inputs = {
        "kyc_complete": _get_kyc_complete(app_doc),
        "has_active_loan": history_metrics.get("has_active_loan"),
        "loan_history": history_metrics.get("loan_history"),
        # Frappe coerces unset Currency fields to 0 on save, so 0 is
        # indistinguishable from "never filled in". Both fields therefore
        # normalize falsy (0/None) to None and the scorecard fail-honests to
        # Pending — a genuine 0-expense declaration also pends rather than
        # granting maximum disposable income (errs toward Pending, never
        # approval; see CORRECTABLE_DEFAULT note in the implementing PR).
        "monthly_income": app_doc.get("monthly_income") or None,
        "monthly_expenses": app_doc.get("monthly_expenses") or None,
        "monthly_repayment": _get_monthly_repayment(app_doc),
        "loan_amount": app_doc.get("loan_amount"),
        "max_loan_amount": frappe.db.get_value(
            "Loan Product", app_doc.loan_product, "maximum_loan_amount"
        )
        or None,
        "kyc_quality_checks": _get_kyc_quality_checks(app_doc),
    }

    result = evaluate_application(inputs, _load_scoring_config())

    result["loan_application"] = app_doc.name
    # PaaS wallet metrics are attached as alternative data for auditability;
    # the design doc assigns them no weight in the 45/30/15/10 scorecard, so
    # they do not influence the score.
    result["alternative_data"] = paas_metrics
    return result


def _get_kyc_complete(app_doc) -> int:
    """
    Hard gate 1 (doc: "KYC completeness"). The doc's idNumber/idDocumentFront/
    idDocumentBack/selfie fields live in the mobile flow, not on any backend
    doctype; the backend's existing verification step is the Lead
    `kyc_status` (the same source `LoanApplication.validate_kyc()` enforces),
    which the doc defers to ("per whatever verification step already exists").
    Anything other than a positively Verified status — including applicant
    types with no verification path — conservatively fails the gate.
    """
    if app_doc.applicant_type != "Customer":
        return 0

    customer_email = frappe.db.get_value("Customer", app_doc.applicant, "email_id")
    customer_mobile = frappe.db.get_value("Customer", app_doc.applicant, "mobile_no")

    lead = None
    if customer_email:
        lead = frappe.db.get_value("Lead", {"email_id": customer_email}, "name")
    if not lead and customer_mobile:
        lead = frappe.db.get_value("Lead", {"mobile_no": customer_mobile}, "name")

    if not lead:
        return 0

    kyc_status = frappe.db.get_value("Lead", lead, "kyc_status")
    return 1 if kyc_status == "Verified" else 0


def _get_monthly_repayment(app_doc):
    """
    Component 2 input: the proposed loan's periodic repayment burden (doc:
    "totalRepayable divided across the term"). Prefers the application's own
    computed EMI (`repayment_amount`); falls back to
    total_payable_amount / repayment_periods. Returns None when neither is
    derivable — the scorecard then fail-honests to Pending.
    """
    repayment_amount = app_doc.get("repayment_amount")
    if repayment_amount and float(repayment_amount) > 0:
        return float(repayment_amount)

    total_payable = app_doc.get("total_payable_amount")
    periods = app_doc.get("repayment_periods")
    if total_payable and periods and float(total_payable) > 0 and int(periods) > 0:
        return float(total_payable) / int(periods)

    return None


def _get_kyc_quality_checks(app_doc) -> dict:
    """
    Component 4 (doc: graduated data-quality over optional-but-useful fields).
    The forked Loan Application doctype carries no address fields, so the
    checklist is the optional contact/identity fields it does have, each
    equally weighted.
    """
    email = (app_doc.get("applicant_email_address") or "").strip()
    phone = re.sub(r"[\s\-()]", "", app_doc.get("applicant_phone_number") or "")
    return {
        "applicant_name_present": bool((app_doc.get("applicant_name") or "").strip()),
        "email_well_formed": bool(EMAIL_PATTERN.match(email)),
        "phone_well_formed": bool(PHONE_PATTERN.match(phone)),
    }


def _load_scoring_config() -> dict:
    """
    Loads the data-driven scoring configuration from the seeded `Scoring Rule`
    and `Risk Profile` records (see decision_engine/seeds.py).

    The 45/30/15/10 weights and the doc's outcome bands are also built into
    the scorecard as defaults, so absent records simply mean the doc's own
    numbers apply. The two values the doc requires but does not quantify —
    minDisposableIncome and firstLoanMaxAmount — have NO defaults: while their
    rules are missing or disabled they stay None and the scorecard returns
    Pending rather than inventing them.
    """
    config = {
        "min_disposable_income": None,
        "first_loan_max_amount": None,
        "weights": dict(COMPONENT_WEIGHTS),
        "bands": None,
    }

    if frappe.db.exists("DocType", "Scoring Rule"):
        rules = frappe.get_all(
            "Scoring Rule",
            fields=["metric_name", "threshold", "weight", "is_knockout"],
            filters={"enabled": 1},
        )
        for rule in rules:
            if rule.metric_name == "disposable_income" and rule.is_knockout:
                config["min_disposable_income"] = float(rule.threshold)
            elif rule.metric_name == "first_loan_max_amount":
                if float(rule.threshold) > 0:
                    config["first_loan_max_amount"] = float(rule.threshold)
            elif (
                rule.metric_name in COMPONENT_WEIGHTS
                and not rule.is_knockout
                and float(rule.weight) > 0
            ):
                config["weights"][rule.metric_name] = float(rule.weight)

    config["cold_start_weights"] = derive_cold_start_weights(config["weights"])
    config["bands"] = _load_bands()
    return config


def _load_bands():
    """
    Risk Profile records may re-label the doc's bands (decision/risk_level/
    color) but the band ranges, eligibility and max-amount policy come from
    the design doc's score-to-outcome table and are not overridable here — a
    mislabelled record must not be able to widen eligibility.
    """
    bands = [dict(band) for band in DEFAULT_BANDS]
    if not frappe.db.exists("DocType", "Risk Profile"):
        return bands

    profiles = frappe.get_all(
        "Risk Profile",
        fields=["risk_level", "min_score", "max_score", "decision", "color"],
        order_by="min_score asc",
    )
    for band in bands:
        for profile in profiles:
            if (
                profile.min_score == band["min_score"]
                and profile.max_score == band["max_score"]
            ):
                band["risk_level"] = profile.risk_level
                band["color"] = profile.color
                # "Decline" from a matching profile is honored (narrowing);
                # a profile cannot turn a doc-declined band eligible.
                if profile.decision == "Decline":
                    band["is_eligible"] = False
                    band["max_amount_policy"] = "zero"
                if band["is_eligible"]:
                    band["decision"] = profile.decision
                break
    return bands
