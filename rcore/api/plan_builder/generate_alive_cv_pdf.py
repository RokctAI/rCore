# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe


@frappe.whitelist()
def generate_alive_cv_pdf(
    instance_name: str, profile_type: str = "life", role_focus: str = None
) -> dict:
    """
    Dynamically parses professional historical milestones from the Single Source of Truth (questions.md)
    and compiles a beautifully formatted, premium CV/Resume PDF on-demand, customized for a specific role focus.
    """
    trace_id = frappe.form_dict.get("trace_id") or "generate-alive-cv-pdf-trace"
    import sys

    sys.stderr.write(
        f"[Trace: {trace_id}] generate_alive_cv_pdf called for {instance_name}\n"
    )
    try:
        startup_os_root = ensure_startup_os_core()
        instance_dir = os.path.join(
            startup_os_root, "instances", profile_type, instance_name
        )
        questions_path = os.path.join(instance_dir, "questions.md")

        if not os.path.exists(questions_path):
            frappe.throw(
                f"Active strategic profile '{instance_name}' not found under {profile_type}."
            )

        # Parse main profile attributes from questions.md
        with open(questions_path, "r", encoding="utf-8") as f:
            q_content = f.read()

        full_name_match = re.search(
            r"# (?:Business Strategic Questions|Life Strategic Questions): (.*)",
            q_content,
        )
        full_name = full_name_match.group(1) if full_name_match else instance_name

        primary_base_match = re.search(
            r"\*\s+\*\*Primary Base\*\*:[^*]*\*\s+\*\*Answer\*\*:\s*(.*)", q_content
        )
        primary_base = (
            primary_base_match.group(1)
            if primary_base_match
            else "Cape Town, South Africa"
        )

        life_purpose_match = re.search(
            r"\*\s+\*\*Life Purpose\*\*:[^*]*\*\s+\*\*Answer\*\*:\s*(.*)", q_content
        )
        life_purpose = life_purpose_match.group(1) if life_purpose_match else ""

        # Parse milestones
        milestones = []
        in_milestones = False
        for line in q_content.splitlines():
            if "## 4. Conversational Milestone Log" in line:
                in_milestones = True
                continue
            if in_milestones:
                # Format: *   **[2026-05-26] (Category)**: Text
                match = re.match(
                    r"^\*\s+\*\*\[([^\]]+)\]\s+\(([^\)]+)\)\*\*:\s*(.*)$", line.strip()
                )
                if match:
                    milestones.append(
                        {
                            "date": match.group(1),
                            "category": match.group(2),
                            "text": match.group(3),
                        }
                    )

        # Apply LLM Role Customization if requested and key is present
        summary_intro = life_purpose
        if role_focus and (
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        ):
            try:
                # Use Completions to optimize the introductory profile for the target role focus
                system_prompt = "You are a professional CV Optimizer. Rewrite the user's career/life summary to dynamically align with the requested target role focus. Keep it concise (max 3 sentences)."
                user_content = f"Name: {full_name}\nOriginal summary: {life_purpose}\nTarget Role Focus: {role_focus}"

                # Dynamic completion via ROK completions endpoint
                import requests
                import os

                url = (
                    os.environ.get("ROK_COMPLETIONS_URL")
                    or "http://127.0.0.1:8642/v1/chat/completions"
                )
                payload = {
                    "model": "hermes-agent",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "stream": False,
                }
                res = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=15.0,
                )
                if res.ok:
                    choices = res.json().get("choices", [])
                    if choices:
                        summary_intro = (
                            choices[0].get("message", {}).get("content", "").strip()
                        )
            except Exception as e:
                frappe.log_error(
                    f"Failed to dynamically tailor CV for {role_focus}: {e}"
                )

        # Build Premium HTML template with harmonious styling (HSL, Inter Font, premium colors)
        milestones_html = ""
        for m in milestones:
            milestones_html += f"""
            <div class="timeline-item">
                <div class="timeline-date">{m["date"]}</div>
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <span class="timeline-category">{m["category"]}</span>
                    <p class="timeline-text">{m["text"]}</p>
                </div>
            </div>
            """

        if not milestones_html:
            milestones_html = "<p class='no-milestones'>No career or personal milestones logged yet. Share milestones ambiently with Rok!</p>"

        role_badge = (
            f"<span class='role-focus-badge'>{role_focus} Focus</span>"
            if role_focus
            else ""
        )

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Alive CV - {full_name}</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
            <style>
                body {{
                    font-family: 'Outfit', sans-serif;
                    color: #1e293b;
                    background-color: #ffffff;
                    margin: 0;
                    padding: 40px;
                    line-height: 1.6;
                }}
                .header {{
                    border-bottom: 2px solid #e2e8f0;
                    padding-bottom: 24px;
                    margin-bottom: 30px;
                    position: relative;
                }}
                .name {{
                    font-size: 36px;
                    font-weight: 800;
                    color: #0f172a;
                    margin: 0;
                    letter-spacing: -0.5px;
                }}
                .base {{
                    font-size: 14px;
                    color: #64748b;
                    font-weight: 600;
                    margin-top: 4px;
                }}
                .role-focus-badge {{
                    position: absolute;
                    top: 10px;
                    right: 0;
                    background-color: #6366f1;
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 14px;
                    border-radius: 9999px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .section {{
                    margin-bottom: 35px;
                }}
                .section-title {{
                    font-size: 18px;
                    font-weight: 600;
                    color: #4f46e5;
                    border-bottom: 1px solid #f1f5f9;
                    padding-bottom: 8px;
                    margin-bottom: 20px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .summary {{
                    font-size: 15px;
                    color: #334155;
                    margin: 0;
                }}
                .timeline {{
                    position: relative;
                    padding-left: 24px;
                }}
                .timeline::before {{
                    content: '';
                    position: absolute;
                    left: 4px;
                    top: 5px;
                    bottom: 5px;
                    width: 2px;
                    background-color: #e2e8f0;
                }}
                .timeline-item {{
                    position: relative;
                    margin-bottom: 24px;
                }}
                .timeline-date {{
                    font-size: 13px;
                    font-weight: 600;
                    color: #6366f1;
                    margin-bottom: 4px;
                }}
                .timeline-marker {{
                    position: absolute;
                    left: -24px;
                    top: 4px;
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background-color: #ffffff;
                    border: 2px solid #6366f1;
                }}
                .timeline-content {{
                    background: #f8fafc;
                    border: 1px solid #f1f5f9;
                    border-radius: 8px;
                    padding: 14px 18px;
                }}
                .timeline-category {{
                    display: inline-block;
                    font-size: 10px;
                    font-weight: 600;
                    color: #475569;
                    background-color: #cbd5e1;
                    padding: 2px 8px;
                    border-radius: 4px;
                    margin-bottom: 6px;
                    text-transform: uppercase;
                }}
                .timeline-text {{
                    font-size: 14px;
                    color: #334155;
                    margin: 0;
                }}
                .no-milestones {{
                    color: #64748b;
                    font-style: italic;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 class="name">{full_name}</h1>
                <div class="base">📍 {primary_base}</div>
                {role_badge}
            </div>

            <div class="section">
                <h2 class="section-title">Professional Executive Summary</h2>
                <p class="summary">{summary_intro}</p>
            </div>

            <div class="section">
                <h2 class="section-title">Milestones & Achievements Ledger</h2>
                <div class="timeline">
                    {milestones_html}
                </div>
            </div>
        </body>
        </html>
        """

        # Compile HTML string to pristine PDF binary
        from frappe.utils.pdf import get_pdf

        pdf_bytes = get_pdf(html)

        # Deliver as dynamic file attachment
        frappe.local.response.filename = f"Alive_CV_{instance_name}.pdf"
        frappe.local.response.filecontent = pdf_bytes
        frappe.local.response.type = "download"

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "generate_alive_cv_pdf Error")
        frappe.throw(f"Failed to generate dynamic CV PDF: {e}")
