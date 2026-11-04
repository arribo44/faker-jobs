"""
Tests for scripts/build_data.py: the packaged data must be in sync with DATAS/.
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_data  # noqa: E402


# DATAS/ is not published (see .gitignore): these tests only run where the
# source CSV files are available.
@unittest.skipUnless(os.path.isdir(build_data.DATAS_DIR), "DATAS/ source files not available")
class TestBuildData(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_data.build_data()

    def test_packaged_json_is_up_to_date(self):
        with open(build_data.OUTPUT_PATH, encoding="utf-8") as f:
            packaged = json.load(f)
        self.assertEqual(packaged, json.loads(json.dumps(self.data)),
                         msg="faker_jobs/data/jobs_data.json is stale: re-run scripts/build_data.py")

    def test_every_role_has_text_and_popularity(self):
        self.assertEqual(len(self.data["roles"]), 376)
        for role in self.data["roles"]:
            self.assertTrue(role["description"] and role["skills"] and role["responsibilities"], msg=role["role"])
            self.assertGreater(role["posting_count"], 0, msg=role["role"])
            self.assertIn(role["job_title"], self.data["job_titles"])

    def test_multiple_locations_per_country(self):
        # Now we have multiple cities per country
        countries = [location["country"] for location in self.data["locations"]]
        unique_countries = set(countries)
        # Verify we have locations for multiple countries
        self.assertGreater(len(unique_countries), 1)
        # Verify total locations is greater than unique countries (multiple cities per country)
        self.assertGreater(len(countries), len(unique_countries))
        # Verify each location has required fields
        for location in self.data["locations"]:
            self.assertIn("city", location)
            self.assertIn("country", location)
            self.assertIn("latitude", location)
            self.assertIn("longitude", location)

    def test_unique_company_names(self):
        names = [company["company"].lower() for company in self.data["companies"]]
        self.assertEqual(len(names), len(set(names)))

    def test_ranges_are_ordered(self):
        for field, (low, high) in self.data["ranges"].items():
            self.assertLessEqual(low, high, msg=field)
        self.assertLess(self.data["ranges"]["experience_min"][1], self.data["ranges"]["experience_max"][0])
        self.assertLess(self.data["ranges"]["salary_min_k"][1], self.data["ranges"]["salary_max_k"][0])

    def test_enough_benefits_per_posting(self):
        self.assertGreaterEqual(len(self.data["benefits"]), self.data["meta"]["benefits_per_posting"])


if __name__ == "__main__":
    unittest.main()
