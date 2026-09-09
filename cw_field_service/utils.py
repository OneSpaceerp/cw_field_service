# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import math
from typing import Any, Dict, Optional, Tuple

try:
	import frappe
	from frappe.utils import get_datetime, now_datetime
except ImportError:
	frappe = None  # type: ignore


def calculate_haversine_distance(
	lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
	"""
	Calculates the great circle distance between two GPS coordinates in meters.
	Formula: Haversine
	"""
	earth_radius_m = 6371000.0  # Earth radius in meters

	phi1 = math.radians(lat1)
	phi2 = math.radians(lat2)
	delta_phi = math.radians(lat2 - lat1)
	delta_lambda = math.radians(lon2 - lon1)

	a = (
		math.sin(delta_phi / 2.0) ** 2
		+ math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
	)
	c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

	return earth_radius_m * c


def evaluate_geofence(
	current_lat: Optional[float],
	current_lon: Optional[float],
	site_lat: Optional[float],
	site_lon: Optional[float],
	radius_meters: float = 200.0,
	warning_buffer_meters: float = 300.0,
) -> Tuple[str, Optional[float]]:
	"""
	Evaluates geofence status based on distance to registered site coordinates.
	Returns (status, distance_meters).
	Statuses:
	- 'Verified': Distance <= radius_meters
	- 'Warning': radius_meters < Distance <= (radius_meters + warning_buffer_meters)
	- 'Exception': Distance > (radius_meters + warning_buffer_meters) or missing coordinates
	"""
	if current_lat is None or current_lon is None:
		return ("Exception", None)
	if site_lat is None or site_lon is None:
		return ("Warning", None)

	dist = calculate_haversine_distance(current_lat, current_lon, site_lat, site_lon)

	if dist <= radius_meters:
		return ("Verified", round(dist, 2))
	elif dist <= (radius_meters + warning_buffer_meters):
		return ("Warning", round(dist, 2))
	else:
		return ("Exception", round(dist, 2))


def check_overdue_service_requests():
	"""
	Scheduled task running daily to detect service requests breaching SLA response due dates.
	"""
	if not frappe:
		return

	now = now_datetime()
	overdue_requests = frappe.get_all(
		"CW Service Request",
		filters={
			"status": ["in", ["Open", "Scheduled"]],
			"response_due_date": ["<", now],
		},
		fields=["name", "customer", "priority", "response_due_date", "assigned_supervisor"],
	)

	for req in overdue_requests:
		frappe.logger("cw_field_service").warning(
			f"Service Request {req.name} for customer {req.customer} is overdue! Due date: {req.response_due_date}"
		)
