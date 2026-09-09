// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

frappe.ui.form.on("CW Service Location", {
	refresh(frm) {
		if (frm.doc.latitude && frm.doc.longitude) {
			frm.add_custom_button(__("View on Google Maps"), function () {
				const url = `https://www.google.com/maps?q=${frm.doc.latitude},${frm.doc.longitude}`;
				window.open(url, "_blank");
			});
		}
	}
});
