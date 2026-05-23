# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
import json
import os
import re
import datetime
import sys
import urllib.request


def ensure_startup_os_core():
    """
    Ensures that the compiler.py and parser.py are available for the plan builder API.
    Resolves the StartupOS path dynamically. If running in Frappe, sites/StartupOS/core
    is the standard writable workspace. If files are missing, fetches them from raw GitHub.
    """
    # Determine writable StartupOS folder
    frappe_sites = "/home/frappe/frappe-bench/sites"
    if os.path.isdir(frappe_sites):
        startup_os_root = os.path.join(frappe_sites, "StartupOS")
    else:
        # Development fallback
        startup_os_root = os.path.join(os.getcwd(), "StartupOS")

    core_dir = os.path.join(startup_os_root, "core")
    os.makedirs(core_dir, exist_ok=True)

    init_py = os.path.join(core_dir, "__init__.py")
    if not os.path.exists(init_py):
        with open(init_py, 'w') as f:
            f.write("")

    core_files = ["compiler.py", "parser.py", "agent_bridge.py"]
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/RokctAI/The-Rokct-Protocol/main"
    github_raw_core = f"{GITHUB_RAW_BASE}/core/skills/startup_os/scripts/core"

    for f_name in core_files:
        dest_file = os.path.join(core_dir, f_name)
        # Always attempt fresh pull to stay updated, with fallback to local cached
        url = f"{github_raw_core}/{f_name}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(dest_file, 'wb') as f:
                    f.write(response.read())
        except Exception as e:
            if not os.path.exists(dest_file):
                # If offline and no local file, try to copy from local monorepo if available
                local_proto_file = f"c:\\Users\\sinya\\Desktop\\RokctAI\\Monorepo\\rcore\\rcore\\platform\\startup_os\\core\\{f_name}"
                if os.path.exists(local_proto_file):
                    import shutil
                    shutil.copy(local_proto_file, dest_file)
                else:
                    raise RuntimeError(f"Failed to fetch StartupOS core engine {f_name}: {e}")

    if startup_os_root not in sys.path:
        sys.path.insert(0, startup_os_root)

    return startup_os_root


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
        instance_dir = os.path.join(startup_os_root, "instances", profile_type, instance_name)
        os.makedirs(instance_dir, exist_ok=True)
        questions_path = os.path.join(instance_dir, "questions.md")

        # Human-friendly trading name
        display_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', instance_name).strip()

        if profile_type == "business":
            trading_name = answers.get("trading_name") or display_name
            primary_base = answers.get("primary_base") or "Cape Town, South Africa"
            core_value_proposition = answers.get("core_value_proposition") or "Pending — dynamic values."
            customer_segments = answers.get("customer_segments") or "Pending."
            power_strategy = answers.get("power_continuity_strategy") or "Off-grid solar."
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

        with open(questions_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # 2. Trigger the dynamic compiler
        compile_instance(profile_type, instance_name)

        # 3. Save to database using type-aware commit_plan
        db_result = commit_plan(profile_type=profile_type, instance_name=instance_name)

        # 4. Mark onboarding complete for the Company / site
        try:
            companies = frappe.get_all("Company", limit_page_length=1)
            if companies:
                frappe.db.set_value("Company", companies[0].name, "onboarding_complete", 1)
                frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to set onboarding_complete: {e}")

        return {
            "status": "success",
            "message": "Questions committed, compiled, and database plan updated successfully.",
            "db_result": db_result
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "commit_onboarding_answers Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def commit_plan(plan_data=None, profile_type=None, instance_name=None):
    """
    Accepts either raw JSON payload from frontend (backward compatibility)
    or profile_type + instance_name to read parsed answers from questions.md and feed the DB.
    """
    try:
        # Determine standard StartupOS paths and imports
        startup_os_root = ensure_startup_os_core()
        from core.parser import parse_questions_md

        # 1. Clear existing plan if any to avoid duplication
        plan_doc = frappe.get_doc("Plan On A Page")
        if plan_doc.vision:
            old_vision = plan_doc.vision
            # Delete old KPIs, Objectives, and Pillars linked to this Vision
            pillars = frappe.get_all("Pillar", filters={"vision": old_vision})
            for p in pillars:
                objectives = frappe.get_all("Strategic Objective", filters={"pillar": p.name})
                for o in objectives:
                    frappe.db.delete("KPI", {"strategic_objective": o.name})
                frappe.db.delete("Strategic Objective", {"pillar": p.name})
            frappe.db.delete("Pillar", {"vision": old_vision})
            frappe.db.delete("Vision", {"name": old_vision})
            
            plan_doc.vision = None
            plan_doc.save(ignore_permissions=True)

        # 2. Case A: Raw plan_data passed (backward compatibility)
        if plan_data:
            data = json.loads(plan_data)
            
            # Create the Vision
            vision_doc = frappe.new_doc("Vision")
            vision_doc.title = data.get("vision_title")
            vision_doc.description = data.get("vision_description")
            vision_doc.insert(ignore_permissions=True)

            # Create Pillars, Objectives, KPIs
            for pillar_data in data.get("pillars", []):
                pillar_doc = frappe.new_doc("Pillar")
                pillar_doc.title = pillar_data.get("title")
                pillar_doc.description = pillar_data.get("description")
                pillar_doc.vision = vision_doc.name
                pillar_doc.insert(ignore_permissions=True)

                for objective_data in pillar_data.get("objectives", []):
                    objective_doc = frappe.new_doc("Strategic Objective")
                    objective_doc.title = objective_data.get("title")
                    objective_doc.description = objective_data.get("description")
                    objective_doc.pillar = pillar_doc.name
                    objective_doc.insert(ignore_permissions=True)

                    for kpi_data in objective_data.get("kpis", []):
                        kpi_doc = frappe.new_doc("KPI")
                        kpi_doc.title = kpi_data.get("title")
                        kpi_doc.description = kpi_data.get("description")
                        kpi_doc.strategic_objective = objective_doc.name
                        kpi_doc.insert(ignore_permissions=True)

            plan_doc.vision = vision_doc.name
            plan_doc.save(ignore_permissions=True)
            return {"status": "success", "message": "Plan on a Page created successfully."}

        # 3. Case B: Profile type and instance name passed (read from questions.md)
        if not profile_type or not instance_name:
            frappe.throw("Invalid arguments. Must supply either plan_data or profile_type + instance_name.")

        questions_path = os.path.join(startup_os_root, "instances", profile_type, instance_name, "questions.md")
        if not os.path.exists(questions_path):
            frappe.throw(f"StartupOS questions.md not found at: {questions_path}")

        # Parse questions.md
        q_data = parse_questions_md(questions_path)
        display_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', instance_name).strip()

        # Build Vision, Pillars, Objectives, KPIs based on type
        if profile_type == "business":
            trading_name = q_data.get("trading_name") or display_name
            core_value_proposition = q_data.get("core_value_proposition") or "Pending core values."
            customer_segments = q_data.get("customer_segments") or "Pending target market."
            power_strategy = q_data.get("power_continuity_strategy") or "Pending operations strategy."
            y1 = q_data.get("projected_year_1") or "Pending Year 1."
            y2 = q_data.get("projected_year_2") or "Pending Year 2."
            y3 = q_data.get("projected_year_3") or "Pending Year 3."

            # Create Vision
            vision_doc = frappe.new_doc("Vision")
            vision_doc.title = f"Vision: {trading_name}"
            vision_doc.description = f"Core Mission: To deliver alternative bookkeeping and supply chain orchestration for unbanked micro-merchants.\n\nValue Proposition: {core_value_proposition}"
            vision_doc.insert(ignore_permissions=True)

            # Pillar 1: Identity & Customer Foundations
            p1 = frappe.new_doc("Pillar")
            p1.title = "Identity & Customer Foundations"
            p1.description = "Establish clear enterprise brand status and validate addressable customer segments."
            p1.vision = vision_doc.name
            p1.insert(ignore_permissions=True)

            o1_1 = frappe.new_doc("Strategic Objective")
            o1_1.title = "Validate Customer Segments"
            o1_1.description = f"Target segment definition: {customer_segments}"
            o1_1.pillar = p1.name
            o1_1.insert(ignore_permissions=True)

            o1_2 = frappe.new_doc("Strategic Objective")
            o1_2.title = "Deliver Core Value Proposition"
            o1_2.description = f"Commercial value validation: {core_value_proposition}"
            o1_2.pillar = p1.name
            o1_2.insert(ignore_permissions=True)

            # Pillar 2: Operations & Resilience
            p2 = frappe.new_doc("Pillar")
            p2.title = "Operations & Resilience"
            p2.description = "Robust off-grid execution and backup power/continuity resilience framework."
            p2.vision = vision_doc.name
            p2.insert(ignore_permissions=True)

            o2_1 = frappe.new_doc("Strategic Objective")
            o2_1.title = "Ensure Power Continuity"
            o2_1.description = f"Power strategy: {power_strategy}"
            o2_1.pillar = p2.name
            o2_1.insert(ignore_permissions=True)

            # Pillar 3: Financial Projections & Targets
            p3 = frappe.new_doc("Pillar")
            p3.title = "Financial Projections & Targets"
            p3.description = "3-year high-fidelity strategic performance milestones."
            p3.vision = vision_doc.name
            p3.insert(ignore_permissions=True)

            o3_1 = frappe.new_doc("Strategic Objective")
            o3_1.title = "Achieve Year 1 Milestone"
            o3_1.description = f"Financial Projection: {y1}"
            o3_1.pillar = p3.name
            o3_1.insert(ignore_permissions=True)

            o3_2 = frappe.new_doc("Strategic Objective")
            o3_2.title = "Achieve Year 2 Milestone"
            o3_2.description = f"Financial Projection: {y2}"
            o3_2.pillar = p3.name
            o3_2.insert(ignore_permissions=True)

            o3_3 = frappe.new_doc("Strategic Objective")
            o3_3.title = "Achieve Year 3 Milestone"
            o3_3.description = f"Financial Projection: {y3}"
            o3_3.pillar = p3.name
            o3_3.insert(ignore_permissions=True)

        else:
            # life
            full_name = q_data.get("full_name") or display_name
            life_purpose = q_data.get("life_purpose") or "Pending core purpose."
            wellness = q_data.get("wellness_focus") or "Restore sleep metrics."
            relationships = q_data.get("key_relationships") or "Immediate family."
            legacy = q_data.get("legacy_vision") or "Generational stewardship."
            ownership = q_data.get("business_ownership") or "Pending ownership."

            # Create Vision
            vision_doc = frappe.new_doc("Vision")
            vision_doc.title = f"Life Purpose: {full_name}"
            vision_doc.description = life_purpose
            vision_doc.insert(ignore_permissions=True)

            # Pillar 1: Personal Identity & Wellness
            p1 = frappe.new_doc("Pillar")
            p1.title = "Personal Identity & Wellness"
            p1.description = "Nurture physical, mental, and spiritual mastery."
            p1.vision = vision_doc.name
            p1.insert(ignore_permissions=True)

            o1_1 = frappe.new_doc("Strategic Objective")
            o1_1.title = "Optimize Physical Conditioning"
            o1_1.description = f"Wellness focus: {wellness}"
            o1_1.pillar = p1.name
            o1_1.insert(ignore_permissions=True)

            # Pillar 2: Relationships & Stewardship
            p2 = frappe.new_doc("Pillar")
            p2.title = "Relationships & Stewardship"
            p2.description = "Build evergreen partnership bonds and safeguard generational legacy assets."
            p2.vision = vision_doc.name
            p2.insert(ignore_permissions=True)

            o2_1 = frappe.new_doc("Strategic Objective")
            o2_1.title = "Strengthen Key Relationships"
            o2_1.description = f"Primary partners: {relationships}"
            o2_1.pillar = p2.name
            o2_1.insert(ignore_permissions=True)

            o2_2 = frappe.new_doc("Strategic Objective")
            o2_2.title = "Secure Generational Legacy"
            o2_2.description = f"Legacy vision: {legacy}"
            o2_2.pillar = p2.name
            o2_2.insert(ignore_permissions=True)

            # Pillar 3: Venture & Career Integration
            p3 = frappe.new_doc("Pillar")
            p3.title = "Venture & Career Integration"
            p3.description = "Align commercial activities with broader personal growth plans."
            p3.vision = vision_doc.name
            p3.insert(ignore_permissions=True)

            o3_1 = frappe.new_doc("Strategic Objective")
            o3_1.title = "Integrate Business & Career Growth"
            o3_1.description = f"Business ownership details: {ownership}"
            o3_1.pillar = p3.name
            o3_1.insert(ignore_permissions=True)

        plan_doc.vision = vision_doc.name
        plan_doc.save(ignore_permissions=True)

        # Create Company Policies or Personal Goals based on parsed answers
        if profile_type == "business":
            # Check and create default company policies if needed
            policy_title = f"{trading_name} Strategic Alignment Policy"
            if not frappe.db.exists("Company Policy", policy_title):
                policy_doc = frappe.new_doc("Company Policy")
                policy_doc.title = policy_title
                policy_doc.description = f"Enterprise-wide mandate to pursue: {core_value_proposition}\n\nPower Resilience Strategy: {power_strategy}"
                policy_doc.insert(ignore_permissions=True)
        else:
            # life
            goal_title = f"{full_name}: Wellness Mastery"
            if not frappe.db.exists("Personal Mastery Goal", goal_title):
                goal_doc = frappe.new_doc("Personal Mastery Goal")
                goal_doc.title = goal_title
                goal_doc.description = f"Physical condition focus: {wellness}"
                goal_doc.insert(ignore_permissions=True)

        return {"status": "success", "message": "Plan on a Page committed from questions.md successfully."}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "commit_plan Error")
        return {"status": "error", "message": str(e)}
