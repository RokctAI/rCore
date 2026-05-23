# Unified Onboarding Integration & Strategic plan Verification Script
# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.

import os
import sys
import json
import shutil
from pathlib import Path

# Add directories to system path for local execution testing
SYS_PATHS = [
    r"C:\Users\sinya\Desktop\RokctAI\rcore",
    r"C:\Users\sinya\Desktop\RokctAI\control",
]
for p in SYS_PATHS:
    if p not in sys.path:
        sys.path.append(p)

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# --- 1. MOCK FRAPPE MODULE ENVIRONMENT ---
import types

class MockDoc:
    def __init__(self, doctype, name=None):
        self.doctype = doctype
        self.name = name or f"Mock-{doctype}-001"
        self.title = ""
        self.description = ""
        self.vision = None
        self.pillar = None
        self.strategic_objective = None

    def insert(self, ignore_permissions=False):
        print(f"   [Mock DB] INSERT {self.doctype} document: '{self.title or self.name}'")
        return self

    def save(self, ignore_permissions=False):
        print(f"   [Mock DB] SAVE {self.doctype} document: '{self.name}' with vision='{self.vision}'")
        return self


frappe_mock = types.ModuleType("frappe")
frappe_mock.conf = {}
frappe_mock.PermissionError = Exception

def throw(msg, exc=None):
    print(f"   [Mock Throw] {msg}")
    raise RuntimeError(msg)

def whitelist(allow_guest=False):
    def decorator(func):
        return func
    return decorator

def new_doc(doctype):
    return MockDoc(doctype)

def get_doc(doctype, name=None):
    return MockDoc(doctype, name)

def get_all(doctype, filters=None):
    print(f"   [Mock DB] GET ALL {doctype} with filters: {filters}")
    if doctype == "Pillar":
        return [MockDoc("Pillar", "Mock-Pillar-1")]
    elif doctype == "Strategic Objective":
        return [MockDoc("Strategic Objective", "Mock-Objective-1")]
    return []

def get_app_path(app, *parts):
    if app == "rcore":
        base = r"C:\Users\sinya\Desktop\RokctAI\rcore\rcore"
    else:
        base = r"C:\Users\sinya\Desktop\RokctAI\control\control"
    return os.path.join(base, *parts)

class MockDB:
    def delete(self, doctype, filters):
        print(f"   [Mock DB] DELETE {doctype} matching filters: {filters}")

    def exists(self, doctype, name):
        print(f"   [Mock DB] EXISTS check for {doctype} name: {name}")
        return False

    def set_value(self, doctype, name, fieldname, value):
        print(f"   [Mock DB] SET VALUE {doctype}:{name} -> {fieldname}={value}")
        return 1

    def commit(self):
        print("   [Mock DB] COMMIT transaction")

db = MockDB()

def log_error(message, title="Error"):
    print(f"   [Mock Logging] LOG ERROR [{title}]: {message}")

def get_traceback():
    return "Simulated traceback"

frappe_mock.throw = throw
frappe_mock.whitelist = whitelist
frappe_mock.new_doc = new_doc
frappe_mock.get_doc = get_doc
frappe_mock.get_all = get_all
frappe_mock.get_app_path = get_app_path
frappe_mock.db = db
frappe_mock.log_error = log_error
frappe_mock.get_traceback = get_traceback

sys.modules['frappe'] = frappe_mock

class MockModule(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self.__path__ = []

    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        
        full_submodule_name = f"{self.__name__}.{name}"
        
        class CallableMock(MockModule):
            def __call__(self, *args, **kwargs):
                return ""
                
        mock_obj = CallableMock(full_submodule_name)
        sys.modules[full_submodule_name] = mock_obj
        return mock_obj

# Dynamically register common submodules to satisfy all potential app imports
for sub in ["utils", "model", "geo", "contacts", "desk", "social", "website", "email", "exceptions"]:
    sys.modules[f'frappe.{sub}'] = MockModule(f'frappe.{sub}')




import frappe  # verify import works


# --- 2. RUN INTEGRATION VERIFICATION ---
def verify_onboarding_integration():
    print("======================================================================")
    print("🚀 STARTING INTEGRATION VERIFICATION: DECOUPLED STRATEGIC ONBOARDING")
    print("======================================================================\n")

    # A. Verify Control Site Template Retrieval
    print("STEP 1: Verify get_onboarding_template endpoint from Control...")
    try:
        from control.control.api import get_onboarding_template
        
        bus_template = get_onboarding_template("business")
        life_template = get_onboarding_template("life")
        
        assert len(bus_template) == 8, "Business template must contain 8 standard questions."
        assert len(life_template) == 8, "Life template must contain 8 standard questions."
        
        print("✅ STEP 1 SUCCESS: Templates retrieved successfully.")
        print(f"   - Business: {len(bus_template)} questions parsed.")
        print(f"   - Life: {len(life_template)} questions parsed.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ STEP 1 FAILURE: {e}")
        sys.exit(1)

    # B. Verify Tenant Profile Commit and Compilation
    print("\nSTEP 2: Verify commit_onboarding_answers (Business Profile) on Tenant...")
    try:
        from rcore.rcore.api.plan_builder import commit_onboarding_answers

        sample_answers = {
            "trading_name": "AntigravityLabs",
            "primary_base": "Johannesburg, South Africa",
            "core_value_proposition": "Building extreme robust agentic coding architectures.",
            "customer_segments": "Enterprise engineering teams and autonomous scale developers.",
            "power_continuity_strategy": "Hybrid solar arrays with segregated backup generator clusters.",
            "projected_year_1": "R2.5M revenue | R800k Net Profit",
            "projected_year_2": "R6.0M revenue | R2.0M Net Profit",
            "projected_year_3": "R15.0M revenue | R5.5M Net Profit",
        }

        sample_milestones = [
            {"date": "2026-05-23", "category": "Engineering", "text": "Completed core dynamic dynamic execution API"},
            {"date": "2026-05-24", "category": "Product", "text": "Launched test harness simulator suite"},
        ]

        # Trigger simulated profile commit (writes questions.md, runs compiler, commits to mock DB)
        result = commit_onboarding_answers(
            profile_type="business",
            instance_name="AntigravityLabs",
            answers=sample_answers,
            milestones=sample_milestones
        )

        print("\n✅ STEP 2 SUCCESS: Profile committed, compiled and database fed successfully.")
        print(f"   - Result details: {json.dumps(result, indent=2)}")

        # Verify filesystem side-effects
        # Determine the generated questions.md location
        startup_os_root = os.path.join(os.getcwd(), "StartupOS")
        questions_path = os.path.join(startup_os_root, "instances", "business", "AntigravityLabs", "questions.md")
        output_dir = os.path.join(startup_os_root, "instances", "business", "AntigravityLabs", "output")
        
        assert os.path.exists(questions_path), "File questions.md must exist on filesystem."
        assert os.path.exists(output_dir), "Compiler output directory must exist."
        
        print("✅ Filesystem side-effects verified successfully!")
        print(f"   - questions.md size: {os.path.getsize(questions_path)} bytes")
        print(f"   - Compiled files generated: {os.listdir(output_dir)}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ STEP 2 FAILURE: {e}")
        sys.exit(1)

    print("\n======================================================================")
    print("🎉 ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("======================================================================")


if __name__ == "__main__":
    verify_onboarding_integration()
