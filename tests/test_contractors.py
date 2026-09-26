import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import os
import unittest
from unittest.mock import patch

os.environ["OA_MCP_TOKEN"] = ""
os.environ["OA_MCP_URL"] = "https://example.invalid"
os.environ["DEEL_API_TOKEN"] = ""

import contractor_check
import deel_client
import pipeline
from oa_client import OAClient


class ContractorTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.skill = copy.deepcopy(OAClient(token=None).get_skill("us-contractor-payments"))
        self.contractor = {"name": "Example contractor", "country": "US", "us_person": True,
                           "payment_year": 2026, "ytd_paid": "2000", "currency": "USD",
                           "payment_basis": "eligible_nonemployee_services", "form_on_file": None,
                           "services_in_us": True, "full_time_exclusive": False}

    def result(self, **changes):
        return contractor_check.check(deel_client.normalize({**self.contractor, **changes}), self.skill)

    def test_payment_year_boundaries(self):
        for year, paid, met in ((2025, "599.99", False), (2025, "600", True), (2025, "600.01", True),
                                (2026, "1999.99", False), (2026, "2000", True), (2026, "2000.01", True)):
            with self.subTest(year=year, paid=paid):
                self.assertIs(self.result(payment_year=year, ytd_paid=paid)["amount_threshold_met"], met)

    def test_low_payment_does_not_invent_a_form_or_filing(self):
        result = self.result(ytd_paid="500")
        text = result["headline"] + " " + result["detail"]
        self.assertNotIn("W-9 on file", text)
        self.assertNotIn("1099 will issue", text)

    def test_us_work_is_flagged_despite_foreign_form(self):
        result = self.result(us_person=False, country="CA", form_on_file="W-8BEN")
        self.assertTrue(any(row["category"] == "services" and row["status"] == "review"
                            for row in result["findings"]))

    def test_relationship_review_does_not_hide_other_findings(self):
        result = self.result(us_person=False, full_time_exclusive=True)
        categories = {row["category"] for row in result["findings"] if row["status"] == "review"}
        self.assertTrue({"relationship", "documentation", "services"} <= categories)
        self.assertNotIn("looks like an employee", result["detail"])

    def test_missing_year_amount_and_status_remain_unknown(self):
        for changes in ({"payment_year": None}, {"payment_year": 2027}, {"ytd_paid": None},
                        {"us_person": None}, {"currency": None}, {"payment_basis": None}):
            with self.subTest(changes=changes):
                result = self.result(**changes)
                self.assertFalse(result["complete"])
                self.assertIsNone(result["amount_threshold_met"])
        self.assertIs(self.result(ytd_paid=0)["amount_threshold_met"], False)

    def test_boolean_strings_and_numeric_booleans_are_invalid(self):
        for field in ("us_person", "services_in_us", "full_time_exclusive"):
            for value in ("false", "true", 0, 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.result(**{field: value})

    def test_invalid_money_and_year(self):
        for value in (True, "NaN", "Infinity", -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.result(ytd_paid=value)
        for value in (True, "2026", 2026.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.result(payment_year=value)

    def test_country_does_not_override_us_person_status(self):
        self.assertIs(self.result(country="CA")["amount_threshold_met"], True)

    def test_unsupported_payment_rules_do_not_hide_other_findings(self):
        self.skill["rules"] = {}
        result = self.result(us_person=False, services_in_us=True, full_time_exclusive=True)
        self.assertFalse(result["complete"])
        review = {row["category"] for row in result["findings"] if row["status"] == "review"}
        self.assertEqual(review, {"documentation", "services", "relationship"})

    def test_blank_form_does_not_count_as_documentation(self):
        result = self.result(us_person=False, form_on_file="   ")
        finding = next(row for row in result["findings"] if row["category"] == "documentation")
        self.assertEqual(finding["status"], "review")
        self.assertIn("No foreign-person form", finding["text"])

    def test_pipeline_preserves_each_finding_and_continues_after_invalid_input(self):
        rows = [{**self.contractor, "us_person": "false"},
                {**self.contractor, "name": "Unknown amount", "ytd_paid": None},
                {**self.contractor, "name": "Independent reviews", "us_person": False,
                 "full_time_exclusive": True},
                {**self.contractor, "name": "Known zero", "ytd_paid": 0}]
        output = io.StringIO()
        with patch.object(deel_client, "extract", return_value=rows), contextlib.redirect_stdout(output):
            self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
        text = output.getvalue()
        for expected in ("invalid input", "unknown amount", "Independent reviews", "Known zero", "0.00",
                         "documentation:", "services:", "relationship:", "unverified sample rules"):
            self.assertIn(expected, text)
        self.assertNotIn("signed off", text)

    def test_default_cli_selects_offline_mode_explicitly(self):
        with patch.object(pipeline, "OAClient", return_value=OAClient(token=None)) as constructor:
            with patch.object(pipeline, "run", return_value=True), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline.main(["pipeline.py"]), 0)
        constructor.assert_called_once_with(token=None)

    def test_invalid_amount_keeps_three_independent_findings_for_the_same_record(self):
        record = {**self.contractor, "us_person": False, "ytd_paid": -1,
                  "full_time_exclusive": True, "services_in_us": True, "form_on_file": None}
        output = io.StringIO()
        with patch.object(deel_client, "extract", return_value=[record]), contextlib.redirect_stdout(output):
            self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
        for text in ("invalid input", "ytd_paid", "No foreign-person form", "US services are reported",
                     "Full-time and exclusive work"):
            self.assertIn(text, output.getvalue())

    def test_invalid_relationship_flag_keeps_the_amount_comparison(self):
        output = io.StringIO()
        record = {**self.contractor, "full_time_exclusive": "false"}
        with patch.object(deel_client, "extract", return_value=[record]), contextlib.redirect_stdout(output):
            self.assertFalse(pipeline.run("unused.json", OAClient(token=None)))
        self.assertIn("invalid input", output.getvalue())
        self.assertIn("meets the inclusive $2,000 threshold", output.getvalue())

    def test_extreme_json_number_keeps_independent_findings_and_later_records(self):
        for token in ("1e999999999999999999999", "1" * 5000):
            with self.subTest(kind="exponent" if "e" in token else "integer"):
                row = {**self.contractor, "us_person": False, "full_time_exclusive": True,
                       "ytd_paid": "REPLACE_NUMERIC_TOKEN"}
                payload = json.dumps([row, {**self.contractor, "name": "Later record"}])
                payload = payload.replace('"REPLACE_NUMERIC_TOKEN"', token)
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "amount.json"
                    source.write_text(payload, encoding="utf-8")
                    output, error = io.StringIO(), io.StringIO()
                    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                        self.assertEqual(pipeline.main(["pipeline.py", str(source)]), 2)
                for expected in ("ytd_paid", "unknown amount", "No foreign-person form",
                                 "US services are reported", "Full-time and exclusive work", "Later record"):
                    self.assertIn(expected, output.getvalue())
                self.assertEqual(error.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
