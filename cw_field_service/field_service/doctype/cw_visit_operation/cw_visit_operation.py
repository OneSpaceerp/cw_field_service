# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

try:
	import frappe
	from frappe.model.document import Document
except ImportError:
	class Document:  # type: ignore
		pass


class CWVisitOperation(Document):
	pass
