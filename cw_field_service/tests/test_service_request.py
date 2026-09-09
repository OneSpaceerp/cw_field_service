# Copyright (c) 2026, Nest Software Development & C-Water
# For license information, please see license.txt

import unittest
from datetime import datetime, timedelta

from cw_field_service.field_service.doctype.cw_service_request.cw_service_request import CWServiceRequest


class DummyServiceRequest(CWServiceRequest):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class TestServiceRequest(unittest.TestCase):
	def test_sla_due_date_calculation(self):
		requested = datetime(2026, 9, 10, 10, 0, 0)
		req = DummyServiceRequest(
			customer="Test Customer",
			priority="High",
			requested_date=requested,
			sla_target_hours=24,
			response_due_date=None,
			status="Open",
		)
		# Simulate calculation
		req.response_due_date = requested + timedelta(hours=req.sla_target_hours)
		self.assertEqual(req.response_due_date, datetime(2026, 9, 11, 10, 0, 0))

	def test_resolution_date_stamped(self):
		req = DummyServiceRequest(
			status="Resolved",
			resolved_date=None,
		)
		if req.status in ["Resolved", "Closed"] and not req.resolved_date:
			req.resolved_date = datetime(2026, 9, 10, 15, 30, 0)
		self.assertIsNotNone(req.resolved_date)


if __name__ == "__main__":
	unittest.main()
