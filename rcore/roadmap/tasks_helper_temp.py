# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


def _get_prompts():
    return []


def _construct_contextual_prompt(roadmap, feature, mode="Building"):
    """
    Constructs a prompt by replacing placeholders {stack}, {platform}, {dependency}, {feature_tags}
    with actual values from the Roadmap and Feature documents.
    """

    # 1. Fetch Prompts
    prompts = _get_prompts()

    # 2. Find Best Match Prompt
    # Logic: Match Type (Feature/Bug) and Mode (Planning/Building)
    # Default to generic if no match
    template = next((p for p in prompts if p.type ==
                    feature.type and p.mode == mode), None)

    if not template:
        # Fallback if no template found
        if mode == "Building":
            return f"Task: {
                feature.feature}\nDetails: {
                feature.explanation or 'No details provided.'}\nType: {
                feature.type}\n\nIMPORTANT: IMPLEMENTATION MODE. Please implement the requested changes."
        else:
            return f"Task: {
                feature.feature}\nDetails: {
                feature.explanation or 'No details provided.'}"

    prompt_text = template.prompt

    # 3. Gather Context
    # Classifications
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

    # Feature Tags
    # Need to fetch tags from child table 'tags' in Feature
    ft_tags = [t.tag for t in feature.get("tags", [])]
    tags_str = ", ".join(ft_tags) if ft_tags else "General"

    # 4. Inject Context
    prompt_text = prompt_text.replace("{stack}", stack_str)
    prompt_text = prompt_text.replace("{platform}", platform_str)
    prompt_text = prompt_text.replace("{dependency}", dep_str)
    prompt_text = prompt_text.replace("{feature_tags}", tags_str)

    # 5. Append Task Specifics
    # The template is just the "Persona/System" part. We need to append the
    # actual task.
    final_prompt = f"{prompt_text}\n\nTask: {
        feature.feature}\nDetails: {
        feature.explanation or 'No details provided.'}"

    return final_prompt
