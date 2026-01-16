# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe

class ScoringEngine:
    """
    A service to calculate a credit score based on a set of metrics and configurable rules.
    This centralized engine handles both standard lending rules and PaaS-specific logic.
    """
    def __init__(self, metrics):
        self.metrics = metrics
        self.rules = []
        self.score = 0
        self.breakdown = []

    def load_rules(self):
        """
        Fetches 'Scoring Rule' documents from the database.
        """
        if frappe.db.exists("DocType", "Scoring Rule"):
            self.rules = frappe.get_all("Scoring Rule", fields=["metric_name", "condition", "threshold", "weight", "is_knockout"], filters={"enabled": 1})

    def calculate_score(self):
        """
        Main method to trigger the score calculation.
        """
        if not self.rules:
            self.load_rules()
            
        self._apply_rules()
        
        # Determine Decision and Risk Level
        risk_profile = self._get_risk_profile()
        
        return {
            "score": self.score,
            "breakdown": self.breakdown,
            "decision": risk_profile.get("decision", "Review"),
            "risk_level": risk_profile.get("risk_level", "Unknown"),
            "color": risk_profile.get("color", "Gray")
        }, self.breakdown

    def _apply_rules(self):
        """
        Applies rules. Handles Knockouts (Score -> 0).
        """
        if not self.rules:
            self.score = 0
            return

        total_weight = sum(rule.weight for rule in self.rules if not rule.is_knockout)
        # Avoid division by zero if all are knockouts (edge case) or no weights
        if total_weight == 0: total_weight = 1

        knockout_triggered = False

        for rule in self.rules:
            metric_value = self.metrics.get(rule.metric_name, 0)

            rule_passed = False
            threshold = float(rule.threshold)
            value = float(metric_value)

            if rule.condition == "Greater Than": rule_passed = value > threshold
            elif rule.condition == "Less Than": rule_passed = value < threshold
            elif rule.condition == "Equals": rule_passed = value == threshold
            elif rule.condition == "Greater Than or Equals": rule_passed = value >= threshold
            elif rule.condition == "Less Than or Equals": rule_passed = value <= threshold

            # Knockout Logic: Rule MUST pass. If failed, immediate Zero.
            if rule.is_knockout and not rule_passed:
                knockout_triggered = True
                self.breakdown.append({
                    "metric_name": rule.metric_name,
                    "score": 0,
                    "weight": 0,
                    "description": f"KNOCKOUT FAILED: {rule.condition} {rule.threshold}, Value: {metric_value}"
                })
                break # Stop processing

            if not rule.is_knockout:
                weighted_score = (rule.weight / total_weight) * 100 if rule_passed else 0
                if weighted_score > 0:
                    self.score += weighted_score

            self.breakdown.append({
                "metric_name": rule.metric_name,
                "score": 100 if rule_passed else 0, # Raw success/fail
                "weight": rule.weight,
                "description": f"Condition: {rule.condition} {rule.threshold}, Value: {metric_value}"
            })

        if knockout_triggered:
            self.score = 0
        else:
            self.score = int(self.score)

    def _get_risk_profile(self):
        """
        Matches standard score (0-100) to a Risk Profile.
        """
        if frappe.db.exists("DocType", "Risk Profile"):
            profiles = frappe.get_all("Risk Profile", fields=["risk_level", "min_score", "max_score", "decision", "color"], order_by="min_score asc")
            for p in profiles:
                if p.min_score <= self.score <= p.max_score:
                    return p
        
        # Fallback Defaults
        if self.score >= 70: return {"decision": "Approve", "risk_level": "Low Risk", "color": "Green"}
        if self.score >= 40: return {"decision": "Review", "risk_level": "Medium Risk", "color": "Orange"}
        return {"decision": "Decline", "risk_level": "High Risk", "color": "Red"}
