# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

from typing import Any, Dict, List, Tuple

try:
	import frappe
	from frappe.utils import date_diff, now_datetime
except ImportError:
	frappe = None  # type: ignore


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
	columns = [
		{"label": "Request ID", "fieldname": "name", "fieldtype": "Link", "options": "CW Service Request", "width": 140},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 180},
		{"label": "Site Location", "fieldname": "service_location", "fieldtype": "Link", "options": "CW Service Location", "width": 140},
		{"label": "Request Type", "fieldname": "request_type", "fieldtype": "Link", "options": "CW Service Type", "width": 140},
		{"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 90},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": "Requested Date", "fieldname": "requested_date", "fieldtype": "Date", "width": 110},
		{"label": "Response Due Date", "fieldname": "response_due_date", "fieldtype": "Datetime", "width": 140},
		{"label": "Assigned Engineer", "fieldname": "assigned_engineer", "fieldtype": "Link", "options": "Employee", "width": 140},
		{"label": "SLA Status", "fieldname": "sla_status", "fieldtype": "Data", "width": 110},
	]

	if not frappe:
		return columns, []

	filters = filters or {}
	conds = {"status": ["in", ["Open", "Scheduled", "In Progress"]]}
	if filters.get("customer"):
		conds["customer"] = filters["customer"]
	if filters.get("priority"):
		conds["priority"] = filters["priority"]

	requests = frappe.get_all(
		"CW Service Request",
		filters=conds,
		fields=[
			"name",
			"customer_name",
			"service_location",
			"request_type",
			"priority",
			"status",
			"requested_date",
			"response_due_date",
			"assigned_engineer",
		],
		order_by="response_due_date asc, creation asc",
	)

	now = now_datetime()
	for r in requests:
		if r.get("response_due_date"):
			r["sla_status"] = "Overdue" if r["response_due_date"] < now else "Within SLA"
		else:
			r["sla_status"] = "No SLA"

	return columns, requests
