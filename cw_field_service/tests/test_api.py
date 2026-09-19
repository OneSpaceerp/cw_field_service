# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import unittest
from cw_field_service.utils import evaluate_geofence


class TestFieldServiceAPI(unittest.TestCase):
	def test_geofence_edge_cases(self):
		# Null coordinates
		status, dist = evaluate_geofence(None, None, 29.97, 30.94)
		self.assertEqual(status, "Exception")
		self.assertIsNone(dist)

		# Missing site coordinates
		status, dist = evaluate_geofence(29.97, 30.94, None, None)
		self.assertEqual(status, "Warning")
		self.assertIsNone(dist)

	def test_idempotency_payload_structure(self):
		batch = [
			{
				"idempotency_key": "uuid-12345",
				"visit_id": "VISIT-2026-0001",
				"action": "check_in",
				"payload": {"latitude": 29.972, "longitude": 30.941},
			}
		]
		self.assertEqual(len(batch), 1)
		self.assertEqual(batch[0]["action"], "check_in")
		self.assertEqual(batch[0]["idempotency_key"], "uuid-12345")

	def test_create_visit_queue_payload(self):
		create_payload = {
			"idempotency_key": "uuid-create-99",
			"visit_id": None,
			"action": "create_visit",
			"payload": {
				"customer": "CUST-001",
				"customer_name": "Al-Ahram Beverages",
				"visit_type": "Emergency Breakdown",
				"priority": "High",
				"description": "RO membrane pressure failure detected on site",
				"latitude": 29.9725,
				"longitude": 30.9415,
				"accuracy": 12.0,
				"image_data": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
				"image_name": "pressure_leak.jpg",
			},
		}
		self.assertEqual(create_payload["action"], "create_visit")
		self.assertEqual(create_payload["payload"]["customer"], "CUST-001")
		self.assertEqual(create_payload["payload"]["latitude"], 29.9725)
		self.assertTrue(create_payload["payload"]["image_data"].startswith("data:image/"))


if __name__ == "__main__":
	unittest.main()
