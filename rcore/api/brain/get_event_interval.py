import json
import frappe
from rcore import __version__ as brain_version
from rcore.services.jules_service import JulesClient

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

        start_pattern = re.compile(rf"{re.escape(start_event)} by .* on (\d{{4}}-\d{{2}}-\d{{2}})")
        end_pattern = re.compile(rf"{re.escape(end_event)} by .* on (\d{{4}}-\d{{2}}-\d{{2}})")

        for line in summary.split('\n'):
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
            return {"interval_days": interval.days, "interval_seconds": interval.total_seconds()}

        missing = []
        if not start_date:
            missing.append(start_event)
        if not end_date:
            missing.append(end_event)

        return {"error": f"Could not find one or more events in the document's history: {', '.join(missing)}"}

    except frappe.DoesNotExistError:
        return {"error": f"No Engram found for {reference_doctype} {reference_name}"}
    except Exception as e:
        frappe.log_error(f"Brain: Failed to get event interval: {e}", frappe.get_traceback())
        frappe.throw(f"An error occurred while calculating the event interval: {e}")
