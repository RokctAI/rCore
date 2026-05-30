import json
# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient


@frappe.whitelist()
def query(doctype, name):
    """
    A secure API endpoint for an AI model to query the Brain's memory.
    Ensures security is enforced by checking for read permission.
    """
    if not frappe.has_permission(doctype, "read", doc=name):
        frappe.throw(
            f"You do not have permission to access the memory of {doctype} {name}",
            frappe.PermissionError,
        )

    try:
        engram_name = f"{doctype}-{name}"
        engram_doc = frappe.get_doc("Engram", engram_name)
        response_data = engram_doc.as_dict()
        response_data["brain_version"] = brain_version
        return response_data
    except frappe.DoesNotExistError:
        frappe.throw(f"No Engram found for {doctype} {name}", frappe.NotFound)
    except Exception as e:
        frappe.throw(f"An error occurred while querying the Brain: {e}")


@frappe.whitelist()
def record_event(message, reference_doctype, reference_name, is_ai_action=False):
    """
    A secure API endpoint to record a custom event in the Brain's memory.
    """
    try:

        class MockDoc:
            def __init__(self):
                self.doctype = reference_doctype
                self.name = reference_name
                self.modified = frappe.utils.now()
                self.owner = frappe.session.user
                self.is_ai_action = is_ai_action
                self._doc_before_save = None

            def has_field(self, fieldname):
                return False

            def get(self, key, default=None):
                return getattr(self, key, default)

            @property
            def meta(self):
                class MockMeta:
                    def get_label(self, f):
                        return f

                return MockMeta()

        mock_doc = MockDoc()

        from rcore.utils.engram_builder import process_event_in_realtime

        process_event_in_realtime(mock_doc, message)

        return {"status": "success", "message": "Event recorded."}
    except Exception as e:
        frappe.log_error(f"Brain: Failed to record event: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred while recording the event: {e}")


@frappe.whitelist()
def record_chat_summary(
    chat_transcript, reference_doctype=None, reference_name=None, modules=None
):
    """
    Accepts a raw chat transcript, enqueues a background job to summarize it.
    """
    if (
        not chat_transcript
        or not isinstance(chat_transcript, str)
        or not chat_transcript.strip()
    ):
        frappe.throw(
            "`chat_transcript` must be a non-empty string.", title="Invalid Input"
        )

    if not reference_doctype or not reference_name:
        reference_doctype = "User"
        reference_name = frappe.session.user

    frappe.enqueue(
        "rcore.api.rcore.generate_summary_and_update_engram",
        queue="short",
        timeout=300,
        job_name=f"summarize-chat-{reference_doctype}-{reference_name}",
        chat_transcript=chat_transcript,
        reference_doctype=reference_doctype,
        reference_name=reference_name,
        user=frappe.session.user,
        modules=modules,
    )

    return {"status": "accepted", "message": "Chat summary job has been queued."}


def generate_summary_and_update_engram(
    chat_transcript, reference_doctype, reference_name, user, modules=None
):
    """
    Background job that generates a summary and updates the Engram document.
    """
    from rcore.services.llm_service import ask_brain, DEFAULT_MODEL
    import json

    try:
        prompt = f"Please provide a concise summary of the following chat conversation:\n\n{chat_transcript}"
        response = ask_brain(prompt)
        summary_text = response.get("text", "").strip()

        if not summary_text:
            raise ValueError("LLM returned an empty summary.")

        engram_name = f"{reference_doctype}-{reference_name}"
        try:
            engram_doc = frappe.get_doc("Engram", engram_name)
        except frappe.DoesNotExistError:
            engram_doc = frappe.new_doc("Engram")
            engram_doc.reference_doctype = reference_doctype
            engram_doc.reference_name = reference_name
            engram_doc.name = engram_name
            from rcore.utils.engram_builder import get_document_title

            engram_doc.reference_title = get_document_title(
                reference_doctype, reference_name
            )

        if modules:
            try:
                modules_list = (
                    json.loads(modules) if isinstance(modules, str) else modules
                )
                if isinstance(modules_list, list):
                    engram_doc.module = ", ".join(sorted(list(set(modules_list))))
            except (json.JSONDecodeError, TypeError):
                engram_doc.module = "Chat"

        if not engram_doc.module:
            module = frappe.db.get_value("DocType", reference_doctype, "module")
            engram_doc.module = module or "Chat"

        engram_doc.source = "Chat Summary"
        user_full_name = frappe.get_fullname(user)
        new_summary_line = f"Chat Summary by {user_full_name} on {frappe.utils.getdate(frappe.utils.now())}:\n{summary_text}"
        engram_doc.summary = (
            (engram_doc.summary + "\n\n---\n\n" + new_summary_line)
            if engram_doc.summary
            else new_summary_line
        )

        involved = set(
            engram_doc.get("involved_users", "").split(", ")
            if engram_doc.get("involved_users")
            else []
        )
        involved.add(user_full_name)
        engram_doc.involved_users = ", ".join(sorted(list(filter(None, involved))))

        engram_doc.last_activity_date = frappe.utils.now()
        engram_doc.save(ignore_permissions=True)
        frappe.db.commit()

        from rcore.services.llm_service import embed_text

        if engram_doc.summary:
            context_text = f"{reference_doctype} {reference_name} ({engram_doc.reference_title}):\n{engram_doc.summary}"
            vector = embed_text(context_text)

            if vector:
                frappe.db.sql(
                    """
                    UPDATE tabEngram 
                    SET embedding = %s 
                    WHERE name = %s
                """,
                    (str(vector), engram_doc.name),
                )
                frappe.db.commit()

        frappe.db.commit()

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            f"Brain: Failed to generate or record chat summary for {reference_doctype} {reference_name}: {e}",
            frappe.get_traceback(),
        )


@frappe.whitelist()
def get_event_interval(reference_doctype, reference_name, start_event, end_event):
    """
    Calculates the time interval between two events in a document's history.
    """
    import re
    from frappe.utils import get_datetime

    try:
        engram_doc = frappe.get_doc("Engram", f"{reference_doctype}-{reference_name}")
        summary = engram_doc.summary

        start_date = None
        end_date = None

        start_pattern = re.compile(
            rf"{re.escape(start_event)} by .* on (\d{{4}}-\d{{2}}-\d{{2}})"
        )
        end_pattern = re.compile(
            rf"{re.escape(end_event)} by .* on (\d{{4}}-\d{{2}}-\d{{2}})"
        )

        for line in summary.split("\n"):
            if not start_date:
                start_match = start_pattern.search(line)
                if start_match:
                    start_date = get_datetime(start_match.group(1))

            if not end_date:
                end_match = end_pattern.search(line)
                if end_match:
                    end_date = get_datetime(end_match.group(1))

        if start_date and end_date:
            if end_date < start_date:
                return {"error": "End event occurred before start event."}

            interval = end_date - start_date
            return {
                "interval_days": interval.days,
                "interval_seconds": interval.total_seconds(),
            }

        missing = []
        if not start_date:
            missing.append(start_event)
        if not end_date:
            missing.append(end_event)

        return {
            "error": f"Could not find one or more events in the document's history: {', '.join(missing)}"
        }

    except frappe.DoesNotExistError:
        return {"error": f"No Engram found for {reference_doctype} {reference_name}"}
    except Exception as e:
        frappe.log_error(
            f"Brain: Failed to get event interval: {e}", frappe.get_traceback()
        )
        frappe.throw(f"An error occurred while calculating the event interval: {e}")


@frappe.whitelist()
def accept_stimulus(stimulus_name, template_name="Default"):
    """
    Claims a stimulus for the current user and triggers associated workflows.
    """
    stimulus = frappe.get_doc("Stimulus", stimulus_name)
    if stimulus.claimed_by:
        frappe.throw(
            f"This stimulus has already been claimed by {stimulus.claimed_by}.",
            title="Already Claimed",
        )

    try:
        stimulus.claimed_by = frappe.session.user
        stimulus.status = "Claimed"
        stimulus.save(ignore_permissions=True)

        record_event(
            message=f"Stimulus {stimulus_name} claimed by {frappe.session.user}.",
            reference_doctype="Stimulus",
            reference_name=stimulus_name,
            is_ai_action=True,
        )

        tasks_to_create = []
        if stimulus.custom_workflow_json:
            try:
                raw_data = json.loads(stimulus.custom_workflow_json)
                tasks_to_create = raw_data.get("tasks", [])
            except:
                pass

        if not tasks_to_create:
            try:
                from rcore.utils.common import call_control

                opportunities = call_control(
                    "get_public_opportunities",
                    {
                        "opportunity_type": "tenders",
                        "filters": json.dumps({"slug": stimulus_name}),
                    },
                )
                if opportunities:
                    tasks_to_create = opportunities[0].get("tasks", [])
            except:
                pass

        if frappe.db.exists("DocType", "Task"):
            for task_template in tasks_to_create:
                subject = (
                    task_template.get("subject")
                    if isinstance(task_template, dict)
                    else task_template
                )
                offset = (
                    task_template.get("due_date_offset_days", 7)
                    if isinstance(task_template, dict)
                    else 7
                )

                frappe.get_doc(
                    {
                        "doctype": "Task",
                        "subject": subject,
                        "exp_start_date": frappe.utils.nowdate(),
                        "exp_end_date": frappe.utils.add_to_date(
                            frappe.utils.nowdate(), days=offset
                        ),
                        "_assign": frappe.session.user,
                    }
                ).insert(ignore_permissions=True)

        frappe.db.commit()
        return {
            "status": "success",
            "message": f"Stimulus {stimulus_name} claimed and tasks created.",
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(), f"Failed to claim stimulus {stimulus_name}"
        )
        frappe.throw(f"An error occurred while claiming the stimulus: {e}")


@frappe.whitelist()
def reject_stimulus(stimulus_name):
    """
    Dismisses a stimulus for the current user.
    """
    stimulus = frappe.get_doc("Stimulus", stimulus_name)
    user = frappe.session.user

    if any(d.user == user for d in stimulus.get("dismissed_by", [])):
        return {"status": "success", "message": "Stimulus already dismissed."}

    try:
        stimulus.append("dismissed_by", {"user": user})
        stimulus.save(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success", "message": f"Stimulus {stimulus_name} dismissed."}
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(), f"Failed to dismiss stimulus {stimulus_name}"
        )
        frappe.throw(f"An error occurred while dismissing the stimulus: {e}")


@frappe.whitelist()
def accept_neurotrophin(neurotrophin_name, template_name="Default"):
    """
    Accepts a neurotrophin (funding opportunity) and triggers associated workflows.
    """
    neurotrophin = frappe.get_doc("Neurotrophin", neurotrophin_name)
    if neurotrophin.claimed_by:
        frappe.throw(
            f"This funding opportunity has already been accepted by {neurotrophin.claimed_by}.",
            title="Already Accepted",
        )

    try:
        neurotrophin.claimed_by = frappe.session.user
        neurotrophin.status = "Accepted"
        neurotrophin.save(ignore_permissions=True)

        record_event(
            message=f"Funding Opportunity {neurotrophin_name} accepted by {frappe.session.user}.",
            reference_doctype="Neurotrophin",
            reference_name=neurotrophin_name,
            is_ai_action=True,
        )

        tasks_to_create = []
        if neurotrophin.raw_json:
            try:
                raw_data = json.loads(neurotrophin.raw_json)
                tasks_to_create = raw_data.get("tasks", [])
            except:
                pass

        if not tasks_to_create:
            try:
                from rcore.utils.common import call_control

                opportunities = call_control(
                    "get_public_opportunities",
                    {
                        "opportunity_type": "grants",
                        "filters": json.dumps({"slug": neurotrophin.slug}),
                    },
                )
                if opportunities:
                    tasks_to_create = opportunities[0].get("tasks", [])
            except:
                pass

        if frappe.db.exists("DocType", "Task"):
            for task_subject in tasks_to_create:
                subject = (
                    task_subject.get("subject")
                    if isinstance(task_subject, dict)
                    else task_subject
                )
                offset = (
                    task_subject.get("due_date_offset_days", 7)
                    if isinstance(task_subject, dict)
                    else 7
                )

                frappe.get_doc(
                    {
                        "doctype": "Task",
                        "subject": subject,
                        "exp_start_date": frappe.utils.nowdate(),
                        "exp_end_date": frappe.utils.add_to_date(
                            frappe.utils.nowdate(), days=offset
                        ),
                        "_assign": frappe.session.user,
                    }
                ).insert(ignore_permissions=True)

        frappe.db.commit()
        return {
            "status": "success",
            "message": f"Funding Opportunity {neurotrophin_name} accepted and tasks created.",
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(), f"Failed to accept neurotrophin {neurotrophin_name}"
        )
        frappe.throw(f"An error occurred while accepting the funding opportunity: {e}")


@frappe.whitelist()
def search(module=None, module_group=None, involved_user=None, limit=20):
    """
    A search API for finding relevant Engrams based on metadata.
    """
    if not frappe.session.user:
        frappe.throw(
            "You must be logged in to use this feature.", frappe.PermissionError
        )

    t_engram = frappe.qb.DocType("Engram")
    query = (
        frappe.qb.from_(t_engram)
        .select(
            t_engram.name,
            t_engram.reference_doctype,
            t_engram.reference_name,
            t_engram.reference_title,
            t_engram.module,
            t_engram.summary,
            t_engram.last_activity_date,
        )
        .orderby(t_engram.last_activity_date, order=frappe.qb.desc)
    )

    if module:
        query = query.where(t_engram.module == module)

    if module_group:
        modules_in_group = frappe.get_all(
            "Module Def", filters={"parent": module_group}, pluck="name"
        )
        if modules_in_group:
            query = query.where(t_engram.module.isin(modules_in_group))
        else:
            return []

    try:
        engrams = query.limit(limit).run(as_dict=True)
        return engrams
    except Exception as e:
        frappe.log_error(f"Brain: Search API failed: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred during the search: {e}")


@frappe.whitelist()
def semantic_search(query, limit=5, involved_user=None):
    """
    Performs vector similarity search using pgvector.
    """
    if not frappe.session.user:
        frappe.throw("Authentication Required", frappe.PermissionError)

    from rcore.services.llm_service import embed_text

    vector = embed_text(query)
    if not vector:
        return []

    conditions = ""
    params = [str(vector), limit]

    if involved_user:
        conditions += " AND involved_users LIKE %s"
        params.insert(1, f"%{involved_user}%")

    sql = f"""
        SELECT 
            name, reference_doctype, reference_name, reference_title, summary, 
            (embedding <=> %s) as distance
        FROM "tabEngram"
        WHERE embedding IS NOT NULL {conditions}
        ORDER BY distance ASC
        LIMIT %s
    """

    results = frappe.db.sql(sql, tuple(params), as_dict=True)
    return results


@frappe.whitelist()
def reject_neurotrophin(neurotrophin_name):
    """
    Dismisses a neurotrophin for the current user.
    """
    neurotrophin = frappe.get_doc("Neurotrophin", neurotrophin_name)
    user = frappe.session.user

    if any(d.user == user for d in neurotrophin.get("dismissed_by", [])):
        return {
            "status": "success",
            "message": "Funding opportunity already dismissed.",
        }

    try:
        neurotrophin.append("dismissed_by", {"user": user})
        neurotrophin.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": "success",
            "message": f"Funding Opportunity {neurotrophin_name} dismissed.",
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(
            frappe.get_traceback(),
            f"Failed to dismiss neurotrophin {neurotrophin_name}",
        )
        frappe.throw(f"An error occurred while dismissing the funding opportunity: {e}")


@frappe.whitelist()
def dispatch_ai_task(task_type, data):
    """
    Dispatches tasks to the AI workers.
    """
    if isinstance(data, str):
        data = frappe.parse_json(data)

    from rcore.services.llm_service import (
        dispatch_ai_task as service_dispatch,
        BRAIN_QUEUE,
        VISION_QUEUE,
        ROUTER_QUEUE,
    )

    queue_map = {"vision": VISION_QUEUE, "rcore": BRAIN_QUEUE, "router": ROUTER_QUEUE}

    queue = queue_map.get(task_type)
    if not queue:
        frappe.throw(f"Invalid Task Type: {task_type}")

    return service_dispatch(queue, data)


@frappe.whitelist()
def get_ai_result(job_id):
    """
    Polling endpoint for AI worker results.
    """
    import redis
    import json

    r = redis.from_url(frappe.conf.get("redis_queue") or "redis://localhost:6379")

    result_raw = r.get(f"rokct:result:{job_id}")
    if result_raw:
        return json.loads(result_raw)

    return {"status": "pending"}


@frappe.whitelist()
def generate_release_notes(repo_url, commit_log, version_name="vNext"):
    """
    Generates Release Notes via LLM.
    """
    if frappe.session.user == "Guest":
        frappe.throw(
            "Authentication Required: Please provide a valid API Token.",
            frappe.PermissionError,
        )

    try:
        if "github.com/" in repo_url:
            parts = repo_url.split("github.com/")[-1].split("/")
            repo_owner = parts[0]
        else:
            repo_owner = repo_url.split("/")[0]
    except Exception:
        frappe.throw(
            f"Invalid Repo URL format: {repo_url}.", frappe.InvalidRequestError
        )

    settings = frappe.get_single("Brain Settings")
    allowed_owners = (settings.allowed_repo_owners or "").split(",")
    allowed_owners = [o.strip().lower() for o in allowed_owners if o.strip()]

    if repo_owner.lower() not in allowed_owners:
        frappe.throw(
            f"Repo Owner '{repo_owner}' is not authorized.", frappe.PermissionError
        )

    from rcore.scripts.generate_release_notes import generate_release_notes as _generate

    return _generate(commit_log, version_name)


# --- Jules AI Integration ---


@frappe.whitelist()
def start_jules_session(
    prompt,
    source_repo,
    api_key=None,
    automation_mode="AUTO_CREATE_PR",
    require_approval=False,
    title=None,
):
    client = JulesClient()
    return client.create_session(
        api_key, prompt, source_repo, automation_mode, require_approval, title
    )


@frappe.whitelist()
def get_jules_status(session_id, api_key=None):
    client = JulesClient()
    return client.get_session(api_key, session_id)


@frappe.whitelist()
def get_jules_activities(session_id, api_key=None):
    client = JulesClient()
    return client.get_activities(api_key, session_id)


@frappe.whitelist()
def get_jules_sources(api_key=None):
    client = JulesClient()
    return client.get_sources(api_key)


@frappe.whitelist()
def delete_jules_session(session_id, api_key=None):
    client = JulesClient()
    return client.delete_session(api_key, session_id)


@frappe.whitelist()
def get_jules_sessions(api_key=None):
    client = JulesClient()
    return client.get_sessions(api_key)


@frappe.whitelist()
def vote_on_plan(session_id, action, api_key=None):
    if action != "approve":
        frappe.throw("Only 'approve' action is currently supported.")
    client = JulesClient()
    return client.approve_plan(api_key, session_id)


@frappe.whitelist()
def send_jules_message(session_id, message, api_key=None):
    client = JulesClient()
    return client.send_message(api_key, session_id, message)
