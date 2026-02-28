# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RoadmapSettings(Document):
    def before_save(self):
        """
        On saving the Roadmap Settings, automatically generate a GitHub Action Secret
        if one does not already exist, and populate default security prompts.
        """
        if not self.github_action_secret:
            self.github_action_secret = frappe.generate_hash(length=40)

        # POPULATE DEFAULT SECURITY PROMPTS
        if not self.prompts:
            self.append("prompts", {
                "title": "Security Sentinel Scan",
                "type": "Bug",
                "mode": "Planning",
                "prompt": "Act as Guardian, the security protector of the codebase. Your philosophy is 'Trust Nothing, Verify Everything.' Scan the codebase and roadmap context for: 1) Hardcoded Secrets (API keys, passwords), 2) Injection risks (SQL/Shell), 3) Data Exposure (sensitive info in logs/errors), and 4) Auth & Access bypasses. Prioritize Critical vulnerabilities. Output a list of potential bugs and vulnerabilities in JSON format."
            })
            self.append("prompts", {
                "title": "Guardian Implementation Fix",
                "type": "Bug",
                "mode": "Building",
                "prompt": "Act as Guardian. Your goal is to fix security vulnerabilities using a defense-in-depth approach. Prioritize Critical issues (Secrets, Injection, Auth Bypass). Follow the PR format: '🛡️ Sentinel: [Severity] [Summary]'. Explain the Vulnerability, Impact, and Fix. Always run tests/lint before reporting, and use established security libraries. Trust Nothing, Verify Everything."
            })
            self.append("prompts", {
                "title": "Lead Architect: Feature Ideation",
                "type": "Feature",
                "mode": "Planning",
                "prompt": "Act as a Senior Software Architect. The project stack is: {stack}. The dependencies are: {dependency}. The platform contexts are: {platform}. Brainstorm feature ideas that add high value to the project roadmap based on the current codebase and project status. Focus on modularity, scalability, and user impact. For each idea, you MUST assign one or more of the following Tags: ['Frontend', 'Backend', 'UI', 'UX', 'Database', 'Security', 'API', 'Mobile']. Provide output in JSON format."
            })
            self.append("prompts", {
                "title": "Lead Architect: Implementation",
                "type": "Feature",
                "mode": "Building",
                "prompt": """Act as a Senior Engineer.
Project Stack: {stack}
Dependencies: {dependency}
Context Tags: {feature_tags}

Implementation Guidelines:
{tag_guidelines}

General Rules:
1. Follow existing project patterns (e.g., Vertical Slices).
2. Write clean, documented, and testable code.
3. Ensure no breaking changes to existing functionality."""
            })


def populate_defaults():
    """Manual trigger to populate default prompts if empty."""
    settings = frappe.get_doc("Roadmap Settings")
    settings.save()
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def get_public_roadmap_content():
    """
    Returns the content of the configured Public Roadmap.
    Used by the frontend to render the public roadmap page.
    """
    settings = frappe.get_single("Roadmap Settings")
    if not settings.public_roadmap:
        return None

    roadmap = frappe.get_doc("Roadmap", settings.public_roadmap)
    features = frappe.get_all(
        "Roadmap Feature",
        filters={
            "roadmap": settings.public_roadmap,
            "status": [
                "!=",
                "Idea"]},
        fields=[
            "feature",
            "description",
            "status",
            "priority",
            "ai_status"],
        order_by="creation desc")

    return {
        "title": roadmap.title,
        "description": roadmap.description,
        "features": features
    }
