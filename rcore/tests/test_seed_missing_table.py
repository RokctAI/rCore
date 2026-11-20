# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
# License: AGPL-3.0-only

"""seed_generic must not query a doctype whose table is missing (Postgres
aborts the transaction) and must roll back to a savepoint on a failed record.
Runs without a bench: frappe is replaced by a stub."""

import sys
import types
import unittest
from unittest import mock


def _load_seed():
    frappe = types.ModuleType("frappe")
    frappe.db = mock.MagicMock()
    frappe.get_doc = mock.MagicMock()
    utils = types.ModuleType("frappe.utils")
    utils.get_bench_path = lambda: "."
    frappe.utils = utils
    with mock.patch.dict(sys.modules, {"frappe": frappe, "frappe.utils": utils}):
        sys.modules.pop("rcore.seed", None)
        import rcore.seed as seed
    return seed, frappe


class TestSeedGeneric(unittest.TestCase):
    def setUp(self):
        self.seed, self.frappe = _load_seed()
        self.seeder = self.seed.JSONSeeder.__new__(self.seed.JSONSeeder)
        self.seeder.load_json = lambda f: [{"id": 15, "name": "x"}]

    def test_missing_table_is_skipped_without_queries(self):
        self.frappe.db.table_exists.return_value = False
        self.seeder.seed_generic("ads_packages.json", "Ads Package")
        self.frappe.db.exists.assert_not_called()
        self.frappe.db.savepoint.assert_not_called()
        self.frappe.get_doc.assert_not_called()

    def test_failed_record_rolls_back_to_savepoint(self):
        self.frappe.db.table_exists.return_value = True
        self.frappe.db.exists.side_effect = RuntimeError("boom")
        self.seeder.seed_generic("ads_packages.json", "Ads Package")
        self.frappe.db.savepoint.assert_called_once_with("seed_generic_item")
        self.frappe.db.rollback.assert_called_once_with(save_point="seed_generic_item")

    def test_existing_table_inserts(self):
        self.frappe.db.table_exists.return_value = True
        self.frappe.db.exists.return_value = False
        self.seeder.seed_generic("ads_packages.json", "Ads Package")
        self.frappe.get_doc.assert_called_once()
        self.frappe.db.rollback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
