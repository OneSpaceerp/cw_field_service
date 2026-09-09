// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.query_reports["Water Parameter Trends"] = {
	filters: [
		{
			fieldname: "service_location",
			label: __("Site Location"),
			fieldtype: "Link",
			options: "CW Service Location"
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "parameter",
			label: __("Water Parameter"),
			fieldtype: "Link",
			options: "CW Water Parameter Master"
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
