# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

try:
	import frappe
	from frappe.model.document import Document
except ImportError:
	class Document:  # type: ignore
		pass


class CWServiceLocation(Document):
	def validate(self):
		if self.latitude is not None and not (-90.0 <= self.latitude <= 90.0):
			if "frappe" in globals() and frappe:
				frappe.throw("Latitude must be between -90.0 and 90.0 degrees.")
		if self.longitude is not None and not (-180.0 <= self.longitude <= 180.0):
			if "frappe" in globals() and frappe:
				frappe.throw("Longitude must be between -180.0 and 180.0 degrees.")
