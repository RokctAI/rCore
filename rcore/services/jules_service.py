# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import requests
import frappe
from frappe.utils import get_url


class JulesClient:
    BASE_URL = "https://jules.googleapis.com/v1alpha"

    def __init__(self):
        pass

    def _get_headers(self, api_key):
        if not api_key:
            frappe.throw("Jules API Key is missing.")
        return {"Content-Type": "application/json", "X-Goog-Api-Key": api_key}

    def create_session(
        self,
        api_key,
        prompt,
        source_repo,
        automation_mode="AUTO_CREATE_PR",
        require_approval=False,
        title=None,
        branch="main",
    ):
        """Creates a new Jules session."""
        if not source_repo:
            frappe.throw("Source Repository is missing.")

        url = f"{self.BASE_URL}/sessions"
        payload = {
            "prompt": prompt,
            "sourceContext": {
                "source": source_repo,
                "githubRepoContext": {"startingBranch": branch},
            },
            "automationMode": automation_mode,
            "requirePlanApproval": require_approval,
        }
        if title:
            payload["title"] = title

        try:
            response = requests.post(
                url, json=payload, headers=self._get_headers(api_key), timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def get_session(self, api_key, session_id):
        """Gets full session details (including status and outputs)."""
        url = f"{self.BASE_URL}/sessions/{session_id}"
        try:
            response = requests.get(url, headers=self._get_headers(api_key), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def delete_session(self, api_key, session_id):
        """Deletes a session (cleanup)."""
        url = f"{self.BASE_URL}/sessions/{session_id}"
        try:
            response = requests.delete(
                url, headers=self._get_headers(api_key), timeout=10
            )
            response.raise_for_status()
            return {"status": "deleted", "session_id": session_id}
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def get_activities(self, api_key, session_id):
        """Fetches activity log for the session."""
        url = f"{self.BASE_URL}/sessions/{session_id}/activities"
        try:
            response = requests.get(url, headers=self._get_headers(api_key), timeout=10)
            response.raise_for_status()
            return response.json().get("activities", [])
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def get_sessions(self, api_key):
        """Fetches all sessions."""
        url = f"{self.BASE_URL}/sessions"
        try:
            response = requests.get(url, headers=self._get_headers(api_key), timeout=10)
            response.raise_for_status()
            return response.json().get("sessions", [])
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def get_sources(self, api_key):
        """Fetches available repositories."""
        url = f"{self.BASE_URL}/sources"
        try:
            response = requests.get(url, headers=self._get_headers(api_key), timeout=10)
            response.raise_for_status()
            return response.json().get("sources", [])
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def approve_plan(self, api_key, session_id):
        """Approves a plan for the session."""
        url = f"{self.BASE_URL}/sessions/{session_id}:approvePlan"
        try:
            response = requests.post(
                url, headers=self._get_headers(api_key), json={}, timeout=10
            )
            response.raise_for_status()
            return {"status": "success", "message": "Plan approved."}
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def send_message(self, api_key, session_id, message):
        """Sends a message to the session."""
        url = f"{self.BASE_URL}/sessions/{session_id}:sendMessage"
        payload = {"prompt": message}
        try:
            response = requests.post(
                url, headers=self._get_headers(api_key), json=payload, timeout=30
            )
            response.raise_for_status()
            return {"status": "success", "message": "Message sent."}
        except requests.exceptions.RequestException as e:
            self._handle_error(e)

    def _handle_error(self, error):
        msg = f"Jules API Error: {str(error)}"
        if hasattr(error, "response") and error.response is not None:
            try:
                error_data = error.response.json()
                msg += f" - {error_data}"
            except:
                msg += f" - {error.response.text}"

        frappe.log_error(msg, "Jules Service Error")
        frappe.throw(msg)
