# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


import json
import frappe


@frappe.whitelist()
def commit_onboarding_answers(profile_type, instance_name, answers, milestones=None):
    """
    Creates or updates the questions.md file for the given profile and instance name,
    runs the StartupOS compiler to render downstream deliverables, and commits
    the resulting plan to the database.
    """
    try:
        if profile_type not in ["business", "life"]:
            frappe.throw("Profile type must be 'business' or 'life'.")

        if not instance_name:
            frappe.throw("Instance name is required.")

        # Ensure core engines are loaded dynamically
        startup_os_root = ensure_startup_os_core()

        from core.compiler import compile_instance

        # Handle answers payload (deserialize if string)
        if isinstance(answers, str):
            answers = json.loads(answers)
        if milestones and isinstance(milestones, str):
            milestones = json.loads(milestones)

        # 1. Determine instance folder and write questions.md
        instance_dir = os.path.join(
            startup_os_root, "instances", profile_type, instance_name
        )
        os.makedirs(instance_dir, exist_ok=True)
        questions_path = os.path.join(instance_dir, "questions.md")

        # Human-friendly trading name
        display_name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", instance_name).strip()

        if profile_type == "business":
            trading_name = answers.get("trading_name") or display_name
            primary_base = answers.get("primary_base") or "Cape Town, South Africa"
            core_value_proposition = (
                answers.get("core_value_proposition") or "Pending — dynamic values."
            )
            customer_segments = answers.get("customer_segments") or "Pending."
            power_strategy = (
                answers.get("power_continuity_strategy") or "Off-grid solar."
            )
            y1 = answers.get("projected_year_1") or "Pending Year 1 projection."
            y2 = answers.get("projected_year_2") or "Pending Year 2 projection."
            y3 = answers.get("projected_year_3") or "Pending Year 3 projection."

            content = f"""# Business Strategic Questions: {trading_name}

This file is the Single Source of Truth (SSOT) for {trading_name}'s strategic, operational, and compliance variables.

---

## 1. Venture Identity & Foundations
*   **Trading Name**: What is the primary commercial brand or trading name?
    *   **Answer**: {trading_name}
*   **Primary Base**: What is your primary geographical base of operations?
    *   **Answer**: {primary_base}
*   **Core Value Proposition**: What is your product or service's unique value statement?
    *   **Answer**: {core_value_proposition}
*   **Customer Segments**: Who are the primary target users and demographic segments?
    *   **Answer**: {customer_segments}

---

## 2. Operations & Power Resilience
*   **Power Continuity Strategy**: How does your venture manage regional load shedding or grid failure?
    *   **Answer**: {power_strategy}

---

## 3. Financial Projections
*   **Projected Year 1**: What is the target Year 1 revenue and profit projection?
    *   **Answer**: {y1}
*   **Projected Year 2**: What is the target Year 2 revenue and profit projection?
    *   **Answer**: {y2}
*   **Projected Year 3**: What is the target Year 3 revenue and profit projection?
    *   **Answer**: {y3}
"""
        else:
            # life
            full_name = answers.get("full_name") or display_name
            gender = answers.get("gender") or "Male"
            primary_base = answers.get("primary_base") or "Cape Town, South Africa"
            life_purpose = answers.get("life_purpose") or "Pending purpose."
            wellness = answers.get("wellness_focus") or "Restore daily sleep depth."
            relationships = answers.get("key_relationships") or "Immediate family."
            legacy = answers.get("legacy_vision") or "Establish a generational legacy."
            ownership = answers.get("business_ownership") or "Pending."

            content = f"""# Life Strategic Questions: {full_name}

This file is the Single Source of Truth (SSOT) for {full_name}'s life development and tactical growth variables.

---

## 1. Personal Identity & Focus
*   **Full Name**: What is your full name?
    *   **Answer**: {full_name}
*   **Gender**: What is your gender?
    *   **Answer**: {gender}
*   **Primary Base**: What is your primary geographical base of operations?
    *   **Answer**: {primary_base}
*   **Life Purpose**: What is your high-level core mission or purpose statement?
    *   **Answer**: {life_purpose}
*   **Wellness Focus**: What is your primary wellness or biological high-performance goal?
    *   **Answer**: {wellness}

---

## 2. Relationships & Stewardship
*   **Key Relationships**: Who are the primary partners, confidants, or trustees in your life?
    *   **Answer**: {relationships}
*   **Legacy Vision**: What is the key long-term stewardship goal?
    *   **Answer**: {legacy}

---

## 3. Venture & Career Integration
*   **Business Ownership**: Do you own a registered business or run a side hustle?
    *   **Answer**: {ownership}
"""

        # Append milestones if provided
        if milestones:
            content += "\n\n## 4. Conversational Milestone Log (Living Ledger)\n"
            for m in milestones:
                m_date = m.get("date") or datetime.date.today().strftime("%Y-%m-%d")
                m_category = m.get("category") or "General"
                m_text = m.get("text") or ""
                if m_text:
                    content += f"\n*   **[{m_date}] ({m_category})**: {m_text}"

        with open(questions_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 2. Trigger the dynamic compiler
        compile_instance(profile_type, instance_name)

        # 3. Save to database using type-aware commit_plan
        db_result = commit_plan(profile_type=profile_type, instance_name=instance_name)

        # 4. Mark onboarding complete for the Company / site
        try:
            companies = frappe.get_all("Company", limit_page_length=1)
            if companies:
                frappe.db.set_value(
                    "Company", companies[0].name, "onboarding_complete", 1
                )
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to set onboarding_complete: {e}")

        return {
            "status": "success",
            "message": "Questions committed, compiled, and database plan updated successfully.",
            "db_result": db_result,
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "commit_onboarding_answers Error")
        return {"status": "error", "message": str(e)}
