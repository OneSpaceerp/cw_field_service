# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

from typing import Any, Dict, List, Optional, Tuple

try:
	import frappe
except ImportError:
	frappe = None  # type: ignore


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], None, Dict[str, Any]]:
	columns = [
		{"label": "Date", "fieldname": "planned_date", "fieldtype": "Date", "width": 110},
		{"label": "Site Location", "fieldname": "service_location", "fieldtype": "Link", "options": "CW Service Location", "width": 140},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 170},
		{"label": "Parameter", "fieldname": "parameter_name", "fieldtype": "Data", "width": 150},
		{"label": "Measured Value", "fieldname": "reading_value", "fieldtype": "Float", "width": 120},
		{"label": "Unit", "fieldname": "unit", "fieldtype": "Data", "width": 80},
		{"label": "Target Min", "fieldname": "min_range", "fieldtype": "Float", "width": 100},
		{"label": "Target Max", "fieldname": "max_range", "fieldtype": "Float", "width": 100},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": "Visit ID", "fieldname": "parent", "fieldtype": "Link", "options": "CW Site Visit", "width": 140},
	]

	if not frappe:
		return columns, [], None, {}

	filters = filters or {}
	conditions = ["v.docstatus < 2"]
	values: Dict[str, Any] = {}

	if filters.get("service_location"):
		conditions.append("v.service_location = %(service_location)s")
		values["service_location"] = filters["service_location"]

	if filters.get("customer"):
		conditions.append("v.customer = %(customer)s")
		values["customer"] = filters["customer"]

	if filters.get("parameter"):
		conditions.append("r.parameter = %(parameter)s")
		values["parameter"] = filters["parameter"]

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("v.planned_date BETWEEN %(from_date)s AND %(to_date)s")
		values["from_date"] = filters["from_date"]
		values["to_date"] = filters["to_date"]

	where_clause = " AND ".join(conditions)

	query = f"""
		SELECT
			v.planned_date,
			v.service_location,
			v.customer_name,
			r.parameter_name,
			CAST(r.reading_value AS DECIMAL(10, 2)) as reading_value,
			r.unit,
			r.min_range,
			r.max_range,
			r.status,
			r.parent
		FROM `tabCW Visit Reading` r
		JOIN `tabCW Site Visit` v ON r.parent = v.name
		WHERE {where_clause}
		ORDER BY v.planned_date ASC, r.idx ASC
	"""

	data = frappe.db.sql(query, values, as_dict=True)

	# Build chart data if a specific parameter is filtered
	chart = {}
	if filters.get("parameter") and data:
		labels = [str(d.get("planned_date")) for d in data]
		values_list = [d.get("reading_value") or 0.0 for d in data]
		param_label = data[0].get("parameter_name") or filters["parameter"]
		chart = {
			"data": {
				"labels": labels,
				"datasets": [{"name": param_label, "values": values_list}],
			},
			"type": "line",
			"height": 280,
		}

	return columns, data, None, chart
