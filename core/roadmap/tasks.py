# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import requests
import json

# --- Main Scheduled Tasks ---

def populate_roadmap_with_ai_ideas():
    """
    (Daily Task)
    Initiates AI idea generation sessions for all configured roadmaps.
    This function runs quickly, creating tracking documents for each session
    without waiting for the results.
    """
    try:
        jules_api_key = _get_api_key()
        if not jules_api_key:
            return

        roadmaps = frappe.get_all("Roadmap", filters={"source_repository": ["is", "set"]}, fields=["name", "source_repository"])
        prompts = _get_prompts()

        if not prompts:
            frappe.log_info("No AI prompts configured in Roadmap Settings. Skipping idea generation.", "Jules Idea Generation")
            return

        for roadmap in roadmaps:
            roadmap_name = roadmap.get("name")
            if frappe.db.exists("Roadmap Feature", {"parent": roadmap_name, "status": "Ideas", "is_ai_generated": 1}):
                continue

            for prompt in prompts:
                try:
                    session_id = _create_jules_session(jules_api_key, roadmap.get("source_repository"), prompt.title, prompt.prompt)
                    if session_id:
                        # Create a tracking document instead of waiting
                        frappe.get_doc({
                            "doctype": "AI Idea Session",
                            "roadmap": roadmap_name,
                            "session_id": session_id,
                            "status": "Pending",
                            "prompt_title": prompt.title
                        }).insert(ignore_permissions=True)
                        frappe.db.commit()
                except Exception as e:
                    frappe.log_error(f"Failed to create Jules session for roadmap '{roadmap_name}': {e}", "Jules Idea Generation")

    except Exception as e:
        frappe.log_error(f"The AI idea generation task failed globally: {e}", "Jules Idea Generation")

def process_pending_ai_sessions():
    """
    (Frequent Task)
    Polls for results from all 'Pending' AI idea sessions and processes them when ready.
    """
    jules_api_key = _get_api_key()
    if not jules_api_key:
        return

    pending_sessions = frappe.get_all("AI Idea Session", filters={"status": "Pending"})

    for session_doc in pending_sessions:
        session = frappe.get_doc("AI Idea Session", session_doc.name)
        try:
            activities = _get_jules_activities(jules_api_key, session.session_id)
            if activities:
                latest_response = _get_latest_agent_message(activities)
                if latest_response:
                    ideas = _parse_ideas_from_response(latest_response)
                    if ideas:
                        for idea in ideas:
                            idea['type'] = "Bug" if "bug" in session.prompt_title.lower() else "Feature"
                        _save_ideas_to_roadmap(session.roadmap, ideas)

                    session.status = "Completed"
                    session.save(ignore_permissions=True)
                    frappe.db.commit()
        except Exception as e:
            session.status = "Error"
            session.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error(f"Failed to process AI session {session.session_id}: {e}", "Jules Idea Processing")


# --- Helper Functions ---

def _get_api_key():
    """Retrieves the Jules API key from site configuration."""
    if frappe.conf.get("app_role") == "control":
        return frappe.conf.get("jules_api_key")
    if frappe.db.exists("DocType", "Jules Settings"):
        return frappe.get_doc("Jules Settings").get_password("jules_api_key")
    return None

def _save_ideas_to_roadmap(roadmap_name, ideas):
    """Saves a list of generated ideas to a specified Roadmap document."""
    roadmap_doc = frappe.get_doc("Roadmap", roadmap_name)
    for idea in ideas:
        feature_doc = frappe.new_doc("Roadmap Feature")
        feature_doc.feature = idea.get("title")
        feature_doc.explanation = idea.get("explanation")
        feature_doc.status = "Ideas"
        feature_doc.is_ai_generated = 1
        feature_doc.type = idea.get("type", "Feature")
        roadmap_doc.append("features", feature_doc)
    roadmap_doc.save(ignore_permissions=True)
    frappe.db.commit()

def _get_prompts():
    """Returns a list of prompts from Roadmap Settings."""
    settings = frappe.get_doc("Roadmap Settings")
    return settings.prompts or []

def _parse_ideas_from_response(response_text):
    """Safely parses a JSON string and returns a list of ideas."""
    try:
        return json.loads(response_text).get("ideas", [])
    except (json.JSONDecodeError, AttributeError):
        frappe.log_error(f"Failed to parse JSON response from Jules: {response_text}", "Jules Idea Generation")
        return []

def _create_jules_session(api_key, source_repo, title, prompt):
    """Creates a new Jules session using the configured API URL."""
    settings = frappe.get_doc("Roadmap Settings")
    api_url = settings.jules_api_url or "https://jules.googleapis.com/v1alpha/sessions"

    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": api_key}
    data = {"prompt": prompt, "sourceContext": {"source": source_repo, "githubRepoContext": {"startingBranch": "main"}}, "title": title, "requirePlanApproval": True}
    response = requests.post(api_url, json=data, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json().get("name")

def _get_jules_activities(api_key, session_id):
    """Fetches activities for a given Jules session."""
    settings = frappe.get_doc("Roadmap Settings")
    api_url = (settings.jules_api_url or "https://jules.googleapis.com/v1alpha/sessions").strip('/')

    headers = {"X-Goog-Api-Key": api_key}
    response = requests.get(f"{api_url}/{session_id}/activities", headers=headers, timeout=15)
    response.raise_for_status()
    activities = response.json().get("activities", [])
    return activities if len(activities) > 1 else None

def _get_latest_agent_message(activities):
    """Extracts the latest agent message from a list of activities."""
    return next((act.get("agentActivity", {}).get("message") for act in reversed(activities) if act.get("agentActivity")), None)

def jules_task_monitor():
    # Placeholder for existing function
    pass
