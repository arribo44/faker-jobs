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
        self.assertEqual(set(data["countries"]), {"USA", "UK", "France", "Germany", "Spain", "Italy"})
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
                        self.assertEqual(state is not None, country == "USA")
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
        self.assertTrue(build_companies.valid_name("3m"))

    def test_company_size_in_class(self):
        import random
        rng = random.Random(0)
        self.assertEqual(build_companies.company_size(rng, 1, 30), 30)
        for estimate in (0, 3, 500):
            self.assertTrue(11 <= build_companies.company_size(rng, 1, estimate) <= 50)
        self.assertEqual(build_companies.company_size(rng, 7, 250000), 250000)

    def test_job_shares(self):
        shares = build_companies.shares(collections.Counter({0: 100, 7: 1}))
        self.assertAlmostEqual(sum(shares), 1, places=4)
        self.assertGreater(shares[7], shares[0])  # one large group employs more than 100 micro firms


if __name__ == "__main__":
    unittest.main()
