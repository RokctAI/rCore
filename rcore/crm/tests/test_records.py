# Copyright (c) 2026 RokctAI
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# See license.txt

"""Frappe-free unit tests for the pure CRM helpers in src/crm/core/records.py.

These run with plain python (no Frappe server): the module under test is
loaded by file path because the composed package namespace (rcore.crm...)
only exists after compose_backend.py has poured the SDK into a host app.
"""

import importlib.util
import os
import unittest

_RECORDS_PATH = os.path.join(
	os.path.dirname(__file__), os.pardir, "crm", "core", "records.py"
)
_spec = importlib.util.spec_from_file_location("crm_core_records", _RECORDS_PATH)
records = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(records)


class TestBuildFullName(unittest.TestCase):
	def test_all_parts(self):
		self.assertEqual(
			records.build_full_name("Mr", "John", "Ronald", "Doe"), "Mr John Ronald Doe"
		)

	def test_skips_empty_parts(self):
		self.assertEqual(records.build_full_name(None, "John", "", "Doe"), "John Doe")

	def test_first_name_only(self):
		self.assertEqual(records.build_full_name(first_name="Cher"), "Cher")


class TestDeriveLeadName(unittest.TestCase):
	def test_existing_lead_name_wins(self):
		self.assertEqual(records.derive_lead_name("Jane Doe", "Acme", "j@x.com"), "Jane Doe")

	def test_organization_fallback(self):
		self.assertEqual(records.derive_lead_name(None, "Acme", "j@x.com"), "Acme")

	def test_email_local_part_fallback(self):
		self.assertEqual(records.derive_lead_name(None, None, "jane.doe@example.com"), "jane.doe")

	def test_unnamed_placeholder(self):
		self.assertEqual(records.derive_lead_name(None, None, None), "Unnamed Lead")


class TestResolvePrimaryContactDetails(unittest.TestCase):
	def test_no_contacts(self):
		self.assertEqual(records.resolve_primary_contact_details([]), ("", "", ""))

	def test_no_primary(self):
		contacts = [{"is_primary": 0, "email": "a@x.com"}]
		self.assertEqual(records.resolve_primary_contact_details(contacts), ("", "", ""))

	def test_primary_details_are_stripped(self):
		contacts = [
			{"is_primary": 0, "email": "other@x.com"},
			{
				"is_primary": 1,
				"email": " jane@x.com ",
				"mobile_no": "123 ",
				"phone": None,
			},
		]
		self.assertEqual(
			records.resolve_primary_contact_details(contacts), ("jane@x.com", "123", "")
		)

	def test_multiple_primaries_raise(self):
		contacts = [{"is_primary": 1}, {"is_primary": 1}]
		with self.assertRaises(ValueError):
			records.resolve_primary_contact_details(contacts)


class TestMarkPrimaryContact(unittest.TestCase):
	def test_empty(self):
		self.assertIsNone(records.mark_primary_contact([]))

	def test_single_contact_is_implicit_primary(self):
		self.assertEqual(records.mark_primary_contact([{"contact": "C-1"}]), 0)

	def test_multiple_without_explicit_choice(self):
		rows = [{"contact": "C-1"}, {"contact": "C-2"}]
		self.assertIsNone(records.mark_primary_contact(rows))

	def test_explicit_choice(self):
		rows = [{"contact": "C-1"}, {"contact": "C-2"}]
		self.assertEqual(records.mark_primary_contact(rows, "C-2"), 1)

	def test_explicit_choice_not_found(self):
		rows = [{"contact": "C-1"}]
		self.assertIsNone(records.mark_primary_contact(rows, "C-9"))


class TestDurations(unittest.TestCase):
	def test_get_duration_seconds_from_strings(self):
		self.assertEqual(
			records.get_duration_seconds("2026-01-01T00:00:00", "2026-01-01T01:30:00"),
			5400.0,
		)

	def test_seconds_to_duration_zero(self):
		self.assertEqual(records.seconds_to_duration(0), "0s")
		self.assertEqual(records.seconds_to_duration(None), "0s")

	def test_seconds_to_duration_compact_formats(self):
		self.assertEqual(records.seconds_to_duration(3600), "1h")
		self.assertEqual(records.seconds_to_duration(60), "1m")
		self.assertEqual(records.seconds_to_duration(1), "1s")
		self.assertEqual(records.seconds_to_duration(3660), "1h 1m")
		self.assertEqual(records.seconds_to_duration(3601), "1h 1s")
		self.assertEqual(records.seconds_to_duration(61), "1m 1s")
		self.assertEqual(records.seconds_to_duration(3661), "1h 1m 1s")


if __name__ == "__main__":
	unittest.main()
