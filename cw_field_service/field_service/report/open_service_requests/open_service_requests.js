// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.query_reports["Open Service Requests"] = {
	filters: [
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer"
		},
		{
			fieldname: "priority",
			label: __("Priority"),
			fieldtype: "Select",
			options: "\nLow\nMedium\nHigh\nCritical"
		}
	]
};
