import frappe
import json


def get_prompts():
    """
    Fetches prompts from Roadmap Settings.
    """
    try:
        settings = frappe.get_single("Roadmap Settings")
        return settings.prompts or []
    except BaseException:
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
        return not is_queued  # Safe if NOT queued
    except Exception:
        # If API fails, assume safe to try (let Jules reject if needed) or fail
        # open.
        return True


def construct_contextual_prompt(roadmap, feature, mode="Building"):
    """
    Constructs a prompt by replacing placeholders {stack}, {platform}, {dependency}, {feature_tags}
    with actual values from the Roadmap and Feature documents.
    Dynamically injects instructions based on tags.
    """

    # 1. Fetch Prompts
    prompts = get_prompts()

    # 2. Find Best Match Prompt
    feature_type = feature.get("type", "Feature")
    template = next((p for p in prompts if p.type ==
                    feature_type and p.mode == mode), None)

    if not template:
        base_msg = f"Task: {
            feature.feature}\nDetails: {
            feature.explanation or 'No details provided.'}\nType: {
            feature.type}"
        return f"{base_msg}\n\nIMPORTANT: IMPLEMENTATION MODE. Please implement the requested changes." if mode == "Building" else base_msg

    prompt_text = template.prompt

    # 3. Gather Context
    stacks = [
        c.value for c in roadmap.get(
            "classifications",
            []) if c.category == "Stack"]
    platforms = [
        c.value for c in roadmap.get(
            "classifications",
            []) if c.category == "Platform"]
    dependencies = [
        c.value for c in roadmap.get(
            "classifications",
            []) if c.category == "Dependency"]

    stack_str = ", ".join(stacks) if stacks else "Unknown"
    platform_str = ", ".join(platforms) if platforms else "Web"
    dep_str = ", ".join(dependencies) if dependencies else "None specific"

    description = roadmap.get("description") or "No description provided."

    # Feature Tags
    ft_tags = [t.tag for t in feature.get("tags", [])] if feature else []
    tags_str = ", ".join(ft_tags) if ft_tags else "General"

    # 4. Inject Context Parameters
    prompt_text = prompt_text.replace("{stack}", stack_str)
    prompt_text = prompt_text.replace("{platform}", platform_str)
    prompt_text = prompt_text.replace("{dependency}", dep_str)
    prompt_text = prompt_text.replace("{feature_tags}", tags_str)

    # Append Description
    if "Roadmap Description:" not in prompt_text:
        prompt_text = f"Roadmap Description: {description}\n\n{prompt_text}"

    # 5. Dynamic Tag Instruction Injection (Stack-Agnostic)
    # Only append instructions for tags that exist on this feature.

    tag_instructions = {
        "Frontend": "Frontend: Use the project's established UI/Component library (as defined in Stack). Ensure responsiveness and accessibility.",
        "UI": "UI: Focus on visual fidelity, spacing, and typography to match the premium design system.",
        "UX": "UX: Implement smooth interactions, loading states, and error handling for a seamless user experience.",
        "Backend": "Backend: ensure safe data handling, efficient queries, and strict type safety.",
        "Database": "Database: Maintain schema consistency. Use transactions for mutations.",
        "Security": "Security: Sanitize all inputs. Check permissions. Do not expose sensitive data.",
        "API": "API: Follow the existing API patterns (REST/RPC). Handle errors gracefully.",
        "Mobile": "Mobile: Optimize for touch targets and platform-specific guidelines (iOS/Android)."}

    injected_instructions = []
    for tag in ft_tags:
        # Match case-insensitive
        for key, instruction in tag_instructions.items():
            if key.lower() in tag.lower():
                injected_instructions.append(f"- {instruction}")

    if injected_instructions and "{tag_guidelines}" in prompt_text:
        # If placeholder exists, replace it
        prompt_text = prompt_text.replace(
            "{tag_guidelines}", "\n".join(injected_instructions))
    elif injected_instructions:
        # Otherwise append
        prompt_text += "\n\nTargeted Guidelines:\n" + \
            "\n".join(injected_instructions)

    # 6. Append Task Specifics
    final_prompt = f"{prompt_text}\n\nTask: {
        feature.feature}\nDetails: {
        feature.explanation or 'No details provided.'}"

    if mode == "Building":
        final_prompt += "\n\nIMPORTANT: IMPLEMENTATION MODE. Please implement the requested changes. You may create a Pull Request."

    return final_prompt
