# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
import time
from rcore.roadmap.utils import check_queue_status, get_prompts, construct_contextual_prompt

# --- Main Scheduled Tasks ---

@frappe.whitelist()
def trigger_daily_generation():
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
        roadmaps = frappe.get_all("Roadmap", 
            filters={
                "source_repository": ["is", "set"],
                "jules_api_key": ["is", "set"],
                "status": "Active"
            }, 
            fields=["name", "source_repository", "jules_api_key"]
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
                frappe.log_error(f"Skipping Idea Gen for {roadmap_name}: Jules Queue is Full/Busy.", "Jules Concurrency")
                continue

            # Don't spam: If we already have AI generated ideas in 'Ideas' column, skip
            if frappe.db.exists("Roadmap Feature", {"parent": roadmap_name, "status": "Ideas", "is_ai_generated": 1}):
                continue

            # Fetch existing context to prevent duplicates
            existing_features = frappe.get_all("Roadmap Feature", 
                filters={"parent": roadmap_name}, 
                fields=["feature", "status", "type", "explanation"]
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
                        # Building Mode (Future proofing) - allows code generation
                        system_instruction = ""

                    full_prompt = f"{prompt.prompt}\n{context_str}\n{system_instruction}"
                    # Delegate to Brain
                    session = frappe.call("brain.api.start_jules_session", 
                        prompt=full_prompt, 
                        source_repo=roadmap.get("source_repository"), 
                        api_key=api_key,
                        automation_mode="AUTOMATION_MODE_UNSPECIFIED"
                    )
                    
                    if session and session.get("name"): # name is session_id
                        frappe.get_doc({
                            "doctype": "AI Idea Session",
                            "roadmap": roadmap_name,
                            "session_id": session.get("name"),
                            "status": "Pending",
                            "prompt_title": prompt.title
                        }).insert(ignore_permissions=True)
                        frappe.db.commit()
                except Exception as e:
                    frappe.log_error(f"Failed to start Brain session for '{roadmap_name}': {e}", "Jules Idea Generation")

    except Exception as e:
        frappe.log_error(f"AI idea task failed: {e}", "Jules Idea Generation")

def process_pending_ai_sessions():
    """
    (Hourly/Frequent Task)
    POLLS pending AI Idea Sessions for results via Brain.
    """
    try:
        pending_sessions = frappe.get_all("AI Idea Session", filters={"status": "Pending"})

        for session_doc in pending_sessions:
            session = frappe.get_doc("AI Idea Session", session_doc.name)
            # Fetch Key from Parent Roadmap
            try:
                roadmap = frappe.get_doc("Roadmap", session.roadmap)
                api_key = roadmap.get_password("jules_api_key")
                
                if not api_key:
                     # FALLBACK
                     settings = frappe.get_single("Roadmap Settings")
                     api_key = settings.get_password("jules_api_key")

                if not api_key:
                    session.status = "Error"
                    session.add_comment("Comment", "Missing API Key (Roadmap & Global)")
                    session.save(ignore_permissions=True)
                    continue

                # TIMEOUT CHECK (30 Minutes)
                # If session is pending for > 30 mins, kill it.
                creation_time = frappe.utils.get_datetime(session.creation)
                if frappe.utils.time_diff_in_seconds(frappe.utils.now_datetime(), creation_time) > 1800:
                     session.status = "Error"
                     session.add_comment("Comment", "Session Timed Out (>30 mins)")
                     try:
                         frappe.call("brain.api.delete_jules_session", session_id=session.session_id, api_key=api_key)
                     except:
                         pass
                     session.save(ignore_permissions=True)
                     frappe.db.commit()
                     continue

                # Delegate to Brain
                activities = frappe.call("brain.api.get_jules_activities", 
                    session_id=session.session_id, 
                    api_key=api_key
                )
                
                if activities:
                    latest_response = _get_latest_agent_message(activities)
                    if latest_response:
                        ideas = _parse_ideas_from_response(latest_response)
                        if ideas:
                            original_prompt_title = session.prompt_title or ""
                            for idea in ideas:
                                idea['type'] = "Bug" if "bug" in original_prompt_title.lower() else "Feature"
                            
                            _save_ideas_to_roadmap(session.roadmap, ideas)

                        session.status = "Completed"
                        
                        # Cleanup session in Cloud
                        frappe.call("brain.api.delete_jules_session", session_id=session.session_id, api_key=api_key)
                        
                        session.save(ignore_permissions=True)
                        frappe.db.commit()
            except Exception as e:
                session.status = "Error"
                session.save(ignore_permissions=True)
                frappe.db.commit()
                frappe.log_error(f"Failed to process session {session.session_id}: {e}", "Jules Idea Processing")
    except Exception as e: 
        frappe.log_error(f"Pending Sessions task failed: {e}", "Jules Pending Processor")


def process_building_queue():
    """
    (Featured Task)
    Process items in 'Idea Passed' and 'Bugs' by assigning them to Jules (Building Mode).
    """
    try:
        # Find features waiting for building
        features = frappe.get_all("Roadmap Feature", 
            filters={
                "status": ["in", ["Idea Passed", "Bugs"]],
                "jules_session_id": ["is", "not set"], # Don't double process
            },
            fields=["name", "status", "feature", "explanation", "type", "parent"]
        )
        
        # Group by Roadmap to optimize API checks
        features_by_roadmap = {}
        for f in features:
            if f.parent not in features_by_roadmap:
                 features_by_roadmap[f.parent] = []
            features_by_roadmap[f.parent].append(f)

        for roadmap_name, roadmap_features in features_by_roadmap.items():
            try:
                roadmap = frappe.get_doc("Roadmap", roadmap_name)
                # Only process if Roadmap is configured
                if not roadmap.source_repository or not roadmap.jules_api_key:
                    continue
                
                api_key = roadmap.get_password("jules_api_key")
                if not api_key:
                    # FALLBACK
                    settings = frappe.get_single("Roadmap Settings")
                    api_key = settings.get_password("jules_api_key")

                if not api_key: continue

                # CHECK CONCURRENCY (Queue Status)
                if not check_queue_status(api_key):
                    frappe.log_error(f"Skipping Building Queue for {roadmap_name}: Jules Queue is Full/Busy.", "Jules Concurrency")
                    continue

                for f in roadmap_features:
                    # Construct Building Prompt using roadmap context
                    full_prompt = construct_contextual_prompt(roadmap, f, "Building")

                    # Start Jules Session
                    session = frappe.call("brain.api.start_jules_session", 
                        prompt=full_prompt, 
                        source_repo=roadmap.source_repository, 
                        api_key=api_key,
                        automation_mode="AUTO_CREATE_PR",
                        require_approval=roadmap.require_jules_approval,
                        title=f.feature
                    )

                    if session and session.get("name"):
                        # Update Feature Status
                        doc = frappe.get_doc("Roadmap Feature", f.name)
                        doc.jules_session_id = session.get("name") # session_id
                        doc.status = "Doing" # Move to Doing
                        doc.save(ignore_permissions=True)
                        frappe.db.commit()
            
            except Exception as e:
                frappe.log_error(f"Building Queue failed for roadmap {roadmap_name}: {e}", "Jules Building Queue")

    except Exception as e:
        frappe.log_error(f"Building Queue task failed: {e}", "Jules Building Queue")

def jules_task_monitor():
    """
    (Hourly Task)
    Monitors Roadmap Features assigned to Jules (Push Flow).
    Checks for PRs and Moves to Done.
    """
    features = frappe.get_all("Roadmap Feature", 
        filters={
            "jules_session_id": ["is", "set"],
            "status": "Doing" # Only check active ones
        }, 
        fields=["name", "jules_session_id", "status", "parent"]
    )

    for f in features:
        try:
            roadmap = frappe.get_doc("Roadmap", f.parent)
            api_key = roadmap.get_password("jules_api_key")
            
            if not api_key:
                # FALLBACK
                settings = frappe.get_single("Roadmap Settings")
                api_key = settings.get_password("jules_api_key")

            if not api_key: continue

            # Check Status via Brain
            session_data = frappe.call("brain.api.get_jules_status", 
                session_id=f.jules_session_id, 
                api_key=api_key
            )
            
            state = session_data.get("state")
            
            # Sync detailed State
            if state == "AWAITING_USER_FEEDBACK":
                 doc = frappe.get_doc("Roadmap Feature", f.name)
                 if doc.ai_status != "Pending": # Avoid spamming
                     doc.add_comment("Comment", "⚠️ Jules is waiting for your feedback. Please open the session to reply.")
                 doc.save(ignore_permissions=True)
                 frappe.db.commit()
                 continue
            
            if state == "AWAITING_PLAN_APPROVAL":
                 doc = frappe.get_doc("Roadmap Feature", f.name)
                 if doc.ai_status != "Pending":
                     doc.add_comment("Comment", "⚠️ Jules Plan is ready for review. Please open the session to approve.")
                 doc.save(ignore_permissions=True)
                 frappe.db.commit()
                 continue

            # Handle Failure
            if state in ["FAILED", "CANCELLED", "ERROR"]:
                 doc = frappe.get_doc("Roadmap Feature", f.name)
                 doc.status = "Error" # Alert user
                 doc.ai_status = "Error"
                 doc.add_comment("Comment", f"Jules Session Failed/Cancelled. State: {state}. Please open session to investigate.")
                 doc.save(ignore_permissions=True)
                 frappe.db.commit()
                 continue

            outputs = session_data.get("outputs", [])
            pr_link = None
            for out in outputs:
                if out.get("pullRequest"):
                     pr_link = out.get("pullRequest").get("url") # Standardize on 'url'
                     break
            
            if pr_link:
                doc = frappe.get_doc("Roadmap Feature", f.name)
                doc.add_comment("Comment", f"Jules completed the task. PR: {pr_link}")
                doc.status = "Done" # Move to Done/Developed
                doc.pull_request_url = pr_link
                # doc.jules_session_id = None # Keep session alive for human verification
                doc.save(ignore_permissions=True)
                
                # Do NOT delete session yet. Human must verify.
                frappe.db.commit()
                
        except Exception as e:
            frappe.log_error(f"Monitor failed for Feature {f.name}: {e}", "Jules Monitor")

def cleanup_archived_sessions():
    """
    (Hourly Task)
    Cleans up Jules sessions for items moved to 'Archived'.
    Saves activity log to the document before deletion.
    """
    try:
        # Find features in 'Archived' that still have a session ID
        features = frappe.get_all("Roadmap Feature", 
            filters={
                "status": "Archived",
                "jules_session_id": ["is", "set"]
            },
            fields=["name", "jules_session_id", "parent"]
        )

        for f in features:
            try:
                roadmap = frappe.get_doc("Roadmap", f.parent)
                api_key = roadmap.get_password("jules_api_key")
                
                if not api_key:
                    # FALLBACK
                    settings = frappe.get_single("Roadmap Settings")
                    api_key = settings.get_password("jules_api_key")

                if not api_key: 
                    # Can't delete without key, but clear ID to stop retrying? 
                    # unsafe. skip.
                    continue

                # 1. Delete Session (Directly)
                frappe.call("brain.api.delete_jules_session", 
                    session_id=f.jules_session_id, 
                    api_key=api_key
                )
                
                # 2. Finalize Doc
                doc = frappe.get_doc("Roadmap Feature", f.name)
                doc.jules_session_id = None # Clear it
                doc.add_comment("Comment", "Auto-Cleanup: Jules Session archived and deleted.")
                doc.save(ignore_permissions=True)
                frappe.db.commit()
                
            except Exception as e:
                frappe.log_error(f"Cleanup failed for feature {f.name}: {e}", "Jules Cleanup")

    except Exception as e:
        frappe.log_error(f"Cleanup task failed: {e}", "Jules Cleanup")


@frappe.whitelist()
def discover_roadmap_context(roadmap_name):
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
        session = frappe.call("brain.api.start_jules_session", 
            prompt=prompt, 
            source_repo=roadmap.source_repository, 
            api_key=api_key,
            automation_mode="AUTOMATION_MODE_UNSPECIFIED"
        )
        
        session_id = session.get("name")
        if not session_id:
            frappe.throw("Failed to start Jules Session.")

        # 2. Poll for Result (Max 30 seconds - usually fast for pure text)
        for _ in range(10):
            time.sleep(3) 
            activities = frappe.call("brain.api.get_jules_activities", 
                session_id=session_id, 
                api_key=api_key
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
                                 # Clear existing? Or Append? Let's Append unique.
                                 existing_tags = [c.value for c in roadmap.classifications]
                                 for c in data["classifications"]:
                                     if c.get("value") not in existing_tags:
                                         roadmap.append("classifications", {
                                             "category": c.get("category", "Tech"),
                                             "value": c.get("value")
                                         })
                             roadmap.save(ignore_permissions=True)
                             
                             # Handle Initial Ideas
                             if "initial_ideas" in data:
                                 _save_ideas_to_roadmap(roadmap_name, data["initial_ideas"])

                             # Success! Cleanup and Return.
                             frappe.call("brain.api.delete_jules_session", session_id=session_id, api_key=api_key)
                             return data
                 except:
                     continue
        
        # Timeout
        frappe.call("brain.api.delete_jules_session", session_id=session_id, api_key=api_key)
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
    return next((act.get("agentActivity", {}).get("message") for act in reversed(activities) if act.get("agentActivity")), None)

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