// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.ui.form.on("CW Site Visit", {
	refresh(frm) {
		// Filter service locations by customer
		if (frm.doc.customer) {
			frm.set_query("service_location", function () {
				return {
					filters: {
						customer: frm.doc.customer,
						is_active: 1
					}
				};
			});
		}

		// Action buttons
		if (!frm.is_new() && frm.doc.docstatus === 0) {
			// Check-in action
			if (frm.doc.visit_status === "Planned") {
				frm.add_custom_button(__("GPS Check-in (Start)"), function () {
					frm.trigger("perform_gps_checkin");
				}, __("Field Actions"));
			}

			// Check-out action
			if (frm.doc.visit_status === "In Progress") {
				frm.add_custom_button(__("GPS Check-out (Complete)"), function () {
					frm.trigger("perform_gps_checkout");
				}, __("Field Actions"));
			}

			// Populate Checklist Template
			if (!frm.doc.checklist_items || frm.doc.checklist_items.length === 0) {
				frm.add_custom_button(__("Load Checklist Template"), function () {
					frappe.prompt([
						{
							fieldname: "template",
							label: __("Checklist Template"),
							fieldtype: "Link",
							options: "CW Checklist Template",
							reqd: 1
						}
					], function (values) {
						frappe.call({
							method: "frappe.client.get",
							args: {
								doctype: "CW Checklist Template",
								name: values.template
							},
							callback: function (r) {
								if (r.message && r.message.checklist_items) {
									frm.clear_table("checklist_items");
									r.message.checklist_items.forEach(function (item) {
										let row = frm.add_child("checklist_items");
										row.checklist_item = item.checklist_item;
										row.response = item.response_type === "Pass/Fail" ? "Pass" : "Yes";
										row.is_mandatory = item.is_mandatory;
									});
									frm.refresh_field("checklist_items");
									frappe.show_alert({ message: __("Checklist items loaded"), indicator: "green" });
								}
							}
						});
					}, __("Select Template"));
				}, __("Tools"));
			}
		}
	},

	perform_gps_checkin(frm) {
		if (navigator.geolocation) {
			frappe.show_alert({ message: __("Acquiring GPS coordinates..."), indicator: "blue" });
			navigator.geolocation.getCurrentPosition(
				function (pos) {
					frm.set_value("checkin_time", frappe.datetime.now_datetime());
					frm.set_value("checkin_latitude", pos.coords.latitude);
					frm.set_value("checkin_longitude", pos.coords.longitude);
					frm.set_value("checkin_accuracy", pos.coords.accuracy);
					frm.set_value("visit_status", "In Progress");
					frm.save();
					frappe.msgprint(__("Check-in recorded at Lat: {0}, Lon: {1}", [pos.coords.latitude, pos.coords.longitude]));
				},
				function (err) {
					frappe.msgprint(__("GPS Error: {0}. You can enter reason manually if allowed.", [err.message]));
				},
				{ enableHighAccuracy: true, timeout: 10000 }
			);
		} else {
			frappe.msgprint(__("Geolocation is not supported by your browser."));
		}
	},

	perform_gps_checkout(frm) {
		if (navigator.geolocation) {
			navigator.geolocation.getCurrentPosition(
				function (pos) {
					frm.set_value("checkout_time", frappe.datetime.now_datetime());
					frm.set_value("checkout_latitude", pos.coords.latitude);
					frm.set_value("checkout_longitude", pos.coords.longitude);
					frm.set_value("checkout_accuracy", pos.coords.accuracy);
					frm.set_value("visit_status", "Pending Review");
					frm.save();
					frappe.msgprint(__("Check-out recorded and visit marked as Pending Review."));
				},
				function (err) {
					frm.set_value("checkout_time", frappe.datetime.now_datetime());
					frm.set_value("visit_status", "Pending Review");
					frm.save();
					frappe.msgprint(__("Check-out timestamp recorded without GPS."));
				}
			);
		}
	}
});
