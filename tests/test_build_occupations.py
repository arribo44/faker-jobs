"""
Tests for scripts/build_occupations.py: the packaged occupation data must be
in sync with the ROME and ESCO sources in DATAS/.
"""
import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_occupations  # noqa: E402
import fetch_esco  # noqa: E402

SOURCES = (build_occupations.ROME_PATH, fetch_esco.MAPPING_PATH, fetch_esco.CACHE_PATH)


# DATAS/ is not published: these tests only run where the sources (and
# openpyxl, a dev dependency) are available.
@unittest.skipUnless(all(map(os.path.exists, SOURCES)) and importlib.util.find_spec("openpyxl"),
                     "ROME/ESCO source files or openpyxl not available")
class TestBuildOccupations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_occupations.build_occupations()

    def test_packaged_json_is_up_to_date(self):
        for locale, data in self.data.items():
            with open(build_occupations.output_path(locale), encoding="utf-8") as f:
                packaged = json.load(f)
            self.assertEqual(packaged, json.loads(json.dumps(data)),
                             msg=f"occupations_{locale}.json is stale: re-run scripts/build_occupations.py")

    def test_every_esco_occupation_is_cached(self):
        mapped = {uri for uri, *_ in fetch_esco.read_mapping()}
        with open(fetch_esco.CACHE_PATH, encoding="utf-8") as f:
            self.assertTrue(mapped <= set(json.load(f)))

    def test_every_soft_skill_has_an_english_label(self):
        _sectors, jobs = build_occupations.load_rome(build_occupations.read_rome())
        used = {skill for job in jobs.values() for skill in job["soft_skills"]}
        self.assertEqual(used, set(build_occupations.SOFT_SKILLS_EN))


if __name__ == "__main__":
    unittest.main()
