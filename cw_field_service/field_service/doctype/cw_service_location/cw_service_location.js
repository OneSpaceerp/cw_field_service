// Copyright (c) 2026, Nest Software Development & C-Water
// For license information, please see license.txt

function get_google_maps_url(frm) {
	const lat = frm.doc.latitude;
	const lng = frm.doc.longitude;
	if (lat && lng) {
		return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lat + "," + lng)}`;
	}
	const address = frm.doc.address_display || frm.doc.location_name;
	if (address) {
		return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
	}
	return null;
}

function update_google_maps_link(frm) {
	const url = get_google_maps_url(frm);

	if (url) {
		// 1. Top action button in the toolbar
		frm.add_custom_button(__("View on Google Maps"), function () {
			window.open(url, "_blank", "noopener,noreferrer");
		});

		// 2. Direct clickable link right under Longitude
		const coord_text = (frm.doc.latitude && frm.doc.longitude)
			? `(${frm.doc.latitude}, ${frm.doc.longitude})`
			: "";
		const link_desc = `
			<div style="margin-top: 5px;">
				<a href="${url}" target="_blank" rel="noopener noreferrer" style="color: #0284c7; font-weight: 600; text-decoration: underline; display: inline-flex; align-items: center; gap: 4px; font-size: 12px;">
					<span style="color: #dc2626; font-size: 14px;">📍</span>
					Open on Google Maps ${coord_text}
					<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
				</a>
			</div>
		`;
		frm.set_df_property("longitude", "description", link_desc);

		// 3. Render into dedicated HTML field in form
		if (frm.fields_dict.map_link_html && frm.fields_dict.map_link_html.$wrapper) {
			frm.fields_dict.map_link_html.$wrapper.html(`
				<div style="margin-top: 6px; margin-bottom: 10px;">
					<a href="${url}" target="_blank" rel="noopener noreferrer" class="btn btn-xs btn-primary font-weight-bold" style="color: #ffffff !important; display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border-radius: 6px; text-decoration: none; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">
						<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
						<span>Open on Google Maps</span>
						<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
					</a>
				</div>
			`);
		}

		// 4. Headline banner at the top of the form
		if (frm.dashboard) {
			frm.dashboard.clear_headline && frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				`<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
					<div style="font-size: 13px;">
						<span style="color: #dc2626; font-size: 15px; margin-right: 4px;">📍</span>
						<strong>Site GPS Location:</strong> ${frm.doc.latitude || "N/A"}, ${frm.doc.longitude || "N/A"}
					</div>
					<a href="${url}" target="_blank" rel="noopener noreferrer" class="btn btn-xs btn-primary font-weight-bold" style="color: #ffffff !important; text-decoration: none; padding: 4px 12px; border-radius: 6px;">
						Open in Google Maps <i class="fa fa-external-link" style="margin-left: 4px;"></i>
					</a>
				</div>`,
				"blue"
			);
		}
	} else {
		frm.set_df_property("longitude", "description", __("Enter Latitude & Longitude to open on Google Maps."));
		if (frm.fields_dict.map_link_html && frm.fields_dict.map_link_html.$wrapper) {
			frm.fields_dict.map_link_html.$wrapper.html("");
		}
		if (frm.dashboard && frm.dashboard.clear_headline) {
			frm.dashboard.clear_headline();
		}
	}
}

frappe.ui.form.on("CW Service Location", {
	refresh(frm) {
		update_google_maps_link(frm);
	},
	latitude(frm) {
		update_google_maps_link(frm);
	},
	longitude(frm) {
		update_google_maps_link(frm);
	},
	address_display(frm) {
		update_google_maps_link(frm);
	},
	location_name(frm) {
		update_google_maps_link(frm);
	}
});
