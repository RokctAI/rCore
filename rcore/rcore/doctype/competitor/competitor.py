# Copyright (c) 2025 ROKCT INTELLIGENCE (PTY) LTD
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Competitor(Document):
    pass


@frappe.whitelist()
def get_map_data(competitor=None):
    """
    Retrieves all master map data (zones, routes) and competitor-specific locations.
    """
    zones = frappe.get_all(
        "Competitor Zone", fields=[
            "zone_name", "zone_path"])
    routes = frappe.get_all(
        "Competitor Route",
        fields=[
            "route_name",
            "route_type",
            "route_path"])

    locations = []
    if competitor and frappe.db.exists("Competitor", competitor):
        locations = frappe.get_all(
            "Competitor Location",
            filters={
                "parent": competitor,
                "parenttype": "Competitor"},
            fields=[
                "location_type",
                "location_name",
                "location_geolocation"])

    return {
        "status": "success",
        "data": {
            "locations": locations,
            "zones": zones,
            "routes": routes
        }
    }


@frappe.whitelist()
def save_competitor_locations(competitor, locations_data):
    """
    Saves only the location data for a specific competitor.
    Zones and Routes are master data and not saved from here.
    """
    import json

    if not frappe.db.exists("Competitor", competitor):
        return {"status": "error", "message": "Competitor not found"}

    try:
        data = json.loads(locations_data)
        doc = frappe.get_doc("Competitor", competitor)

        # Update locations
        doc.set("office_locations", [])
        for loc in data:  # The data is now just a list of locations
            doc.append(
                "office_locations", {
                    "location_type": loc.get("type"), "location_name": loc.get("name"), "location_geolocation": f'{
                        "type":"Point","coordinates":[{
                            loc.get("lng")},{
                            loc.get("lat")}]} '})

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"status": "success"}

    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            "Save Competitor Locations Error")
        return {"status": "error", "message": str(e)}


def get_dashboard_data(data):
    """
    Adds a custom "Tools" card to the Competitor dashboard.
    """
    data["transactions"].append({"label": "Tools",
                                 "items": [{"type": "page",
                                            "name": "competitor-analyzer",
                                            "label": "Competitor Map Analyzer",
                                            "description": "Analyze competitor locations and routes.",
                                            }],
                                 })
    return data
