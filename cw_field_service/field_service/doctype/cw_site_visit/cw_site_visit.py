# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

from typing import Optional

try:
	import frappe
	from frappe import _
	from frappe.model.document import Document
	from frappe.utils import flt, get_datetime, now_datetime, time_diff_in_seconds
except ImportError:
	frappe = None  # type: ignore
	def _(msg): return msg
	class Document:  # type: ignore
		pass
	def flt(v, precision=None):
		try: return float(v)
		except (ValueError, TypeError): return 0.0
	def get_datetime(v):
		from datetime import datetime
		if isinstance(v, str):
			return datetime.fromisoformat(v)
		return v
	def now_datetime():
		from datetime import datetime
		return datetime.now()

from cw_field_service.utils import evaluate_geofence


class CWSiteVisit(Document):
	def validate(self):
		self.ensure_service_location_and_approval()
		self.validate_geofence_and_distance()
		self.calculate_duration()
		self.validate_readings_ranges()
		self.validate_mandatory_items()

	def ensure_service_location_and_approval(self):
		if not frappe or not getattr(self, "customer", None):
			return

		is_onsite = getattr(self, "creation_source", "") == "Engineer On-Site"

		# If engineer created on-site with coordinates, use GPS as location approval
		if is_onsite and getattr(self, "checkin_latitude", None) and getattr(self, "checkin_longitude", None):
			if not getattr(self, "service_location", None):
				loc = frappe.db.get_value("CW Service Location", {"customer": self.customer, "is_active": 1}, "name")
				if loc:
					self.service_location = loc
				else:
					import random
					import string
					rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
					cust_clean = "".join(c for c in (self.customer or "SITE") if c.isalnum())[:8].upper()
					site_code = f"SITE-{cust_clean}-{rand_suffix}"
					try:
						new_loc = frappe.get_doc({
							"doctype": "CW Service Location",
							"site_code": site_code,
							"location_name": f"{getattr(self, 'customer_name', None) or self.customer} Site",
							"customer": self.customer,
							"is_active": 1,
							"latitude": flt(self.checkin_latitude),
							"longitude": flt(self.checkin_longitude),
							"geofence_radius_meters": 200.0,
						}).insert(ignore_permissions=True)
						self.service_location = new_loc.name
					except Exception:
						pass

			if getattr(self, "service_location", None):
				loc_coords = frappe.db.get_value(
					"CW Service Location",
					self.service_location,
					["latitude", "longitude"],
					as_dict=True,
				)
				if loc_coords and (not loc_coords.latitude or not loc_coords.longitude):
					frappe.db.set_value(
						"CW Service Location",
						self.service_location,
						{
							"latitude": flt(self.checkin_latitude),
							"longitude": flt(self.checkin_longitude),
						},
						update_modified=False,
					)
				self.geofence_status = "Verified"
				self.distance_to_site_meters = 0.0

	def validate_geofence_and_distance(self):
		if getattr(self, "creation_source", "") == "Engineer On-Site" and getattr(self, "geofence_status", "") == "Verified":
			return

		if not self.service_location:
			return

		site_lat, site_lon, site_radius = None, None, 200.0
		if frappe:
			loc = frappe.db.get_value(
				"CW Service Location",
				self.service_location,
				["latitude", "longitude", "geofence_radius_meters"],
				as_dict=True,
			)
			if loc:
				site_lat = loc.latitude
				site_lon = loc.longitude
				site_radius = flt(loc.geofence_radius_meters) or 200.0

		if self.checkin_latitude and self.checkin_longitude and site_lat and site_lon:
			status, dist = evaluate_geofence(
				self.checkin_latitude,
				self.checkin_longitude,
				site_lat,
				site_lon,
				radius_meters=site_radius,
			)
			self.geofence_status = status
			self.distance_to_site_meters = dist

			if self.geofence_status == "Exception" and not self.geofence_reason:
				if self.visit_status in ["Pending Review", "Approved"] and frappe:
					frappe.throw(
						_("Check-in is outside the registered site geofence ({0}m away). Please provide a Geofence Exception Reason.").format(
							dist
						)
					)

	def calculate_duration(self):
		if self.checkin_time and self.checkout_time:
			start = get_datetime(self.checkin_time)
			end = get_datetime(self.checkout_time)
			diff_sec = (end - start).total_seconds()
			if diff_sec > 0:
				self.visit_duration_minutes = round(diff_sec / 60.0, 1)

	def validate_readings_ranges(self):
		for row in getattr(self, "readings", []):
			if row.reading_value:
				try:
					val = float(row.reading_value)
					if row.min_range is not None and row.max_range is not None:
						if val < flt(row.min_range) or val > flt(row.max_range):
							if row.status == "Normal":
								row.status = "Warning"
				except (ValueError, TypeError):
					pass

	def validate_mandatory_items(self):
		if self.visit_status in ["Pending Review", "Approved"] or getattr(self, "docstatus", 0) == 1:
			for item in getattr(self, "checklist_items", []):
				if item.is_mandatory and not item.response:
					if frappe:
						frappe.throw(_("Checklist item '{0}' is mandatory and must have a response.").format(item.checklist_item))

	def before_submit(self):
		if not self.outcome:
			if frappe:
				frappe.throw(_("Please specify the visit Outcome before submitting."))
		if self.supervisor_decision != "Approved":
			if frappe:
				frappe.throw(_("A visit can only be submitted after Supervisor Approval (Supervisor Decision must be 'Approved')."))
		self.visit_status = "Approved"

	def on_submit(self):
		on_visit_submit(self)

	def on_cancel(self):
		on_visit_cancel(self)


def on_visit_submit(doc, method=None):
	"""Called on submit of CW Site Visit to update linked CW Service Request."""
	if not frappe or not doc.service_request:
		return

	req = frappe.get_doc("CW Service Request", doc.service_request)
	if doc.outcome in ["Resolved", "Partially Resolved"]:
		req.status = "Resolved"
		req.resolution_summary = doc.executive_summary or _("Resolved via Site Visit {0}").format(doc.name)
		req.resolved_date = now_datetime()
	elif doc.outcome == "Follow-up Required":
		req.status = "In Progress"
		req.closure_remarks = _("Follow-up required from visit {0}").format(doc.name)
	req.save(ignore_permissions=True)


def on_visit_cancel(doc, method=None):
	"""Called on cancel of CW Site Visit."""
	if not frappe or not doc.service_request:
		return

	req = frappe.get_doc("CW Service Request", doc.service_request)
	if req.status == "Resolved":
		req.status = "In Progress"
		req.save(ignore_permissions=True)


def get_permission_query_conditions(user):
	"""Row-level permission filter ensuring Field Engineers only see their own assigned visits."""
	if not user or not frappe:
		return ""

	roles = frappe.get_roles(user)
	if "System Manager" in roles or "CW Service Manager" in roles or "CW Field Supervisor" in roles:
		return ""

	if "CW Field Engineer" in roles:
		# Return SQL filter matching employee record
		return f"""(`tabCW Site Visit`.assigned_engineer IN (
			SELECT name FROM `tabEmployee` WHERE user_id = {frappe.db.escape(user)}
		))"""

	return ""
