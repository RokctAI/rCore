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

from typing import Any, Optional
# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt
# tenant context check.

import frappe
import json
import time
from rcore.agent.roadmap.utils import (
    check_queue_status,
    get_prompts,
)

# --- Main Scheduled Tasks ---


# Deliberately NOT @frappe.whitelist(): leads to populate_roadmap_with_ai_ideas
# -> start_jules_session on the platform's API key. Kept for `bench execute`;
# no longer reachable over HTTP.
def trigger_daily_generation() -> Any:
    """Manually triggers the daily AI idea generation."""
    populate_roadmap_with_ai_ideas()


def populate_roadmap_with_ai_ideas():
    """
    (Daily Task)
    Initiates AI idea generation sessions via Brain Service.
    Checks each Roadmap for a repo + key, and if no 'Ideas' are pending, generates new ones.
    """
    try:
        # Fetch Roadmaps with Source Repo AND API Key configured
        roadmaps = frappe.get_all(
            "Roadmap",
            filters={
                "source_repository": ["is", "set"],
                "jules_api_key": ["is", "set"],
                "status": "Active",
            },
            fields=["name", "source_repository", "jules_api_key"],
        )
        prompts = get_prompts()

        if not prompts:
            # Only log if debugging, otherwise it fills logs daily
            return

        for roadmap in roadmaps:
            roadmap_name = roadmap.get("name")
            api_key = roadmap.get_password("jules_api_key")

            if not api_key:
                # FALLBACK to GLOBAL
                settings = frappe.get_single("Roadmap Settings")
                api_key = settings.get_password("jules_api_key")

            if not api_key:
                continue

            # CHECK CONCURRENCY (Queue Status)
            if not check_queue_status(api_key):
                frappe.log_error(
                    f"Skipping Idea Gen for {roadmap_name}: Jules Queue is Full/Busy.",
                    "Jules Concurrency",
                )
                continue

            # Don't spam: If we already have AI generated ideas in 'Ideas'
            # column, skip
            if frappe.db.exists(
                "Roadmap Feature",
                {"parent": roadmap_name, "status": "Ideas", "is_ai_generated": 1},
            ):
                continue

            # Fetch existing context to prevent duplicates
            existing_features = frappe.get_all(
                "Roadmap Feature",
                filters={"parent": roadmap_name},
                fields=["feature", "status", "type", "explanation"],
            )

            for prompt in prompts:
                # Filter Context based on Prompt Type
                is_bug_prompt = prompt.get("type") == "Bug"
                context_str = "\n\nCONTEXT - EXISTING ITEMS (DO NOT SUGGEST THESE):\n"
                has_context = False

                for f in existing_features:
                    f_type = f.get("type", "Feature")
                    msg = f"- [{f.status}] {f.feature}"
                    if f.get("explanation"):
                        msg += f" ({f.explanation})"
                    msg += "\n"

                    # If generating Bugs, show existing Bugs to avoid dupes
                    if is_bug_prompt and f_type == "Bug":
                        context_str += msg
                        has_context = True
                    # If generating Ideas, show existing Features (hide Bugs)
                    elif not is_bug_prompt and f_type != "Bug":
                        context_str += msg
                        has_context = True

                if not has_context:
                    context_str = ""

                try:
                    # Append strict instructions based on Mode
                    # Default to Planning if not set
                    prompt_mode = prompt.get("mode", "Planning")

                    if prompt_mode == "Planning":
                        system_instruction = "\n\nIMPORTANT: This session is for brainstorming/ideation only. Do NOT write code. Do NOT create a Pull Request. Provide the output in JSON format with 'title', 'explanation', and 'type' fields."
                    else:
                        # Building Mode (Future proofing) - allows code
                        # generation
                        system_instruction = ""

                    full_prompt = (
                        f"{prompt.prompt}\n{context_str}\n{system_instruction}"
                    )
                    # Delegate to Brain
                    session = frappe.call(
                        "rcore.api.start_jules_session",
                        prompt=full_prompt,
                        source_repo=roadmap.get("source_repository"),
                        api_key=api_key,
                        automation_mode="AUTOMATION_MODE_UNSPECIFIED",
                    )

                    if session and session.get("name"):  # name is session_id
                        frappe.get_doc(
                            {
                                "doctype": "AI Idea Session",
                                "roadmap": roadmap_name,
                                "session_id": session.get("name"),
                                "status": "Pending",
                                "prompt_title": prompt.title,
                            }
                        ).insert(ignore_permissions=True)
                        frappe.db.commit()
                except Exception as e:
                    frappe.log_error(
                        f"Failed to start Brain session for '{roadmap_name}': {e}",
                        "Jules Idea Generation",
                    )

    except Exception as e:
        frappe.log_error(f"AI idea task failed: {e}", "Jules Idea Generation")


def enrich_roadmap_from_repo(roadmap_name):
    """
    (Background job, enqueued from Roadmap.after_save)
    Fills a Roadmap's description and classifications from what GitHub already
    knows about its repository.

    This replaces the Jules-powered `discover_roadmap_context` enrichment that
    used to run on save: same trigger, same fields, no AI service and no key.
    Frappe takes the data from the repo it was handed rather than inferring it.

    Only empty fields are filled, so a human's edit is never overwritten, and
    the document is saved only when something actually changed — an unchanged
    save would re-fire `after_save` and re-enqueue this job.
    """
    from rcore.agent.roadmap.api import fetch_repo_context

    try:
        roadmap = frappe.get_doc("Roadmap", roadmap_name)

        # Repo-less roadmaps stay inert: fetch_repo_context returns None for an
        # empty or unparseable URL, so nothing is requested and nothing logged.
        context = fetch_repo_context(roadmap.source_repository)
        if not context:
            return

        changed = False

        if not roadmap.description and context.get("description"):
            roadmap.description = context["description"]
            changed = True

        if not roadmap.classifications:
            for classification in context.get("classifications") or []:
                roadmap.append("classifications", classification)
                changed = True

        if changed:
            roadmap.save(ignore_permissions=True)
            frappe.db.commit()

    except Exception as e:
        # Never surfaced to whoever saved the Roadmap: the document is already
        # committed by the time this job runs.
        frappe.log_error(
            f"Roadmap enrichment failed for {roadmap_name}: {e}",
            "Roadmap Repo Enrichment",
        )


def dispatch_build_queue_to_github():
    """
    (Scheduled Task)
    Dispatches features sitting in 'Idea Passed' and 'Bugs' by opening a GitHub
    issue on the roadmap's source repository.

    This replaces the removed `process_building_queue`, which dispatched the
    same queue to Jules. Whoever works the repository — a human or an agent —
    picks the issue up; the PR-merged workflow calls
    `roadmap.api.update_task_status_from_pr` to move the feature to Done.
    """
    from rcore.agent.roadmap.api import assign_to_github, match_repo

    try:
        # Find features waiting for building that have not been dispatched yet.
        features = frappe.get_all(
            "Roadmap Feature",
            filters={
                "status": ["in", ["Idea Passed", "Bugs"]],
                # Don't double process
                "issue_number": ["is", "not set"],
            },
            fields=["name", "parent"],
        )

        for f in features:
            try:
                roadmap = frappe.get_doc("Roadmap", f.parent)
                # A Roadmap with no usable repository is an inert board.
                # Skip it silently — no dispatch, and no error log every 15
                # minutes for boards that are never meant to dispatch. This
                # covers both an empty source_repository and one that does not
                # parse as a GitHub URL.
                if not match_repo(roadmap.source_repository):
                    continue

                assign_to_github(f.name)
                frappe.db.commit()
            except Exception as e:
                frappe.db.rollback()
                frappe.log_error(
                    f"GitHub dispatch failed for Feature {f.name}: {e}",
                    "Roadmap GitHub Dispatch",
                )

    except Exception as e:
        frappe.log_error(
            f"Build queue dispatch task failed: {e}", "Roadmap GitHub Dispatch"
        )


# Deliberately NOT @frappe.whitelist(): calls start_jules_session directly on
# the platform's API key. Its only trigger was Roadmap.after_save, which no
# longer enqueues it. Kept for `bench execute`; no longer reachable over HTTP.
def discover_roadmap_context(roadmap_name: Any) -> Any:
    """
    Auto-Discovery Task (On Demand)
    1. Starts a Planning Session with Jules to analyze the codebase.
    2. Asks for a Description and Classifications (Stack/Platform/Dependency).
    3. Polls (briefly) for handling.
    4. Returns the result and closes the session.
    """
    roadmap = frappe.get_doc("Roadmap", roadmap_name)
    api_key = roadmap.get_password("jules_api_key")

    if not api_key:
        # Fallback
        settings = frappe.get_single("Roadmap Settings")
        api_key = settings.get_password("jules_api_key")

    if not api_key:
        frappe.throw("Jules API Key is missing.")

    if not roadmap.source_repository:
        frappe.throw("Source Repository is missing.")

    # 1. Start Session
    prompt = (
        "Analyze the repository code structure and dependencies.\n"
        "Return a JSON object with the following fields:\n"
        "- description: A concise 1-2 sentence summary of what this project does.\n"
        "- classifications: A FLAT list of objects. Each object MUST have 'category' and 'value'. Do NOT nest. Limit to top 5 MAJOR technologies.\n"
        "- initial_ideas: A list of objects, each with 'title' (string), 'explanation' (string), and 'type' (string, e.g. 'Feature' or 'Bug'). Suggest 3-5 initial features based on the codebase.\n"
        "Do NOT write code. Provide ONLY the JSON."
    )

    try:
        session = frappe.call(
            "rcore.api.start_jules_session",
            prompt=prompt,
            source_repo=roadmap.source_repository,
            api_key=api_key,
            automation_mode="AUTOMATION_MODE_UNSPECIFIED",
        )

        session_id = session.get("name")
        if not session_id:
            frappe.throw("Failed to start Jules Session.")

        # 2. Poll for Result (Max 30 seconds - usually fast for pure text)
        for _ in range(10):
            time.sleep(3)
            activities = frappe.call(
                "rcore.api.get_jules_activities", session_id=session_id, api_key=api_key
            )

            latest_msg = _get_latest_agent_message(activities)
            if latest_msg:
                # Try to parse
                try:
                    # Heuristic: Find JSON blob if mixed with text
                    if "{" in latest_msg and "}" in latest_msg:
                        start = latest_msg.find("{")
                        end = latest_msg.rfind("}") + 1
                        json_str = latest_msg[start:end]
                        data = json.loads(json_str)

                        if "description" in data or "classifications" in data:
                            # Update Roadmap Context
                            if "description" in data and not roadmap.description:
                                roadmap.description = data["description"]

                            if "classifications" in data:
                                # Clear existing? Or Append? Let's Append
                                # unique.
                                existing_tags = [
                                    c.value for c in roadmap.classifications
                                ]
                                for c in data["classifications"]:
                                    if c.get("value") not in existing_tags:
                                        roadmap.append(
                                            "classifications",
                                            {
                                                "category": c.get("category", "Tech"),
                                                "value": c.get("value"),
                                            },
                                        )
                            roadmap.save(ignore_permissions=True)

                            # Handle Initial Ideas
                            if "initial_ideas" in data:
                                _save_ideas_to_roadmap(
                                    roadmap_name, data["initial_ideas"]
                                )

                            # Success! Cleanup and Return.
                            frappe.call(
                                "rcore.api.delete_jules_session",
                                session_id=session_id,
                                api_key=api_key,
                            )
                            return data
                except BaseException:
                    continue

        # Timeout
        frappe.call(
            "rcore.api.delete_jules_session", session_id=session_id, api_key=api_key
        )
        frappe.throw("Jules took too long to analyze the repository.")

    except Exception as e:
        frappe.log_error(f"Discovery Failed: {e}", "Jules Discovery")
        frappe.throw(f"Discovery Failed: {str(e)}")


# --- Helpers ---


def _save_ideas_to_roadmap(roadmap_name, ideas):
    roadmap_doc = frappe.get_doc("Roadmap", roadmap_name)
    for idea in ideas:
        feature_doc = frappe.new_doc("Roadmap Feature")
        feature_doc.feature = idea.get("title")
        feature_doc.explanation = idea.get("explanation")
        feature_doc.status = "Ideas"
        feature_doc.is_ai_generated = 1
        feature_doc.type = idea.get("type", "Feature")

        # Parse Tags from Brain Response
        tags = idea.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                feature_doc.append("tags", {"tag": str(tag)})

        roadmap_doc.append("features", feature_doc)
    roadmap_doc.save(ignore_permissions=True)


def _get_latest_agent_message(activities):
    return next(
        (
            act.get("agentActivity", {}).get("message")
            for act in reversed(activities)
            if act.get("agentActivity")
        ),
        None,
    )


def _parse_ideas_from_response(response_text):
    try:
        # Robust Parsing: Find JSON blob if mixed with text
        json_str = response_text
        if "{" in response_text and "}" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]

        return json.loads(json_str).get("ideas", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def _get_api_key():
    """
    Helper to get the Global Jules API Key from Settings.
    """
    settings = frappe.get_single("Roadmap Settings")
    return settings.get_password("jules_api_key")


def _create_jules_session(api_key, source_repo, title, prompt):
    """
    Helper to start a Jules Session (typically for one-off tasks like workflow setup).
    """
    try:
        session = frappe.call(
            "rcore.api.start_jules_session",
            prompt=prompt,
            source_repo=source_repo,
            api_key=api_key,
            automation_mode="AUTO_CREATE_PR",
            title=title,
        )
        if session:
            return session.get("name")
    except Exception as e:
        frappe.log_error(f"Failed to create Jules session: {e}", "Jules API Helper")
    return None
