# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

from typing import Any, Dict, List, Optional, Tuple

try:
	import frappe
except ImportError:
	frappe = None  # type: ignore


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
	columns = [
		{"label": "Visit ID", "fieldname": "name", "fieldtype": "Link", "options": "CW Site Visit", "width": 140},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": "Site Location", "fieldname": "service_location", "fieldtype": "Link", "options": "CW Service Location", "width": 140},
		{"label": "Engineer", "fieldname": "engineer_name", "fieldtype": "Data", "width": 150},
		{"label": "Planned Date", "fieldname": "planned_date", "fieldtype": "Date", "width": 110},
		{"label": "Check-in Time", "fieldname": "checkin_time", "fieldtype": "Datetime", "width": 140},
		{"label": "Distance (m)", "fieldname": "distance_to_site_meters", "fieldtype": "Float", "width": 110},
		{"label": "Geofence Status", "fieldname": "geofence_status", "fieldtype": "Data", "width": 120},
		{"label": "Exception Reason", "fieldname": "geofence_reason", "fieldtype": "Data", "width": 200},
		{"label": "Supervisor Decision", "fieldname": "supervisor_decision", "fieldtype": "Data", "width": 130},
	]

	if not frappe:
		return columns, []

	filters = filters or {}
	conds: Dict[str, Any] = {"geofence_status": ["in", ["Warning", "Exception"]]}

	if filters.get("geofence_status"):
		conds["geofence_status"] = filters["geofence_status"]
	if filters.get("customer"):
		conds["customer"] = filters["customer"]
	if filters.get("from_date") and filters.get("to_date"):
		conds["planned_date"] = ["between", [filters["from_date"], filters["to_date"]]]

	visits = frappe.get_all(
		"CW Site Visit",
		filters=conds,
		fields=[
			"name",
			"customer_name",
			"service_location",
			"engineer_name",
			"planned_date",
			"checkin_time",
			"distance_to_site_meters",
			"geofence_status",
			"geofence_reason",
			"supervisor_decision",
		],
		order_by="planned_date desc",
	)

	return columns, visits
