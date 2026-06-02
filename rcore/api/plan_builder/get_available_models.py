import json
import frappe

@frappe.whitelist(allow_guest=True)
def get_available_models() -> dict:
    """
    Returns available AI models configured on the backend (Single Source of Truth)
    """
    trace_id = frappe.form_dict.get("trace_id") or "get-available-models-trace"
    import sys
    sys.stderr.write(f"[Trace: {trace_id}] get_available_models called\n")
    models_file = os.path.join(os.path.dirname(__file__), "models.json")
    if os.path.exists(models_file):
        try:
            with open(models_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            frappe.log_error(f"Failed to read models.json: {str(e)}", "AI Models Configuration")
    return {}
