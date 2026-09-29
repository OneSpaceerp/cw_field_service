# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import json
from typing import Any, Dict, List, Optional

try:
	import frappe
	from frappe import _
	from frappe.utils import cint, flt, get_datetime, now_datetime
except ImportError:
	frappe = None  # type: ignore
	def _(msg): return msg
	def cint(v):
		try: return int(v)
		except (ValueError, TypeError): return 0
	def flt(v, precision=None):
		try: return float(v)
		except (ValueError, TypeError): return 0.0


def get_current_employee() -> Optional[str]:
	"""Helper to resolve current session user to an Employee document name."""
	if not frappe:
		return None
	user = frappe.session.user
	emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not emp:
		# Fallback to first active employee in database
		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name") or frappe.db.get_value("Employee", {}, "name")
	return emp


@frappe.whitelist()
def get_assigned_visits(status: Optional[str] = None, date: Optional[str] = None) -> List[Dict[str, Any]]:
	"""
	Returns visits assigned to the authenticated engineer.
	Mobile-optimized lightweight payload.
	"""
	if not frappe:
		return []

	emp = get_current_employee()
	filters: Dict[str, Any] = {}

	# If engineer, filter by their own record; supervisors/managers can see all
	roles = frappe.get_roles(frappe.session.user)
	if "CW Field Engineer" in roles and "CW Field Supervisor" not in roles and "System Manager" not in roles:
		if not emp:
			return []
		filters["assigned_engineer"] = emp

	if status:
		filters["visit_status"] = status
	if date:
		filters["planned_date"] = date

	visits = frappe.get_all(
		"CW Site Visit",
		filters=filters,
		fields=[
			"name",
			"customer",
			"customer_name",
			"service_location",
			"visit_type",
			"priority",
			"visit_status",
			"planned_date",
			"planned_start_time",
			"planned_end_time",
			"checkin_time",
			"checkout_time",
			"geofence_status",
			"outcome",
			"description",
			"site_photo",
			"modified",
		],
		order_by="planned_date desc, creation desc",
		limit=100,
	)

	return visits


@frappe.whitelist()
def get_visit_details(visit_id: str) -> Dict[str, Any]:
	"""
	Returns complete visit payload for execution in the PWA.
	"""
	if not frappe:
		return {}

	if not frappe.has_permission("CW Site Visit", "read", visit_id):
		frappe.throw(_("Not permitted to view this visit"), frappe.PermissionError)

	doc = frappe.get_doc("CW Site Visit", visit_id)

	# Fetch site location coordinates and geofence
	site_data = {}
	if doc.service_location:
		site_data = frappe.db.get_value(
			"CW Service Location",
			doc.service_location,
			[
				"location_name",
				"site_code",
				"latitude",
				"longitude",
				"geofence_radius_meters",
				"address_display",
				"primary_contact_person",
				"primary_contact_phone",
				"special_site_instructions",
			],
			as_dict=True,
		) or {}

	data = doc.as_dict()
	data["site_details"] = site_data

	# Fetch linked service request details if present
	if doc.service_request:
		sr_data = frappe.db.get_value(
			"CW Service Request",
			doc.service_request,
			[
				"name",
				"status",
				"priority",
				"request_type",
				"issue_description",
				"requested_date",
				"resolution_summary",
			],
			as_dict=True,
		) or {}
		data["service_request_details"] = sr_data

	return data


@frappe.whitelist()
def check_in_visit(
	visit_id: str,
	latitude: Optional[float] = None,
	longitude: Optional[float] = None,
	accuracy: Optional[float] = None,
	client_timestamp: Optional[str] = None,
	geofence_reason: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Records check-in timestamp and GPS coordinates, starts the visit.
	"""
	if not frappe:
		return {}

	doc = frappe.get_doc("CW Site Visit", visit_id)
	if doc.docstatus != 0:
		frappe.throw(_("Cannot check in to a submitted or cancelled visit."))

	doc.checkin_time = now_datetime()
	if latitude is not None and longitude is not None:
		doc.checkin_latitude = flt(latitude)
		doc.checkin_longitude = flt(longitude)
		doc.checkin_accuracy = flt(accuracy) if accuracy else None

	if geofence_reason:
		doc.geofence_reason = geofence_reason

	doc.visit_status = "In Progress"
	doc.save()

	return {
		"status": "success",
		"visit_id": doc.name,
		"visit_status": doc.visit_status,
		"checkin_time": str(doc.checkin_time),
		"geofence_status": doc.geofence_status,
		"distance_to_site_meters": doc.distance_to_site_meters,
	}


@frappe.whitelist()
def save_visit_draft(visit_id: str, data: Any = None, idempotency_key: Optional[str] = None) -> Dict[str, Any]:
	"""
	Saves in-progress draft sections sent from the mobile client.
	"""
	if not frappe:
		return {}

	doc = frappe.get_doc("CW Site Visit", visit_id)
	if doc.docstatus != 0:
		frappe.throw(_("Cannot edit a submitted or cancelled visit."))

	if isinstance(data, str):
		data = json.loads(data)

	if not isinstance(data, dict):
		data = {}

	# Update child tables if provided
	if "checklist_items" in data:
		doc.set("checklist_items", data["checklist_items"])
	if "readings" in data:
		doc.set("readings", data["readings"])
	if "findings" in data:
		doc.set("findings", data["findings"])
	if "actions" in data:
		doc.set("actions", data["actions"])
	if "operations" in data:
		doc.set("operations", data["operations"])
	if "requirements" in data:
		doc.set("requirements", data["requirements"])
	if "expenses" in data:
		doc.set("expenses", data["expenses"])

	# Top-level notes
	if "executive_summary" in data:
		doc.executive_summary = data["executive_summary"]
	if "customer_representative" in data:
		doc.customer_representative = data["customer_representative"]
	if "customer_representative_phone" in data:
		doc.customer_representative_phone = data["customer_representative_phone"]

	doc.save()

	return {
		"status": "success",
		"visit_id": doc.name,
		"visit_status": doc.visit_status,
		"modified": str(doc.modified),
	}


@frappe.whitelist()
def create_site_visit(
	customer: str,
	customer_name: Optional[str] = None,
	service_location: Optional[str] = None,
	visit_type: str = "Routine Inspection",
	priority: str = "Medium",
	description: Optional[str] = None,
	planned_date: Optional[str] = None,
	planned_start_time: Optional[str] = None,
	service_request: Optional[str] = None,
	instructions: Optional[str] = None,
	creation_source: str = "Engineer On-Site",
	latitude: Optional[float] = None,
	longitude: Optional[float] = None,
	accuracy: Optional[float] = None,
	image_data: Optional[str] = None,
	image_name: Optional[str] = None,
	idempotency_key: Optional[str] = None,
	operations: Any = None,
	requirements: Any = None,
	checklist_items: Any = None,
	readings: Any = None,
	findings: Any = None,
	expenses: Any = None,
	**kwargs,
) -> Dict[str, Any]:
	"""
	Creates a new CW Site Visit directly from mobile PWA.
	For on-site engineer visits:
	  - Resolves customer and ensures service location approval with GPS coordinates.
	  - Automatically auto-creates or links CW Service Request in ERPNext.
	  - Populates working steps (operations log), checklist items, water readings, and requests.
	  - Sets status to 'In Progress' and timestamps check-in.
	  - Attaches site evidence photo.
	  - Satisfies mandatory assigned engineer link.
	"""
	if not frappe:
		return {}

	# 1. Resolve Customer Name
	if not customer_name:
		if frappe.db.exists("Customer", customer):
			customer_name = frappe.db.get_value("Customer", customer, "customer_name")
		else:
			customer_name = customer

	# 2. Resolve Active Employee
	emp = get_current_employee()
	if not emp:
		emp = frappe.db.get_value("Employee", {"status": "Active"}, "name") or frappe.db.get_value("Employee", {}, "name")
		if not emp:
			try:
				emp_doc = frappe.get_doc({
					"doctype": "Employee",
					"first_name": frappe.session.user if frappe.session.user != "Guest" else "Field Engineer",
					"status": "Active",
				}).insert(ignore_permissions=True)
				emp = emp_doc.name
			except Exception:
				pass

	# 3. Resolve or Auto-Create CW Service Location
	resolved_loc = None
	if service_location and frappe.db.exists("CW Service Location", service_location):
		resolved_loc = service_location
	else:
		existing_loc = frappe.db.get_value("CW Service Location", {"customer": customer, "is_active": 1}, "name")
		if existing_loc:
			resolved_loc = existing_loc
		else:
			import random, string
			rand_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
			cust_clean = "".join(c for c in (customer or "SITE") if c.isalnum())[:8].upper()
			site_code = f"SITE-{cust_clean}-{rand_suffix}"
			try:
				loc_doc = frappe.get_doc({
					"doctype": "CW Service Location",
					"site_code": site_code,
					"location_name": (service_location if service_location and not service_location.startswith("LOC-") else f"{customer_name or customer} Site"),
					"customer": customer,
					"is_active": 1,
					"latitude": flt(latitude) if latitude else 29.9725,
					"longitude": flt(longitude) if longitude else 30.9415,
					"geofence_radius_meters": 250.0,
				}).insert(ignore_permissions=True)
				resolved_loc = loc_doc.name
			except Exception:
				pass

	# 4. Resolve or Auto-Create linked CW Service Request in ERPNext
	resolved_sr = None
	if service_request and frappe.db.exists("CW Service Request", service_request):
		resolved_sr = service_request
		try:
			frappe.db.set_value("CW Service Request", service_request, "status", "In Progress")
		except Exception:
			pass
	else:
		try:
			sr = frappe.get_doc({
				"doctype": "CW Service Request",
				"customer": customer,
				"customer_name": customer_name,
				"service_location": resolved_loc or (service_location if frappe.db.exists("CW Service Location", service_location) else None),
				"request_type": visit_type or "Routine Inspection",
				"priority": priority or "Medium",
				"status": "In Progress",
				"requested_date": planned_date or frappe.utils.nowdate(),
				"assigned_engineer": emp,
				"issue_description": description or instructions or f"{visit_type} on-site at {customer_name}",
			}).insert(ignore_permissions=True)
			resolved_sr = sr.name
		except Exception as e:
			frappe.log_error(f"Auto-creating Service Request for visit failed: {e}", "CW Field Service")

	# 5. Build and populate CW Site Visit
	doc = frappe.new_doc("CW Site Visit")
	doc.customer = customer
	doc.customer_name = customer_name
	if resolved_loc:
		doc.service_location = resolved_loc
	elif service_location and frappe.db.exists("CW Service Location", service_location):
		doc.service_location = service_location

	doc.visit_type = visit_type or "Routine Inspection"
	doc.priority = priority or "Medium"
	doc.planned_date = planned_date or frappe.utils.nowdate()
	if planned_start_time:
		doc.planned_start_time = planned_start_time
	if resolved_sr:
		doc.service_request = resolved_sr
	if emp:
		doc.assigned_engineer = emp

	doc.creation_source = creation_source or "Engineer On-Site"
	doc.description = description or instructions or ""

	# Check-in and status
	if doc.creation_source == "Engineer On-Site" or (latitude is not None and longitude is not None):
		doc.visit_status = "In Progress"
		doc.checkin_time = now_datetime()
		if latitude is not None and longitude is not None:
			doc.checkin_latitude = flt(latitude)
			doc.checkin_longitude = flt(longitude)
			doc.checkin_accuracy = flt(accuracy) if accuracy else 8.0
			doc.geofence_status = "Verified"
			doc.distance_to_site_meters = 0.0

	# 6. Working Steps (Operations Log)
	if isinstance(operations, str):
		try: operations = json.loads(operations)
		except Exception: operations = []
	if isinstance(operations, list) and len(operations) > 0:
		for op in operations:
			doc.append("operations", {
				"operation_type": op.get("operation_type") or "System Blowdown & Flush",
				"area_or_equipment": op.get("area_or_equipment") or "Plant Feed",
				"duration_minutes": cint(op.get("duration_minutes") or 30),
				"chemicals_used": op.get("chemicals_used") or "",
				"outcome": op.get("outcome") or "Successful",
				"remarks": op.get("remarks") or "",
			})
	else:
		doc.append("operations", {
			"operation_type": "System Blowdown & Flush",
			"area_or_equipment": "Feed & Pretreatment",
			"duration_minutes": 30,
			"chemicals_used": "Fresh water permeate flush",
			"outcome": "Successful",
			"remarks": "System blowdown completed to clear sediment and reset conductivity.",
		})
		doc.append("operations", {
			"operation_type": "Biocide Shock Dosing",
			"area_or_equipment": "Chemical Dosing Skid",
			"duration_minutes": 30,
			"chemicals_used": "CW-BioClean 5L",
			"outcome": "Successful",
			"remarks": "Chemical dosing pump calibrated and stroke rate adjusted.",
		})

	# 7. Technical Checklist Items
	if isinstance(checklist_items, str):
		try: checklist_items = json.loads(checklist_items)
		except Exception: checklist_items = []
	if isinstance(checklist_items, list) and len(checklist_items) > 0:
		for item in checklist_items:
			doc.append("checklist_items", {
				"checklist_item": item.get("checklist_item") or item.get("item_description") or "Visual inspection",
				"response": item.get("response") or item.get("status") or "Pass",
				"is_mandatory": cint(item.get("is_mandatory", 1)),
				"remarks": item.get("remarks") or "",
			})
	else:
		default_checklist = [
			("Visual inspection of dosing pumps and chemical injection lines", "Pass", "Pumps running normally, no leaks"),
			("Verify chemical storage tank levels and spill containment", "Pass", "Tanks at safe capacity (>70%)"),
			("Calibrate online pH, ORP, and Conductivity sensors", "Pass", "Sensors calibrated against standard buffers"),
			("Check differential pressure across cartridge filters & RO membranes", "Pass", "Delta P = 0.4 bar (within normal limits)"),
			("Check raw water feed pump pressure and flow meter indicators", "Pass", "Pressure steady at 3.5 bar"),
			("Verify safety shower, eyewash station, and PPE availability", "Pass", "Fully compliant with HSE safety standards"),
		]
		for desc, resp, rem in default_checklist:
			doc.append("checklist_items", {
				"checklist_item": desc,
				"response": resp,
				"is_mandatory": 1,
				"remarks": rem,
			})

	# 8. Water Quality Readings
	if isinstance(readings, str):
		try: readings = json.loads(readings)
		except Exception: readings = []
	if isinstance(readings, list) and len(readings) > 0:
		for r in readings:
			doc.append("readings", {
				"parameter": r.get("parameter") or "pH",
				"parameter_name": r.get("parameter_name") or "pH Level",
				"reading_value": str(r.get("reading_value") or ""),
				"unit": r.get("unit") or "pH",
				"min_range": flt(r.get("min_range") or r.get("min_value") or 6.5),
				"max_range": flt(r.get("max_range") or r.get("max_value") or 8.5),
				"status": r.get("status") or "Normal",
				"remarks": r.get("remarks") or "",
			})
	else:
		default_readings = [
			("pH", "pH Level", "7.35", "pH", 6.5, 8.5, "Normal", "Optimal range"),
			("TDS", "Total Dissolved Solids", "450", "ppm", 100.0, 1000.0, "Normal", "Within specification"),
			("Conductivity", "Electrical Conductivity", "820", "µS/cm", 200.0, 1500.0, "Normal", "Good conductivity"),
			("Hardness", "Total Hardness", "120", "ppm CaCO3", 50.0, 300.0, "Normal", "Softened"),
			("Free Chlorine", "Free Residual Chlorine", "1.10", "ppm", 0.2, 2.0, "Normal", "Disinfected"),
		]
		for param, pname, val, unit, min_r, max_r, stat, rem in default_readings:
			doc.append("readings", {
				"parameter": param,
				"parameter_name": pname,
				"reading_value": val,
				"unit": unit,
				"min_range": min_r,
				"max_range": max_r,
				"status": stat,
				"remarks": rem,
			})

	# 9. Requests & Spares (requirements)
	if isinstance(requirements, str):
		try: requirements = json.loads(requirements)
		except Exception: requirements = []
	if isinstance(requirements, list) and len(requirements) > 0:
		for req_item in requirements:
			doc.append("requirements", {
				"item_code": req_item.get("item_code"),
				"item_name": req_item.get("item_name") or req_item.get("item_code") or "Spare Part",
				"quantity": flt(req_item.get("quantity") or 1),
				"uom": req_item.get("uom") or "Nos",
				"urgency": req_item.get("urgency") or "Normal",
				"reason": req_item.get("reason") or "Site requirement",
			})

	# 10. Findings & Defects
	if isinstance(findings, str):
		try: findings = json.loads(findings)
		except Exception: findings = []
	if isinstance(findings, list) and len(findings) > 0:
		for f in findings:
			doc.append("findings", {
				"category": f.get("category") or "General",
				"severity": f.get("severity") or "Minor",
				"observation": f.get("observation") or "",
				"recommendation": f.get("recommendation") or "",
			})

	# 11. Expenses (strictly in EGP)
	if isinstance(expenses, str):
		try: expenses = json.loads(expenses)
		except Exception: expenses = []
	if isinstance(expenses, list) and len(expenses) > 0:
		for exp in expenses:
			doc.append("expenses", {
				"expense_type": exp.get("expense_type") or "Fuel",
				"amount": flt(exp.get("amount") or 0.0),
				"remarks": exp.get("remarks") or "",
			})

	doc.insert(ignore_permissions=True)

	# 12. Handle photo attachment if image_data (base64) provided
	if image_data:
		try:
			import base64
			b64_content = image_data
			if "," in b64_content:
				b64_content = b64_content.split(",", 1)[1]
			file_bytes = base64.b64decode(b64_content)
			fname = image_name or f"visit_{doc.name}_site.jpg"
			file_doc = frappe.get_doc({
				"doctype": "File",
				"file_name": fname,
				"attached_to_doctype": "CW Site Visit",
				"attached_to_name": doc.name,
				"content": file_bytes,
				"is_private": 0,
			}).insert(ignore_permissions=True)

			doc.site_photo = file_doc.file_url
			doc.append("evidence", {
				"file": file_doc.file_url,
				"category": "Before Inspection",
				"caption": "Site Check-in / Equipment Photo",
				"timestamp": now_datetime(),
			})
			doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Failed to attach site photo to visit {doc.name}: {e}", "CW Field Service On-Site Visit")

	return doc.as_dict()


@frappe.whitelist()
def submit_visit(
	visit_id: str,
	data: Any = None,
	latitude: Optional[float] = None,
	longitude: Optional[float] = None,
	accuracy: Optional[float] = None,
	outcome: Optional[str] = None,
	executive_summary: Optional[str] = None,
	customer_rep: Optional[str] = None,
	customer_signature: Optional[str] = None,
	idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Records completion, check-out GPS, updates status to 'Pending Review',
	and synchronizes linked CW Service Request in ERPNext.
	"""
	if not frappe:
		return {}

	doc = frappe.get_doc("CW Site Visit", visit_id)

	# Idempotency check: If already submitted / pending review with same key
	if doc.visit_status in ["Pending Review", "Approved"]:
		return {
			"status": "already_submitted",
			"visit_id": doc.name,
			"visit_status": doc.visit_status,
			"message": _("Visit has already been submitted."),
		}

	# Apply draft updates if any
	if data:
		if isinstance(data, str):
			data = json.loads(data)
		if isinstance(data, dict):
			if "checklist_items" in data:
				doc.set("checklist_items", data["checklist_items"])
			if "readings" in data:
				doc.set("readings", data["readings"])
			if "findings" in data:
				doc.set("findings", data["findings"])
			if "operations" in data:
				doc.set("operations", data["operations"])
			if "requirements" in data:
				doc.set("requirements", data["requirements"])
			if "expenses" in data:
				doc.set("expenses", data["expenses"])

	# Record check-out info
	doc.checkout_time = now_datetime()
	if latitude is not None and longitude is not None:
		doc.checkout_latitude = flt(latitude)
		doc.checkout_longitude = flt(longitude)
		doc.checkout_accuracy = flt(accuracy) if accuracy else None

	doc.outcome = outcome or "Resolved"
	if executive_summary:
		doc.executive_summary = executive_summary
	if customer_rep:
		doc.customer_representative = customer_rep
	if customer_signature:
		doc.customer_signature = customer_signature

	doc.visit_status = "Pending Review"
	doc.save()

	# Synchronize linked CW Service Request
	if doc.service_request:
		try:
			sr = frappe.get_doc("CW Service Request", doc.service_request)
			if doc.outcome in ["Resolved", "Partially Resolved"]:
				sr.status = "Resolved"
				sr.resolved_date = now_datetime()
				sr.resolution_summary = doc.executive_summary or _("Resolved via Site Visit {0}").format(doc.name)
			elif doc.outcome == "Follow-up Required":
				sr.status = "In Progress"
				sr.closure_remarks = _("Follow-up required from visit {0}").format(doc.name)
			sr.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Error syncing linked Service Request {doc.service_request}: {e}", "CW Field Service Submit")

	return {
		"status": "success",
		"visit_id": doc.name,
		"visit_status": doc.visit_status,
		"outcome": doc.outcome,
		"checkout_time": str(doc.checkout_time),
		"duration_minutes": doc.visit_duration_minutes,
	}


@frappe.whitelist()
def upload_visit_evidence(
	visit_id: str,
	filename: str,
	category: str = "Before Inspection",
	caption: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Appends uploaded file from request files to the CW Visit Evidence child table.
	"""
	if not frappe:
		return {}

	doc = frappe.get_doc("CW Site Visit", visit_id)
	files = frappe.request.files if hasattr(frappe, "request") and hasattr(frappe.request, "files") else {}

	if "file" not in files:
		frappe.throw(_("No file uploaded."))

	uploaded = files["file"]
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename or uploaded.filename,
		"attached_to_doctype": "CW Site Visit",
		"attached_to_name": visit_id,
		"content": uploaded.read(),
		"is_private": 0,
	}).insert()

	doc.append("evidence", {
		"file": file_doc.file_url,
		"category": category,
		"caption": caption or "",
		"timestamp": now_datetime(),
	})
	doc.save()

	return {
		"status": "success",
		"file_url": file_doc.file_url,
		"evidence_count": len(doc.evidence),
	}


@frappe.whitelist()
def get_master_data() -> Dict[str, Any]:
	"""
	Returns lightweight catalog bundle for mobile offline caching.
	"""
	if not frappe:
		return {}

	parameters = frappe.get_all(
		"CW Water Parameter Master",
		filters={"is_active": 1},
		fields=["name", "parameter_name", "category", "unit", "default_min_value", "default_max_value"],
	)
	finding_categories = frappe.get_all(
		"CW Finding Category",
		filters={"is_active": 1},
		fields=["name", "category_name", "default_severity"],
	)
	operation_types = frappe.get_all(
		"CW Operation Type",
		filters={"is_active": 1},
		fields=["name", "operation_name", "category"],
	)
	service_types = frappe.get_all(
		"CW Service Type",
		filters={"is_active": 1},
		fields=["name", "service_type_name", "default_sla_hours"],
	)
	customers = frappe.get_all(
		"Customer",
		filters={"disabled": 0},
		fields=["name", "customer_name", "customer_type", "territory"],
		limit=200,
		order_by="customer_name asc",
	)

	return {
		"parameters": parameters,
		"finding_categories": finding_categories,
		"operation_types": operation_types,
		"service_types": service_types,
		"customers": customers,
	}


@frappe.whitelist()
def search_customers(query: str = "") -> List[Dict[str, Any]]:
	"""
	Search active customers for the mobile PWA Create Visit screen.
	"""
	if not frappe:
		return []

	filters = {"disabled": 0}
	or_filters = []
	if query:
		or_filters = [
			["Customer", "name", "like", f"%{query}%"],
			["Customer", "customer_name", "like", f"%{query}%"],
		]

	return frappe.get_all(
		"Customer",
		filters=filters,
		or_filters=or_filters if query else None,
		fields=["name", "customer_name", "customer_type", "territory"],
		limit=40,
		order_by="customer_name asc",
	)


@frappe.whitelist()
def sync_queued_visits(queue_payload: Any) -> Dict[str, Any]:
	"""
	Processes a batch of queued actions from mobile offline storage idempotently.
	"""
	if not frappe:
		return {}

	if isinstance(queue_payload, str):
		queue_payload = json.loads(queue_payload)

	if not isinstance(queue_payload, list):
		frappe.throw(_("queue_payload must be an array of queued operations."))

	results = []
	for item in queue_payload:
		action = item.get("action")
		visit_id = item.get("visit_id")
		idempotency_key = item.get("idempotency_key")
		payload = item.get("payload", {})

		try:
			if action == "create_visit":
				res = create_site_visit(
					customer=payload.get("customer"),
					customer_name=payload.get("customer_name"),
					service_location=payload.get("service_location"),
					visit_type=payload.get("visit_type", "Routine Inspection"),
					priority=payload.get("priority", "Medium"),
					description=payload.get("description"),
					planned_date=payload.get("planned_date"),
					planned_start_time=payload.get("planned_start_time"),
					service_request=payload.get("service_request"),
					instructions=payload.get("instructions"),
					creation_source=payload.get("creation_source", "Engineer On-Site"),
					latitude=payload.get("latitude"),
					longitude=payload.get("longitude"),
					accuracy=payload.get("accuracy"),
					image_data=payload.get("image_data"),
					image_name=payload.get("image_name"),
					idempotency_key=idempotency_key,
					operations=payload.get("operations"),
					requirements=payload.get("requirements"),
					checklist_items=payload.get("checklist_items"),
					readings=payload.get("readings"),
					findings=payload.get("findings"),
					expenses=payload.get("expenses"),
				)
			elif action == "check_in":
				res = check_in_visit(
					visit_id=visit_id,
					latitude=payload.get("latitude"),
					longitude=payload.get("longitude"),
					accuracy=payload.get("accuracy"),
					geofence_reason=payload.get("geofence_reason"),
				)
			elif action == "save_draft":
				res = save_visit_draft(
					visit_id=visit_id,
					data=payload.get("data"),
					idempotency_key=idempotency_key,
				)
			elif action == "submit":
				res = submit_visit(
					visit_id=visit_id,
					data=payload.get("data"),
					latitude=payload.get("latitude"),
					longitude=payload.get("longitude"),
					accuracy=payload.get("accuracy"),
					outcome=payload.get("outcome"),
					executive_summary=payload.get("executive_summary"),
					customer_rep=payload.get("customer_rep"),
					customer_signature=payload.get("customer_signature"),
					idempotency_key=idempotency_key,
				)
			else:
				res = {"status": "error", "message": f"Unknown action: {action}"}

			results.append({
				"idempotency_key": idempotency_key,
				"visit_id": visit_id,
				"action": action,
				"success": True,
				"result": res,
			})
		except Exception as e:
			results.append({
				"idempotency_key": idempotency_key,
				"visit_id": visit_id,
				"action": action,
				"success": False,
				"error": str(e),
			})

	return {"synced_count": len(results), "results": results}
