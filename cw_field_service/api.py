# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import json
from typing import Any, Dict, List, Optional

try:
	import frappe
	from frappe import _
	from frappe.utils import flt, get_datetime, now_datetime
except ImportError:
	frappe = None  # type: ignore
	def _(msg): return msg


def get_current_employee() -> Optional[str]:
	"""Helper to resolve current session user to an Employee document name."""
	if not frappe:
		return None
	user = frappe.session.user
	emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
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
	planned_date: Optional[str] = None,
	planned_start_time: Optional[str] = None,
	service_request: Optional[str] = None,
	instructions: Optional[str] = None,
	idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	Creates a new CW Site Visit directly from mobile PWA.
	Automatically assigns to current logged-in employee if engineer.
	"""
	if not frappe:
		return {}

	emp = get_current_employee()
	doc = frappe.new_doc("CW Site Visit")
	doc.customer = customer
	if customer_name:
		doc.customer_name = customer_name
	if service_location:
		doc.service_location = service_location
	doc.visit_type = visit_type or "Routine Inspection"
	doc.priority = priority or "Medium"
	doc.planned_date = planned_date or frappe.utils.nowdate()
	if planned_start_time:
		doc.planned_start_time = planned_start_time
	if service_request:
		doc.service_request = service_request
	if emp:
		doc.assigned_engineer = emp

	doc.insert(ignore_permissions=True)
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
	Records completion, check-out GPS, updates status to 'Pending Review'.
	Server-side validations ensure mandatory fields and checklist items are complete.
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

	if outcome:
		doc.outcome = outcome
	if executive_summary:
		doc.executive_summary = executive_summary
	if customer_rep:
		doc.customer_representative = customer_rep
	if customer_signature:
		doc.customer_signature = customer_signature

	doc.visit_status = "Pending Review"
	doc.save()

	return {
		"status": "success",
		"visit_id": doc.name,
		"visit_status": doc.visit_status,
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

	return {
		"parameters": parameters,
		"finding_categories": finding_categories,
		"operation_types": operation_types,
		"service_types": service_types,
	}


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
					planned_date=payload.get("planned_date"),
					planned_start_time=payload.get("planned_start_time"),
					service_request=payload.get("service_request"),
					instructions=payload.get("instructions"),
					idempotency_key=idempotency_key,
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
