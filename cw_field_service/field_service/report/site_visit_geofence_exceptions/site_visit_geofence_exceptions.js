// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.query_reports["Site Visit Geofence Exceptions"] = {
	filters: [
		{
			fieldname: "geofence_status",
			label: __("Geofence Status"),
			fieldtype: "Select",
			options: "\nWarning\nException"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		}
	]
};
