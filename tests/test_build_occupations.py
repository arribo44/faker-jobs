"""
Tests for scripts/build_occupations.py: the packaged occupation data must be
in sync with the ROME and ESCO sources in DATAS/.
"""
import gzip
import importlib.util
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_occupations  # noqa: E402
import fetch_esco  # noqa: E402

SOURCES = (build_occupations.ROME_PATH, build_occupations.BMO_PATH, build_occupations.FAP_ROME_PATH,
           build_occupations.NAF_PATH,
           fetch_esco.MAPPING_PATH,
           *map(fetch_esco.cache_path, fetch_esco.LANGUAGES))


# DATAS/ is not published: these tests only run where the sources (and
# openpyxl and xlrd, dev dependencies) are available.
@unittest.skipUnless(all(map(os.path.exists, SOURCES))
                     and all(map(importlib.util.find_spec, ("openpyxl", "xlrd"))),
                     "ROME/ESCO/BMO/NAF source files, openpyxl or xlrd not available")
class TestBuildOccupations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build_occupations.build_occupations()

    def test_packaged_json_is_up_to_date(self):
        for locale, data in self.data.items():
            with gzip.open(build_occupations.output_path(locale), "rt", encoding="utf-8") as f:
                packaged = json.load(f)
            self.assertEqual(packaged, json.loads(json.dumps(data)),
                             msg=f"occupations_{locale}.json.gz is stale: re-run scripts/build_occupations.py")

    def test_every_esco_occupation_is_cached(self):
        mapped = {uri for uri, *_ in fetch_esco.read_mapping()}
        for language in fetch_esco.LANGUAGES:
            with open(fetch_esco.cache_path(language), encoding="utf-8") as f:
                self.assertTrue(mapped <= set(json.load(f)), msg=language)

    def test_every_soft_skill_has_a_label_in_each_language(self):
        _sectors, jobs = build_occupations.load_rome(build_occupations.read_rome())
        used = {skill for job in jobs.values() for skill in job["soft_skills"]}
        for language, labels in build_occupations.SOFT_SKILLS.items():
            self.assertEqual(used, set(labels), msg=language)

    def test_demand_weights_add_up_to_the_bmo_total(self):
        _sectors, jobs = build_occupations.load_rome(build_occupations.read_rome())
        projects = build_occupations.read_bmo()
        weights = build_occupations.bmo_weights(jobs, projects, build_occupations.read_fap_rome())
        self.assertEqual(set(weights), set(jobs))
        self.assertAlmostEqual(sum(weights.values()), sum(projects.values()), delta=1)


if __name__ == "__main__":
    unittest.main()
