// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.ui.form.on("CW Service Request", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Cancelled" && frm.doc.status !== "Closed") {
			frm.add_custom_button(__("Create Site Visit"), function () {
				frappe.new_doc("CW Site Visit", {
					service_request: frm.doc.name,
					customer: frm.doc.customer,
					service_location: frm.doc.service_location,
					assigned_engineer: frm.doc.assigned_engineer,
					supervisor: frm.doc.assigned_supervisor,
					visit_type: frm.doc.request_type,
					priority: frm.doc.priority
				});
			}, __("Actions"));
		}
	},

	customer(frm) {
		if (frm.doc.customer) {
			// Filter service location by customer
			frm.set_query("service_location", function () {
				return {
					filters: {
						customer: frm.doc.customer,
						is_active: 1
					}
				};
			});
		}
	}
});
