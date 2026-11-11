"""
Tests for the hiring companies: People Data Labs companies by country,
activity sector and size class (faker_jobs/data/companies.json.gz), and
scripts/build_companies.py.
"""
import collections
import os
import sys
import unittest

from faker import Faker

from faker_jobs import JobsProvider, _load_cities, _load_companies, _load_conditions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_companies  # noqa: E402
from rome_labels import SECTORS  # noqa: E402


class CompaniesDataTests(unittest.TestCase):
    def test_six_countries_and_35_sectors(self):
        data = _load_companies()
        self.assertEqual(set(data["countries"]),
                         {"United States", "United Kingdom", "France", "Germany", "Spain", "Italy"})
        codes = set(_load_conditions()["fr_FR"]["sector_codes"].values())
        self.assertEqual(len(codes), 35)
        for country, entry in data["countries"].items():
            self.assertEqual(set(entry["by_class"]), codes, country)
            self.assertAlmostEqual(entry["cum_weights_all"][-1], 1, places=3)
            for code, rows in entry["by_class"].items():
                self.assertAlmostEqual(entry["cum_weights"][code][-1], 1, places=3)
                self.assertEqual(rows[0], [], "1-10 employees are made up")
                self.assertTrue(any(rows), (country, code))

    def test_rows(self):
        data = _load_companies()
        for country, entry in data["countries"].items():
            cities = _load_cities()[country.lower()]["cities"]
            for grouped in entry["by_class"].values():
                for size_class, rows in enumerate(grouped):
                    self.assertLessEqual(len(rows), build_companies.PER_CLASS)
                    low, high = data["classes"][size_class]
                    for name, website, founded, city, state, size, industry in rows:
                        self.assertTrue(name and website)
                        self.assertTrue(low <= size and (size <= high or size_class == len(grouped) - 1))
                        self.assertTrue(founded is None or 1000 < founded < 2030)
                        self.assertTrue(city < len(cities) if isinstance(city, int) else city)
                        self.assertEqual(state is not None, country == "United States")
                        self.assertLess(industry, len(data["industries"]))

    def test_sector_codes_in_every_locale(self):
        for locale, conditions in _load_conditions().items():
            self.assertEqual(len(conditions["sector_codes"]), 35, locale)

    def test_no_company_dominates(self):
        fake = Faker("de_DE")
        fake.add_provider(JobsProvider)
        Faker.seed(0)
        counts = collections.Counter(fake.job_occupation_posting()["company"]["company"] for _ in range(1000))
        self.assertLess(counts.most_common(1)[0][1], 30)

    def test_official_size_shares(self):
        micro = {country: entry["cum_weights_all"][0] for country, entry in _load_companies()["countries"].items()}
        # Official statistics: 2-9 persons employed hold ~16% of the jobs in France, ~28% in Italy.
        self.assertTrue(0.1 < micro["France"] < 0.25, micro)
        self.assertGreater(micro["Italy"], micro["France"])
        self.assertTrue(all(share > 0.05 for share in micro.values()), micro)

    def test_company_size_follows_the_locale_country(self):
        fake = Faker("it_IT")
        fake.add_provider(JobsProvider)
        sizes = [fake.job_company_size() for _ in range(500)]
        self.assertGreater(sum(size <= 250 for size in sizes), 100)


class BuildCompaniesTests(unittest.TestCase):
    def test_every_sector_has_industries(self):
        self.assertEqual(set(build_companies.INDUSTRY_SECTORS.values()), set(SECTORS["en"]))

    def test_display_name(self):
        cases = {
            "ibm": "IBM", "kpmg": "KPMG", "bnp paribas": "BNP Paribas", "l'oréal": "L'Oréal",
            "siemens ag": "Siemens AG", "enel spa": "Enel SpA", "argentario golf resort & spa":
            "Argentario Golf Resort & Spa", "banco de santander": "Banco de Santander", "dr. oetker": "Dr. Oetker",
            "mcdonald's": "Mcdonald's", "rolls-royce": "Rolls-Royce",
        }
        for raw, expected in cases.items():
            self.assertEqual(build_companies.display_name(raw), expected)

    def test_clean_and_valid_names(self):
        self.assertEqual(build_companies.clean_name("châteauform'​  group"), "châteauform' group")
        self.assertFalse(build_companies.valid_name("info@acme.com"))
        self.assertFalse(build_companies.valid_name("123"))
        self.assertFalse(build_companies.valid_name("** private **"))
        self.assertFalse(build_companies.valid_name("(usta) united states tennis association"))
        self.assertFalse(build_companies.valid_name("self-employed"))
        self.assertTrue(build_companies.valid_name("3m"))

    def test_company_size_in_class(self):
        import random
        rng = random.Random(0)
        self.assertEqual(build_companies.company_size(rng, 1, 30), 30)
        for estimate in (0, 3, 500):
            self.assertTrue(11 <= build_companies.company_size(rng, 1, estimate) <= 50)
        self.assertEqual(build_companies.company_size(rng, 7, 250000), 250000)

    def test_calibrate_to_official_shares(self):
        linkedin = [0.02, 0.08, 0.1, 0.1, 0.1, 0.2, 0.1, 0.3]
        groups = [[2, 9], [10, 49], [50, 249], [250, None]]
        calibrated = build_companies.calibrate(linkedin, groups, [20, 20, 20, 40], linkedin)
        self.assertAlmostEqual(sum(calibrated), 1, places=4)
        self.assertEqual(calibrated[:3], [0.2, 0.2, 0.2])
        # 250+ keeps the LinkedIn split of its classes: 201-500 is 1/8 of them.
        self.assertAlmostEqual(calibrated[3], 0.4 * 0.1 / 0.8, places=5)
        # A group without LinkedIn companies in the sector: the country's split.
        country = [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.3]
        empty = build_companies.calibrate([0, 0.5, 0.5, 0, 0, 0, 0, 0], groups, [20, 20, 20, 40], country)
        self.assertAlmostEqual(empty[7], 0.4 * 0.3 / 0.7, places=5)
        with self.assertRaises(ValueError):
            build_companies.calibrate(linkedin, [[2, 9], [10, 14], [15, 49], [50, None]], [1, 1, 1, 1], linkedin)

    def test_job_shares(self):
        shares = build_companies.shares(collections.Counter({0: 100, 7: 1}))
        self.assertAlmostEqual(sum(shares), 1, places=4)
        self.assertGreater(shares[7], shares[0])  # one large group employs more than 100 micro firms


if __name__ == "__main__":
    unittest.main()
