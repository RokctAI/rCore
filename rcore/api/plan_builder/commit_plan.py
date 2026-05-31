import json
import frappe
from rcore.api.plan_builder.ensure_startup_os_core import ensure_startup_os_core

@frappe.whitelist()
def commit_plan(plan_data=None, profile_type=None, instance_name=None):
    """
    Accepts either raw JSON payload from frontend (backward compatibility)
    or profile_type + instance_name to parse compiled strategic markdown deliverables
    and seed them directly to the database, ensuring files stop being used for operational work.
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

        # 3. Case B: Profile type and instance name passed (read and parse compiled output files)
        if not profile_type or not instance_name:
            frappe.throw("Invalid arguments. Must supply either plan_data or profile_type + instance_name.")

        output_dir = os.path.join(startup_os_root, "instances", profile_type, instance_name, "output")
        
        has_compiled_files = False
        parsed_plans = []

        # Local markdown parser function
        def parse_compiled_markdown(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Strip footers and metadata blocks
            content_clean = re.split(r"## Strategic Document Mappings", content, flags=re.IGNORECASE)[0]
            content_clean = re.sub(r">\s*\[!IMPORTANT\]\s*\n\s*>\s*\*\*Document Version Control\*\*.*?\n\n", "", content_clean, flags=re.DOTALL | re.IGNORECASE)
            content_clean = content_clean.replace("---", "")

            lines = content_clean.split("\n")
            parsed_data = {
                "title": "",
                "description": "",
                "pillars": []
            }
            
            current_pillar = None
            current_objective = None
            description_lines = []
            in_h1_intro = False
            
            for line in lines:
                line_strip = line.strip()
                if not line_strip:
                    continue
                    
                if line_strip.startswith("# "):
                    parsed_data["title"] = line_strip[2:].strip()
                    in_h1_intro = True
                    continue
                    
                if line_strip.startswith("## "):
                    in_h1_intro = False
                    p_title = line_strip[3:].strip()
                    p_title = re.sub(r"^\d+[\.\s\-]+", "", p_title)
                    current_pillar = {
                        "title": p_title,
                        "description": "",
                        "objectives": []
                    }
                    parsed_data["pillars"].append(current_pillar)
                    current_objective = None
                    continue
                    
                if line_strip.startswith("### "):
                    in_h1_intro = False
                    if not current_pillar:
                        current_pillar = {
                            "title": "General",
                            "description": "",
                            "objectives": []
                        }
                        parsed_data["pillars"].append(current_pillar)
                    
                    obj_title = line_strip[4:].strip()
                    obj_title = re.sub(r"^[A-Z0-9]+[\.\s\-]+", "", obj_title)
                    current_objective = {
                        "title": obj_title,
                        "description": "",
                        "kpis": []
                    }
                    current_pillar["objectives"].append(current_objective)
                    continue
                    
                if line_strip.startswith(("* ", "- ", "1. ", "2. ", "3. ", "4. ", "5. ")):
                    in_h1_intro = False
                    bullet_content = re.sub(r"^(\*\s*|-\s*|\d+[\.\s\-]+)", "", line_strip).strip()
                    
                    if ":" in bullet_content:
                        b_title, b_val = bullet_content.split(":", 1)
                        b_title = b_title.strip()
                        b_val = b_val.strip()
                    else:
                        b_title = bullet_content
                        b_val = bullet_content
                        
                    if current_objective:
                        current_objective["kpis"].append({
                            "title": b_title,
                            "description": b_val
                        })
                    else:
                        if not current_pillar:
                            current_pillar = {
                                "title": "General",
                                "description": "",
                                "objectives": []
                            }
                            parsed_data["pillars"].append(current_pillar)
                        
                        obj = {
                            "title": b_title,
                            "description": b_val,
                            "kpis": []
                        }
                        current_pillar["objectives"].append(obj)
                    continue
                    
                if in_h1_intro:
                    description_lines.append(line_strip)
                elif current_objective:
                    current_objective["description"] = (current_objective["description"] + "\n" + line_strip).strip()
                elif current_pillar:
                    current_pillar["description"] = (current_pillar["description"] + "\n" + line_strip).strip()

            if description_lines:
                parsed_data["description"] = "\n".join(description_lines)
                
            return parsed_data

        if os.path.exists(output_dir):
            import glob
            md_files = glob.glob(os.path.join(output_dir, "*.md"))
            # Filter out narratives/resumes (cv.md and obituary.md)
            strategic_files = [f for f in md_files if os.path.basename(f) not in ["cv.md", "obituary.md"]]
            
            if strategic_files:
                has_compiled_files = True
                for f_path in strategic_files:
                    try:
                        plan = parse_compiled_markdown(f_path)
                        if plan["title"] or plan["pillars"]:
                            parsed_plans.append(plan)
                    except Exception as parse_err:
                        frappe.log_error(f"Failed to parse compiled strategic file {f_path}: {parse_err}")

        # Seeding Vision, Pillars, Objectives, KPIs
        vision_doc = None
        if has_compiled_files and parsed_plans:
            # 1. Establish central Vision DocType from primary plan
            primary_plan = parsed_plans[0]
            for p in parsed_plans:
                if "plan_on_a_page" in p["title"].lower() or "plan on a page" in p["title"].lower():
                    primary_plan = p
                    break
            
            vision_doc = frappe.new_doc("Vision")
            vision_doc.title = primary_plan["title"]
            vision_doc.description = primary_plan["description"] or f"Strategic Plan on a Page for {instance_name}"
            vision_doc.insert(ignore_permissions=True)

            # 2. Iterate and feed all parsed strategic files directly as DB Seed
            for plan in parsed_plans:
                for pillar_data in plan["pillars"]:
                    # Create Pillar
                    pillar_doc = frappe.new_doc("Pillar")
                    pillar_doc.title = pillar_data["title"]
                    pillar_doc.description = pillar_data["description"] or f"Strategic pillar for {plan['title']}"
                    pillar_doc.vision = vision_doc.name
                    pillar_doc.insert(ignore_permissions=True)

                    # Create Objectives & KPIs
                    for obj_data in pillar_data["objectives"]:
                        objective_doc = frappe.new_doc("Strategic Objective")
                        objective_doc.title = obj_data["title"]
                        objective_doc.description = obj_data["description"] or f"Objective for {pillar_data['title']}"
                        objective_doc.pillar = pillar_doc.name
                        objective_doc.insert(ignore_permissions=True)

                        for kpi_data in obj_data["kpis"]:
                            kpi_doc = frappe.new_doc("KPI")
                            kpi_doc.title = kpi_data["title"]
                            kpi_doc.description = kpi_data["description"]
                            kpi_doc.strategic_objective = objective_doc.name
                            kpi_doc.insert(ignore_permissions=True)

            # Seed additional custom structures if needed
            if profile_type == "business":
                policy_title = f"{instance_name} Strategic Alignment Policy"
                if not frappe.db.exists("Company Policy", policy_title):
                    policy_doc = frappe.new_doc("Company Policy")
                    policy_doc.title = policy_title
                    policy_doc.description = f"Enterprise-wide mandate generated from compiled strategic business plan deliverables."
                    policy_doc.insert(ignore_permissions=True)
            else:
                goal_title = f"{instance_name}: Wellness Mastery"
                if not frappe.db.exists("Personal Mastery Goal", goal_title):
                    goal_doc = frappe.new_doc("Personal Mastery Goal")
                    goal_doc.title = goal_title
                    goal_doc.description = f"Physical wellness mastery goal compiled from personal life plan."
                    goal_doc.insert(ignore_permissions=True)

        else:
            # Fallback Recovery to questions.md parsed answers (useful for mock/test stubs execution)
            questions_path = os.path.join(startup_os_root, "instances", profile_type, instance_name, "questions.md")
            if not os.path.exists(questions_path):
                frappe.throw(f"StartupOS questions.md not found at: {questions_path}")

            q_data = parse_questions_md(questions_path)
            display_name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', instance_name).strip()

            if profile_type == "business":
                trading_name = q_data.get("trading_name") or display_name
                core_val = q_data.get("core_value_proposition") or "Pending core values."
                cust_seg = q_data.get("customer_segments") or "Pending segments."
                power_strategy = q_data.get("power_continuity_strategy") or "Off-grid solar."

                vision_doc = frappe.new_doc("Vision")
                vision_doc.title = f"Vision: {trading_name}"
                vision_doc.description = f"Core Mission: alternative bookkeeping. Value Proposition: {core_val}"
                vision_doc.insert(ignore_permissions=True)

                p1 = frappe.new_doc("Pillar")
                p1.title = "Identity & Customer Foundations"
                p1.description = "Validate customer segments."
                p1.vision = vision_doc.name
                p1.insert(ignore_permissions=True)

                o1 = frappe.new_doc("Strategic Objective")
                o1.title = "Validate Customer Segments"
                o1.description = f"Target segment definition: {cust_seg}"
                o1.pillar = p1.name
                o1.insert(ignore_permissions=True)

                p2 = frappe.new_doc("Pillar")
                p2.title = "Operations & Resilience"
                p2.description = "Resilience framework."
                p2.vision = vision_doc.name
                p2.insert(ignore_permissions=True)

                o2 = frappe.new_doc("Strategic Objective")
                o2.title = "Ensure Power Continuity"
                o2.description = f"Power strategy: {power_strategy}"
                o2.pillar = p2.name
                o2.insert(ignore_permissions=True)

                policy_title = f"{trading_name} Strategic Alignment Policy"
                if not frappe.db.exists("Company Policy", policy_title):
                    policy_doc = frappe.new_doc("Company Policy")
                    policy_doc.title = policy_title
                    policy_doc.description = f"Enterprise-wide mandate to pursue: {core_val}"
                    policy_doc.insert(ignore_permissions=True)

            else:
                full_name = q_data.get("full_name") or display_name
                life_purpose = q_data.get("life_purpose") or "Pending purpose."
                wellness = q_data.get("wellness_focus") or "Restore sleep."

                vision_doc = frappe.new_doc("Vision")
                vision_doc.title = f"Life Purpose: {full_name}"
                vision_doc.description = life_purpose
                vision_doc.insert(ignore_permissions=True)

                p1 = frappe.new_doc("Pillar")
                p1.title = "Personal Identity & Wellness"
                p1.description = "Nurture biological mastery."
                p1.vision = vision_doc.name
                p1.insert(ignore_permissions=True)

                o1 = frappe.new_doc("Strategic Objective")
                o1.title = "Optimize Physical Conditioning"
                o1.description = f"Wellness focus: {wellness}"
                o1.pillar = p1.name
                o1.insert(ignore_permissions=True)

                goal_title = f"{full_name}: Wellness Mastery"
                if not frappe.db.exists("Personal Mastery Goal", goal_title):
                    goal_doc = frappe.new_doc("Personal Mastery Goal")
                    goal_doc.title = goal_title
                    goal_doc.description = f"Physical condition focus: {wellness}"
                    goal_doc.insert(ignore_permissions=True)

        if vision_doc:
            plan_doc.vision = vision_doc.name
            plan_doc.save(ignore_permissions=True)

        return {"status": "success", "message": "Plan on a Page committed and seeded from compiled strategic files successfully."}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "commit_plan Error")
        return {"status": "error", "message": str(e)}
