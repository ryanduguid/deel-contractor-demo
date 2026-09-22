from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Importing oa_client only reads environment variables; it makes no requests.
from oa_client import _MOCK_SKILL


def bundled_skill():
    return next(iter(_MOCK_SKILL.values()))

import contractor_check


class ContractorThresholdTests(unittest.TestCase):
    def result(self, year, amount, form="W-9", skill=None):
        return contractor_check.check({"us_person": True, "country": "US", "full_time_exclusive": False,
            "payment_year": year, "ytd_paid": amount, "form_on_file": form}, skill or bundled_skill())

    def test_year_and_inclusive_boundaries(self):
        for year, amount, expected in [(2025, 599.99, False), (2025, 600, True),
                                      (2026, 1000, False), (2026, 1999.99, False), (2026, 2000, True)]:
            with self.subTest(year=year, amount=amount):
                self.assertEqual("threshold met" in self.result(year, amount)["headline"], expected)

    def test_missing_document_is_separate(self):
        result = self.result(2026, 1000, None)
        self.assertEqual(result["status"], "warn")
        self.assertIn("Below the general", result["headline"])
        self.assertIn("Collect a W-9", result["detail"])

    def test_w9_does_not_remove_reporting(self):
        self.assertIn("threshold met", self.result(2026, 2000)["headline"])

    def test_unknown_year_or_undated_rule_needs_confirmation(self):
        for year in (None, 2027):
            self.assertIn("Confirm", self.result(year, 30000)["headline"])
        self.assertIn("Confirm", self.result(2026, 1000, skill={"rules": {"form_1099_threshold": 600}})["headline"])
