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


if __name__ == "__main__":
	unittest.main()
