app_name = "cw_field_service"
app_title = "C-Water Field Service"
app_publisher = "Nest Software Development"
app_description = "Field Service Management for C-Water on ERPNext v16"
app_email = "info@nsd-eg.com"
app_license = "mit"

# Dependencies
required_apps = ["erpnext"]

# Document Events
doc_events = {
	"CW Site Visit": {
		"on_submit": "cw_field_service.field_service.doctype.cw_site_visit.cw_site_visit.on_visit_submit",
		"on_cancel": "cw_field_service.field_service.doctype.cw_site_visit.cw_site_visit.on_visit_cancel",
	}
}

# Permission query conditions
permission_query_conditions = {
	"CW Site Visit": "cw_field_service.field_service.doctype.cw_site_visit.cw_site_visit.get_permission_query_conditions",
}

# Scheduled Tasks
scheduler_events = {
	"daily": [
		"cw_field_service.utils.check_overdue_service_requests",
	],
}

# Fixtures to export/install
fixtures = [
	{
		"dt": "Role",
		"filters": [
			["name", "in", ["CW Field Engineer", "CW Field Supervisor", "CW Service Manager"]]
		]
	},
	{
		"dt": "CW Service Type",
		"filters": [["name", "!=", ""]]
	},
	{
		"dt": "CW Finding Category",
		"filters": [["name", "!=", ""]]
	},
	{
		"dt": "CW Operation Type",
		"filters": [["name", "!=", ""]]
	},
	{
		"dt": "CW Water Parameter Master",
		"filters": [["name", "!=", ""]]
	}
]
