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
Pure-python credit scorecard implementing polaris/docs/credit-risk-algorithm.md.

This module deliberately imports NOTHING from frappe so the underwriting math is
locally unit-testable. The frappe-facing wiring lives in `api/decision.py` and
`decision_engine/analyzers/loan_history_analyzer.py`, which gather inputs from
doctypes and hand plain dicts to `evaluate_application()`.

Two invariants (regulated lending — do not weaken):

1. Doc-specified numbers only. The hard gates, the 45/30/15/10 component weights
   and the 0-39 / 40-59 / 60-79 / 80-100 decision bands come verbatim from the
   design doc. Where the doc names a mechanism but gives no formula or number,
   the simplest CONSERVATIVE interpretation is used (errs toward lower score /
   decline / Pending, never toward approving) and is isolated behind a clearly
   named CORRECTABLE_DEFAULT constant/function below, so a reviewer can correct
   it in one place. The full list is in the implementing PR.

2. Fail-honest. If a required input or config value is missing (unset income,
   unseeded `minDisposableIncome`, uncomputable repayment burden), the result is
   an explicit "Pending" with machine-readable reason codes — never a fabricated
   or partially-fabricated score presented as real.
"""

import datetime

# ---------------------------------------------------------------------------
# Doc-specified constants (design doc is the sole authority for these values)
# ---------------------------------------------------------------------------

#: Component weights, doc section "Scoring model" (45/30/15/10).
COMPONENT_WEIGHTS = {
    "repayment_history_score": 45.0,
    "affordability_ratio_score": 30.0,
    "amount_to_income_score": 15.0,
    "kyc_quality_score": 10.0,
}

def derive_cold_start_weights(weights):
    """
    Doc section "Cold-start applicants": component 1's weight is redistributed
    into components 2 and 3. The doc does not state the split; proportional to
    their own weights (30/15 => 2:1) is the interpretation that changes the
    doc's relative component ordering least
    (CORRECTABLE_DEFAULT_COLD_START_SPLIT). Component 4 is explicitly not a
    recipient in the doc.
    """
    redistributed = dict(weights)
    history = redistributed.get("repayment_history_score", 0.0)
    affordability = redistributed.get("affordability_ratio_score", 0.0)
    amount = redistributed.get("amount_to_income_score", 0.0)
    denominator = affordability + amount
    if denominator > 0:
        redistributed["affordability_ratio_score"] = (
            affordability + history * affordability / denominator
        )
        redistributed["amount_to_income_score"] = (
            amount + history * amount / denominator
        )
    redistributed["repayment_history_score"] = 0.0
    return redistributed


#: With the doc's 45/30/15/10 weights this is 0/60/30/10.
COLD_START_WEIGHTS = derive_cold_start_weights(COMPONENT_WEIGHTS)

#: Decline reasons for the hard gates. The gate 1-2 strings (KYC_INCOMPLETE,
#: ACTIVE_LOAN) are verbatim from the doc's "Regulatory gate first" section;
#: the two gate-3 strings (AFFORDABILITY_FLOOR, REPAYMENT_UNAFFORDABLE) are
#: authored here — the doc names the gate but supplies no wording for them.
REASON_KYC_INCOMPLETE = "KYC verification incomplete"
REASON_ACTIVE_LOAN = "Existing active loan must be settled first"
REASON_AFFORDABILITY_FLOOR = "Disposable income below required minimum"
REASON_REPAYMENT_UNAFFORDABLE = "Loan repayment burden breaches affordability"

#: Score-to-outcome bands, doc section "Score-to-outcome mapping" (verbatim
#: ranges). `max_amount_policy` encodes the doc's third column. Labels
#: (decision/risk_level/color) are not specified by the doc for these bands;
#: the mapping below keeps `decision` consistent with the doc's `isEligible`
#: column (CORRECTABLE_DEFAULT_BAND_LABELS). Seeded `Risk Profile` records
#: mirror these and, when present, override the labels at runtime.
DEFAULT_BANDS = [
    {
        "min_score": 0,
        "max_score": 39,
        "is_eligible": False,
        "max_amount_policy": "zero",
        "decision": "Decline",
        "risk_level": "High Risk",
        "color": "Red",
    },
    {
        "min_score": 40,
        "max_score": 59,
        "is_eligible": True,
        "max_amount_policy": "reduced_fraction",
        "decision": "Approve",
        "risk_level": "Medium Risk",
        "color": "Orange",
    },
    {
        "min_score": 60,
        "max_score": 79,
        "is_eligible": True,
        "max_amount_policy": "requested_up_to_config_max",
        "decision": "Approve",
        "risk_level": "Low Risk",
        "color": "Green",
    },
    {
        "min_score": 80,
        "max_score": 100,
        "is_eligible": True,
        "max_amount_policy": "requested",
        "decision": "Approve",
        "risk_level": "Very Low Risk",
        "color": "Green",
    },
]

# ---------------------------------------------------------------------------
# Correctable defaults (doc names the mechanism but gives no number/curve).
# All are conservative. Change the constant to recalibrate — nothing else.
# ---------------------------------------------------------------------------

#: Doc: late-but-repaid loans get "partial credit, scaled down by how many days
#: late" — no scaling function given. Default: linear from full credit at 0
#: days late to zero credit at this many days late (and beyond).
CORRECTABLE_DEFAULT_LATE_ZERO_CREDIT_DAYS = 30.0

#: Doc: "a single genuine default should weigh heavily negative" — no magnitude
#: given. Default: a defaulted/written-off loan contributes -100 (the exact
#: negative of a perfect loan) before the component clamp to [0, 100].
CORRECTABLE_DEFAULT_DEFAULTED_LOAN_CREDIT = -100.0

#: Doc: "weight more recent loans more heavily than older ones" — no decay
#: function given. Default: exponential decay of a loan's weight with the age
#: of its outcome, halving every 365 days.
CORRECTABLE_DEFAULT_RECENCY_HALF_LIFE_DAYS = 365.0

#: Doc: affordability ratio (repayment burden / disposable income) — "lower
#: ratio scores higher", no curve given. Default: linear, 100 at ratio 0 down
#: to 0 at this ratio (repayment consuming all disposable income) and beyond.
CORRECTABLE_DEFAULT_AFFORDABILITY_RATIO_AT_ZERO_SCORE = 1.0

#: Doc: requested-amount-relative-to-income — no mapping given. Default:
#: linear, 100 at ratio 0 down to 0 when the requested amount equals this
#: multiple of monthly income (and beyond).
CORRECTABLE_DEFAULT_AMOUNT_TO_INCOME_RATIO_AT_ZERO_SCORE = 1.0

#: Doc: 40-59 band grants "reduced fraction of the requested/config max
#: (conservative)" — fraction not quantified. Default: half.
CORRECTABLE_DEFAULT_REDUCED_BAND_FRACTION = 0.5

#: Doc gate 3 says to "reject if the loan's own repayment burden would breach
#: affordability" without defining "breach". Default: servicing the proposed
#: instalment may not push the applicant below the configured mandatory
#: disposable-income floor (see repayment_breaches_affordability_floor()).


def _clamp(value, low, high):
    return max(low, min(high, value))


def _add_months(day, months):
    """Pure month arithmetic (no frappe.utils): clamp day-of-month to the
    target month's length, matching frappe.utils.add_months behaviour."""
    month_index = day.month - 1 + int(months)
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    # last day of target month
    if month == 12:
        last = 31
    else:
        last = (datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)).day
    return datetime.date(year, month, min(day.day, last))


# ---------------------------------------------------------------------------
# Component 1 — repayment history (weight 45)
# ---------------------------------------------------------------------------

def build_loan_history_records(loans, repayments, as_of):
    """
    Turn raw `Loan` / `Loan Repayment` rows (plain dicts) into the per-loan
    outcome records that score_repayment_history() consumes.

    loans: [{"name", "status", "disbursement_date", "closure_date",
             "repayment_periods", "posting_date"}]
    repayments: [{"against_loan", "posting_date"}]  (submitted repayments only)
    as_of: datetime.date used for recency ages.

    Statuses "Closed"/"Settled" count as repaid in full; "Written Off" counts
    as defaulted. Any other status is an open/active loan and is excluded from
    history (it is handled by the concurrent-active-loan hard gate instead)
    (CORRECTABLE_DEFAULT_LOAN_STATUS_MAP).

    Due date is reconstructed as disbursement_date + repayment_periods months,
    exactly as the doc suggests when the original due date is not retained. If
    the due date or the final repayment date cannot be established for a repaid
    loan, the loan's timeliness is unverifiable and it conservatively earns
    zero credit rather than being assumed on-time
    (CORRECTABLE_DEFAULT_UNVERIFIABLE_TIMELINESS_CREDIT = 0).
    """
    last_repayment_by_loan = {}
    for row in repayments or []:
        loan_name = row.get("against_loan")
        paid_on = _coerce_date(row.get("posting_date"))
        if loan_name is None or paid_on is None:
            continue
        prev = last_repayment_by_loan.get(loan_name)
        if prev is None or paid_on > prev:
            last_repayment_by_loan[loan_name] = paid_on

    records = []
    for loan in loans or []:
        status = loan.get("status")
        if status not in ("Closed", "Settled", "Written Off"):
            continue  # open loan — the active-loan gate deals with it

        disbursed = _coerce_date(loan.get("disbursement_date"))
        closed = _coerce_date(loan.get("closure_date"))
        posted = _coerce_date(loan.get("posting_date"))
        last_repayment = last_repayment_by_loan.get(loan.get("name"))

        reference_date = closed or last_repayment or disbursed or posted or as_of
        age_days = max(0, (as_of - reference_date).days)

        if status == "Written Off":
            records.append(
                {"outcome": "defaulted", "days_late": None, "age_days": age_days}
            )
            continue

        periods = loan.get("repayment_periods")
        due_date = None
        if disbursed is not None and periods:
            due_date = _add_months(disbursed, int(periods))

        if due_date is None or last_repayment is None:
            # Repaid, but timeliness unverifiable — conservative zero credit.
            records.append(
                {"outcome": "unverifiable", "days_late": None, "age_days": age_days}
            )
            continue

        days_late = max(0, (last_repayment - due_date).days)
        records.append(
            {"outcome": "repaid", "days_late": days_late, "age_days": age_days}
        )

    return records


def _coerce_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def per_loan_credit(record):
    """Credit for one historical loan, per the doc's three outcomes."""
    outcome = record.get("outcome")
    if outcome == "defaulted":
        return CORRECTABLE_DEFAULT_DEFAULTED_LOAN_CREDIT
    if outcome == "unverifiable":
        return 0.0
    days_late = float(record.get("days_late") or 0)
    if days_late <= 0:
        return 100.0  # on-time full repayment: full credit
    # late but repaid: partial credit scaled down by days late
    return 100.0 * max(
        0.0, 1.0 - days_late / CORRECTABLE_DEFAULT_LATE_ZERO_CREDIT_DAYS
    )


def score_repayment_history(history_records):
    """
    Aggregate per-loan credits into the 0-100 component score, recency-weighted.

    Returns None when there is no history at all — the cold-start signal; the
    doc forbids treating "unknown" as a neutral middling score.
    """
    if not history_records:
        return None

    weighted_sum = 0.0
    weight_sum = 0.0
    for record in history_records:
        age_days = float(record.get("age_days") or 0)
        recency_weight = 0.5 ** (
            age_days / CORRECTABLE_DEFAULT_RECENCY_HALF_LIFE_DAYS
        )
        weighted_sum += recency_weight * per_loan_credit(record)
        weight_sum += recency_weight

    if weight_sum <= 0:
        return 0.0
    return _clamp(weighted_sum / weight_sum, 0.0, 100.0)


# ---------------------------------------------------------------------------
# Components 2-4
# ---------------------------------------------------------------------------

def score_affordability_ratio(monthly_repayment, monthly_income, monthly_expenses):
    """Component 2 (weight 30): repayment burden as a fraction of disposable
    income; lower ratio scores higher."""
    disposable = float(monthly_income) - float(monthly_expenses)
    if disposable <= 0:
        return 0.0
    ratio = float(monthly_repayment) / disposable
    return 100.0 * max(
        0.0, 1.0 - ratio / CORRECTABLE_DEFAULT_AFFORDABILITY_RATIO_AT_ZERO_SCORE
    )


def score_amount_to_income(loan_amount, monthly_income):
    """Component 3 (weight 15): requested amount relative to income,
    independent of term."""
    income = float(monthly_income)
    if income <= 0:
        return 0.0
    ratio = float(loan_amount) / income
    return 100.0 * max(
        0.0, 1.0 - ratio / CORRECTABLE_DEFAULT_AMOUNT_TO_INCOME_RATIO_AT_ZERO_SCORE
    )


def score_kyc_quality(checks):
    """
    Component 4 (weight 10): graduated data-quality score over
    optional-but-useful fields (doc: "address fields complete, phone number
    valid format, etc."). `checks` is {check_name: bool}; each check carries
    equal weight (CORRECTABLE_DEFAULT_KYC_QUALITY_EQUAL_WEIGHTS). An empty
    checklist scores 0 — a thin application earns nothing here, it is not
    excused from the component.
    """
    if not checks:
        return 0.0
    passed = sum(1 for ok in checks.values() if ok)
    return 100.0 * passed / len(checks)


# ---------------------------------------------------------------------------
# Hard gates (doc: "Regulatory gate first" — no score can override them)
# ---------------------------------------------------------------------------

def repayment_breaches_affordability_floor(
    monthly_repayment, disposable_income, min_disposable_income
):
    """
    Doc gate 3, second clause: "reject if the loan's own repayment burden would
    breach affordability". The doc gives no formula; the conservative default
    is that servicing the instalment must not push the applicant below the
    configured mandatory disposable-income floor.
    """
    return (disposable_income - monthly_repayment) < min_disposable_income


# ---------------------------------------------------------------------------
# Result assembly
# ---------------------------------------------------------------------------

def _pending(reasons, extra=None):
    result = {
        "score": None,
        "decision": "Pending",
        "risk_level": "Unknown",
        "color": "Gray",
        "is_eligible": False,
        "max_allowed_amount": 0,
        "reasons": reasons,
        "breakdown": [],
    }
    if extra:
        result.update(extra)
    return result


def _decline(reasons, breakdown=None, extra=None):
    result = {
        "score": 0,
        "decision": "Decline",
        "risk_level": "High Risk",
        "color": "Red",
        "is_eligible": False,
        "max_allowed_amount": 0,
        "reasons": reasons,
        "breakdown": breakdown or [],
    }
    if extra:
        result.update(extra)
    return result


def _reason(code, message):
    return {"code": code, "reason": message}


def map_score_to_band(score, bands=None):
    """Map an integer 0-100 score to its band. Bands must be contiguous and
    cover 0-100 (the doc's table does)."""
    for band in bands or DEFAULT_BANDS:
        if band["min_score"] <= score <= band["max_score"]:
            return band
    # Defensive: never invent an approval for an unmapped score.
    return DEFAULT_BANDS[0]


def evaluate_application(inputs, config):
    """
    Evaluate one loan application. Pure: everything arrives as plain values.

    inputs:
        kyc_complete: 0/1 — identity verification passed (gate 1)
        has_active_loan: 0/1 (gate 2)
        monthly_income / monthly_expenses: currency or None
        monthly_repayment: proposed instalment burden per month, or None
        loan_amount: requested principal
        max_loan_amount: configured product/config maximum, or None
        loan_history: list from build_loan_history_records(), or [] (cold
            start), or None meaning "history could not be determined"
        kyc_quality_checks: {name: bool} for component 4

    config:
        min_disposable_income: mandatory floor (gate 3), or None if unseeded
        first_loan_max_amount: cold-start ceiling, or None if unseeded
        weights / cold_start_weights: optional overrides (doc defaults used
            otherwise)
        bands: optional Risk Profile band list (doc defaults used otherwise)

    Returns a dict with score/decision/risk_level/color/is_eligible/
    max_allowed_amount/reasons/breakdown/component_scores/cold_start.
    Fail-honest: anything uncomputable => decision "Pending" with reasons.
    """
    config = config or {}
    inputs = inputs or {}

    # --- Gates 1 and 2 need no configuration: evaluate first (doc order). ---
    if not inputs.get("kyc_complete"):
        return _decline([_reason("kyc_incomplete", REASON_KYC_INCOMPLETE)])

    if inputs.get("has_active_loan") is None:
        return _pending(
            [
                _reason(
                    "loan_state_unavailable",
                    "Active-loan status could not be determined",
                )
            ]
        )
    if inputs.get("has_active_loan"):
        return _decline([_reason("active_loan", REASON_ACTIVE_LOAN)])

    # --- Fail-honest: collect everything that blocks computation. ---
    pending_reasons = []

    min_disposable = config.get("min_disposable_income")
    if min_disposable is None:
        pending_reasons.append(
            _reason(
                "min_disposable_income_not_configured",
                "Mandatory affordability floor (minDisposableIncome) is not "
                "configured — seed the 'disposable_income' Scoring Rule",
            )
        )

    monthly_income = inputs.get("monthly_income")
    if monthly_income is None or float(monthly_income) <= 0:
        pending_reasons.append(
            _reason(
                "monthly_income_missing",
                "Monthly income is missing or zero on the application",
            )
        )

    # Mirrors the income handling above: frappe coerces unset Currency fields
    # to 0 on save, so a declared 0 is indistinguishable from "never filled
    # in". A genuine 0-expense declaration therefore pends too rather than
    # being scored with maximum disposable income — errs toward Pending,
    # never approval (CORRECTABLE_DEFAULT: zero-vs-unset ambiguity).
    monthly_expenses = inputs.get("monthly_expenses")
    if monthly_expenses is None or float(monthly_expenses) <= 0:
        pending_reasons.append(
            _reason(
                "monthly_expenses_missing",
                "Monthly expenses are missing or zero on the application",
            )
        )

    monthly_repayment = inputs.get("monthly_repayment")
    if monthly_repayment is None or float(monthly_repayment) <= 0:
        pending_reasons.append(
            _reason(
                "repayment_burden_unavailable",
                "Proposed repayment burden could not be derived from the "
                "application's repayment terms",
            )
        )

    loan_amount = inputs.get("loan_amount")
    if loan_amount is None or float(loan_amount) <= 0:
        pending_reasons.append(
            _reason("loan_amount_missing", "Requested loan amount is missing")
        )

    loan_history = inputs.get("loan_history")
    if loan_history is None:
        pending_reasons.append(
            _reason(
                "loan_history_unavailable",
                "Repayment history could not be determined",
            )
        )

    if pending_reasons:
        return _pending(pending_reasons)

    monthly_income = float(monthly_income)
    monthly_expenses = float(monthly_expenses)
    monthly_repayment = float(monthly_repayment)
    loan_amount = float(loan_amount)
    min_disposable = float(min_disposable)

    # --- Gate 3: mandatory affordability floor. ---
    disposable = monthly_income - monthly_expenses
    if not disposable > min_disposable:
        return _decline(
            [_reason("affordability_floor", REASON_AFFORDABILITY_FLOOR)]
        )
    if repayment_breaches_affordability_floor(
        monthly_repayment, disposable, min_disposable
    ):
        return _decline(
            [_reason("repayment_unaffordable", REASON_REPAYMENT_UNAFFORDABLE)]
        )

    # --- Components. ---
    history_score = score_repayment_history(loan_history)
    cold_start = history_score is None

    component_scores = {
        "repayment_history_score": 0.0 if cold_start else history_score,
        "affordability_ratio_score": score_affordability_ratio(
            monthly_repayment, monthly_income, monthly_expenses
        ),
        "amount_to_income_score": score_amount_to_income(
            loan_amount, monthly_income
        ),
        "kyc_quality_score": score_kyc_quality(
            inputs.get("kyc_quality_checks") or {}
        ),
    }

    if cold_start:
        weights = dict(config.get("cold_start_weights") or COLD_START_WEIGHTS)
    else:
        weights = dict(config.get("weights") or COMPONENT_WEIGHTS)

    total_weight = sum(weights.values())
    if total_weight <= 0:
        return _pending(
            [
                _reason(
                    "scoring_weights_invalid",
                    "Configured component weights sum to zero",
                )
            ]
        )

    raw_score = sum(
        (weights.get(name, 0.0) / total_weight) * _clamp(value, 0.0, 100.0)
        for name, value in component_scores.items()
    )
    # int() truncation matches the existing ScoringEngine convention (rounds
    # down — conservative; the doc gives no rounding rule).
    score = int(_clamp(raw_score, 0.0, 100.0))

    band = map_score_to_band(score, config.get("bands"))

    breakdown = [
        {
            "metric_name": name,
            "score": round(_clamp(value, 0.0, 100.0), 2),
            "weight": weights.get(name, 0.0),
            "description": "Component score (0-100), weighted {0}/{1}".format(
                weights.get(name, 0.0), total_weight
            ),
        }
        for name, value in component_scores.items()
    ]

    extra = {
        "component_scores": component_scores,
        "weights_used": weights,
        "cold_start": cold_start,
    }

    if not band["is_eligible"]:
        return _decline(
            [_reason("score_below_minimum", "Score {0} is in the decline band".format(score))],
            breakdown=breakdown,
            extra=dict(extra, score=score, risk_level=band["risk_level"], color=band["color"]),
        )

    # --- Eligible: work out max_allowed_amount per the doc's band table. ---
    max_config = inputs.get("max_loan_amount")
    policy = band["max_amount_policy"]

    if policy in ("reduced_fraction", "requested_up_to_config_max") and (
        max_config is None or float(max_config) <= 0
    ):
        return _pending(
            [
                _reason(
                    "max_loan_amount_not_configured",
                    "Maximum loan amount is not configured for this product",
                )
            ],
            extra=dict(extra, score=score),
        )

    if policy == "reduced_fraction":
        max_allowed = CORRECTABLE_DEFAULT_REDUCED_BAND_FRACTION * min(
            loan_amount, float(max_config)
        )
    elif policy == "requested_up_to_config_max":
        max_allowed = min(loan_amount, float(max_config))
    else:  # "requested" (80-100 band)
        max_allowed = loan_amount

    if cold_start:
        first_loan_max = config.get("first_loan_max_amount")
        if first_loan_max is None or float(first_loan_max) <= 0:
            return _pending(
                [
                    _reason(
                        "first_loan_max_amount_not_configured",
                        "Cold-start ceiling (firstLoanMaxAmount) is not "
                        "configured — seed the 'first_loan_max_amount' "
                        "Scoring Rule",
                    )
                ],
                extra=dict(extra, score=score),
            )
        max_allowed = min(max_allowed, float(first_loan_max))

    return {
        "score": score,
        "decision": band["decision"],
        "risk_level": band["risk_level"],
        "color": band["color"],
        "is_eligible": True,
        "max_allowed_amount": max_allowed,
        "reasons": [],
        "breakdown": breakdown,
        "component_scores": component_scores,
        "weights_used": weights,
        "cold_start": cold_start,
    }
