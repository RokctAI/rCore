import frappe
import json

def get_prompts():
    """
    Fetches prompts from Roadmap Settings.
    """
    try:
        settings = frappe.get_single("Roadmap Settings")
        return settings.prompts or []
    except:
        return []

def check_queue_status(api_key):
    """
    Checks if there are any sessions in 'QUEUED' state.
    Returns True if Safe (No Queue), False if Busy (Queue exists).
    """
    try:
        sessions = frappe.call("brain.api.get_jules_sessions", api_key=api_key)
        # Check if any session is QUEUED
        is_queued = any(s.get("state") == "QUEUED" for s in sessions)
        return not is_queued # Safe if NOT queued
    except Exception:
        # If API fails, assume safe to try (let Jules reject if needed) or fail open.
        return True

def construct_contextual_prompt(roadmap, feature, mode="Building"):
    """
    Constructs a prompt by replacing placeholders {stack}, {platform}, {dependency}, {feature_tags}
    with actual values from the Roadmap and Feature documents.
    """
    
    # 1. Fetch Prompts
    prompts = get_prompts()
    
    # 2. Find Best Match Prompt
    # Logic: Match Type (Feature/Bug) and Mode (Planning/Building)
    # Default to generic if no match
    feature_type = feature.get("type", "Feature")
    template = next((p for p in prompts if p.type == feature_type and p.mode == mode), None)
    
    if not template:
        # Fallback if no template found
        base_msg = f"Task: {feature.feature}\nDetails: {feature.explanation or 'No details provided.'}\nType: {feature.type}"
        return f"{base_msg}\n\nIMPORTANT: IMPLEMENTATION MODE. Please implement the requested changes." if mode == "Building" else base_msg

    prompt_text = template.prompt
    
    # 3. Gather Context
    # Classifications
    stacks = [c.value for c in roadmap.get("classifications", []) if c.category == "Stack"]
    platforms = [c.value for c in roadmap.get("classifications", []) if c.category == "Platform"]
    dependencies = [c.value for c in roadmap.get("classifications", []) if c.category == "Dependency"]
    
    stack_str = ", ".join(stacks) if stacks else "Unknown"
    platform_str = ", ".join(platforms) if platforms else "Web"
    dep_str = ", ".join(dependencies) if dependencies else "None specific"
    
    description = roadmap.get("description") or "No description provided."

    # Feature Tags
    ft_tags = [t.tag for t in feature.get("tags", [])] if feature else []
    tags_str = ", ".join(ft_tags) if ft_tags else "General"

    # 4. Inject Context
    prompt_text = prompt_text.replace("{stack}", stack_str)
    prompt_text = prompt_text.replace("{platform}", platform_str)
    prompt_text = prompt_text.replace("{dependency}", dep_str)
    prompt_text = prompt_text.replace("{feature_tags}", tags_str)
    
    # Append Description to System Context if not explicitly in template (Generic fallback)
    if "Roadmap Description:" not in prompt_text:
         prompt_text = f"Roadmap Description: {description}\n\n{prompt_text}"
    
    # 5. Append Task Specifics
    final_prompt = f"{prompt_text}\n\nTask: {feature.feature}\nDetails: {feature.explanation or 'No details provided.'}"
    
    return final_prompt
