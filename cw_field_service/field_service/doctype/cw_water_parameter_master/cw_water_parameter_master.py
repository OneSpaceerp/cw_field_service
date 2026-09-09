# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

try:
	import frappe
	from frappe.model.document import Document
except ImportError:
	class Document:  # type: ignore
		pass


class CWWaterParameterMaster(Document):
	def validate(self):
		if self.default_min_value and self.default_max_value:
			if self.default_min_value > self.default_max_value:
				if "frappe" in globals() and frappe:
					frappe.throw("Default Min Value cannot exceed Default Max Value.")
