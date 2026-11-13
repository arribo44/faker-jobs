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
           build_occupations.NAF_PATH, build_occupations.fetch_salaries.EUROSTAT_PATH,
           build_occupations.fetch_salaries.BLS_PATH, build_occupations.fetch_salaries.LFS_PATH,
           build_occupations.fetch_salaries.OECD_PATH, build_occupations.fetch_salaries.ILOSTAT_PATH,
           build_occupations.fetch_salaries.WORLD_BANK_PATH, build_occupations.COUNTRY_INFO_PATH,
           fetch_esco.MAPPING_PATH,
           *map(fetch_esco.cache_path, fetch_esco.LANGUAGES))


# DATAS/ is not published: these tests only run where the sources (and
# openpyxl and xlrd, dev dependencies) are available.
@unittest.skipUnless(all(map(os.path.exists, SOURCES))
                     and all(map(importlib.util.find_spec, ("openpyxl", "xlrd"))),
                     "ROME/ESCO/BMO/NAF/salary source files, openpyxl or xlrd not available")
class TestBuildOccupations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, cls.conditions = build_occupations.split_outputs(build_occupations.build_occupations())

    def test_packaged_json_is_up_to_date(self):
        for locale, data in self.data.items():
            with gzip.open(build_occupations.output_path(locale), "rt", encoding="utf-8") as f:
                packaged = json.load(f)
            self.assertEqual(packaged, json.loads(json.dumps(data)),
                             msg=f"occupations_{locale}.json.gz is stale: re-run scripts/build_occupations.py")
        with open(build_occupations.CONDITIONS_PATH, encoding="utf-8") as f:
            self.assertEqual(json.load(f), json.loads(json.dumps(self.conditions)),
                             msg="conditions.json is stale: re-run scripts/build_occupations.py")
        with open(build_occupations.COUNTRIES_PATH, encoding="utf-8") as f:
            self.assertEqual(json.load(f), json.loads(json.dumps(build_occupations.build_countries(self.conditions))),
                             msg="countries.json is stale: re-run scripts/build_occupations.py")

    def test_floats_are_rounded(self):
        self.assertEqual(build_occupations.round_floats({"a": [0.48871358277284155, 2, "x"]}),
                         {"a": [0.488714, 2, "x"]})

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
        projects, seasonal = build_occupations.read_bmo()
        fap_rome = build_occupations.read_fap_rome()
        weights = build_occupations.bmo_weights(jobs, projects, fap_rome)
        self.assertEqual(set(weights), set(jobs))
        self.assertAlmostEqual(sum(weights.values()), sum(projects.values()), delta=1)
        shares = build_occupations.bmo_seasonal(jobs, projects, seasonal, fap_rome)
        self.assertEqual(set(shares), set(jobs))
        self.assertTrue(all(0 <= share <= 1 for share in shares.values()))
        national = sum(seasonal.values()) / sum(projects.values())
        self.assertAlmostEqual(sum(shares[c] * weights[c] for c in jobs) / sum(weights.values()), national, delta=0.05)



class TestContractWeights(unittest.TestCase):
    """contract_weights() needs no source data."""

    contracts = {
        "permanent": {"weight": 60, "kind": "permanent"},
        "fixed-term": {"weight": 20, "kind": "temporary"},
        "freelance": {"weight": 10, "kind": "freelance"},
        "internship": {"weight": 10, "kind": "intern"},
    }

    def lfs(self, temporary, self_employed=None):
        groups = [f"OC{g}" for g in "0123456789"]
        return {
            "employees": {"TOTAL": 1000, **dict.fromkeys(groups, 100)},
            "temporary": {"TOTAL": 100, **{f"OC{g}": share for g, share in temporary.items()}},
            "employed": {"TOTAL": 1000, **dict.fromkeys(groups, 100)},
            "part_time": {"TOTAL": 100},
            "self_employed": {"TOTAL": 100, **(self_employed or {})},
        }

    def test_national_mix_without_figures(self):
        weights = build_occupations.contract_weights(self.contracts, None)
        self.assertEqual(weights["1"], {name: spec["weight"] for name, spec in self.contracts.items()})

    def test_mix_follows_the_group_shares(self):
        # Group 1: 5 % temporary (half the national 10 %); group 9: 20 % (twice).
        weights = build_occupations.contract_weights(self.contracts, self.lfs({"1": 5, "9": 20}))
        self.assertEqual(weights["1"]["fixed-term"], 10)
        self.assertEqual(weights["9"]["fixed-term"], 40)
        self.assertEqual(weights["1"]["internship"], 10)
        self.assertEqual(weights["1"]["freelance"], 0)   # not published: counts as 0
        for mix in weights.values():
            self.assertAlmostEqual(sum(mix.values()), 100)

    def test_capped_ratio_and_minimum_permanent(self):
        weights = build_occupations.contract_weights(
            self.contracts, self.lfs({"6": 90}, self_employed={"OC6": 90}))
        mix = weights["6"]
        self.assertAlmostEqual(sum(mix.values()), 100)
        self.assertAlmostEqual(mix["permanent"], 10)
        # 20 x 3 and 10 x 3 (capped), then scaled down to leave 10 % permanent.
        self.assertAlmostEqual(mix["fixed-term"] / mix["freelance"], 2, places=2)


if __name__ == "__main__":
    unittest.main()
