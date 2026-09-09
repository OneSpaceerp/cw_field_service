# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

try:
	import frappe
	from frappe.model.document import Document
	from frappe.utils import add_to_date, now_datetime
except ImportError:
	class Document:  # type: ignore
		pass


class CWServiceRequest(Document):
	def validate(self):
		if "frappe" in globals() and frappe:
			# Auto calculate SLA due date if not explicitly set
			if self.sla_target_hours and not self.response_due_date:
				base_time = self.requested_date or now_datetime()
				self.response_due_date = add_to_date(base_time, hours=self.sla_target_hours)

			# Stamp resolution date upon resolution
			if self.status in ["Resolved", "Closed"] and not self.resolved_date:
				self.resolved_date = now_datetime()
