# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import unittest
from datetime import datetime

from cw_field_service.field_service.doctype.cw_site_visit.cw_site_visit import CWSiteVisit
from cw_field_service.utils import calculate_haversine_distance, evaluate_geofence


class DummySiteVisit(CWSiteVisit):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class TestSiteVisit(unittest.TestCase):
	def test_haversine_distance_accurate(self):
		# Coordinates for C-Water 6th of October site vs nearby coordinate (~111 meters away)
		lat1, lon1 = 29.9720, 30.9410
		lat2, lon2 = 29.9730, 30.9410  # ~111 meters north
		dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
		self.assertAlmostEqual(dist, 111.2, delta=5.0)

	def test_geofence_evaluation_verified(self):
		# Within 200m radius
		status, dist = evaluate_geofence(29.9722, 30.9410, 29.9720, 30.9410, radius_meters=200.0)
		self.assertEqual(status, "Verified")
		self.assertLessEqual(dist, 200.0)

	def test_geofence_evaluation_warning(self):
		# Distance is ~333m (between 200m and 500m)
		status, dist = evaluate_geofence(29.9750, 30.9410, 29.9720, 30.9410, radius_meters=200.0, warning_buffer_meters=300.0)
		self.assertEqual(status, "Warning")

	def test_geofence_evaluation_exception(self):
		# Distance > 500m away
		status, dist = evaluate_geofence(29.9900, 30.9410, 29.9720, 30.9410, radius_meters=200.0)
		self.assertEqual(status, "Exception")

	def test_duration_calculation(self):
		visit = DummySiteVisit(
			checkin_time=datetime(2026, 9, 10, 9, 0, 0),
			checkout_time=datetime(2026, 9, 10, 10, 45, 0),
			visit_duration_minutes=None,
		)
		visit.calculate_duration()
		self.assertEqual(visit.visit_duration_minutes, 105.0)

	def test_reading_range_evaluation(self):
		class DummyReading:
			def __init__(self, reading_value, min_range, max_range, status="Normal"):
				self.reading_value = reading_value
				self.min_range = min_range
				self.max_range = max_range
				self.status = status

		visit = DummySiteVisit(
			readings=[
				DummyReading("7.2", 6.5, 8.5),   # In range
				DummyReading("9.5", 6.5, 8.5),   # Out of range (high)
				DummyReading("4.0", 6.5, 8.5),   # Out of range (low)
			]
		)
		visit.validate_readings_ranges()
		self.assertEqual(visit.readings[0].status, "Normal")
		self.assertEqual(visit.readings[1].status, "Warning")
		self.assertEqual(visit.readings[2].status, "Warning")

	def test_onsite_visit_geofence_verified(self):
		visit = DummySiteVisit(
			creation_source="Engineer On-Site",
			geofence_status="Verified",
			checkin_latitude=29.9720,
			checkin_longitude=30.9410,
			service_location=None,
		)
		# Validate geofence should not fail or raise when on-site and verified
		visit.validate_geofence_and_distance()
		self.assertEqual(visit.geofence_status, "Verified")


if __name__ == "__main__":
	unittest.main()
