"""
Tests for the hiring companies: People Data Labs companies by country,
activity sector and size class (faker_jobs/data/companies.json.gz), and
scripts/build_companies.py.
"""
import collections
import gzip
import json
import os
import sys
import unittest

from faker import Faker

from faker_jobs import JobsProvider, _load_cities, _load_companies, _load_conditions

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_companies  # noqa: E402
import build_occupations  # noqa: E402
from naf_industries import INDUSTRY_NAF  # noqa: E402
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
                        self.assertTrue(city is None or (city < len(cities) if isinstance(city, int) else city))
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

    def test_real_company_has_an_activity_of_its_industry(self):
        for locale in ("fr_FR", "it_IT"):
            fake = Faker(locale)
            fake.add_provider(JobsProvider)
            Faker.seed(0)
            provider = next(p for p in fake.providers if isinstance(p, JobsProvider))
            conditions, data = provider._local_conditions(), _load_companies()
            country = provider._home_country(conditions)
            checked = 0
            for _ in range(200):
                posting = fake.job_occupation_posting()
                company = posting["company"]
                if company["website"] is None:
                    continue
                found = data["by_name"][country].get(company["company"].lower())
                if found is None or found[2][1] != company["website"]:
                    continue
                prefixes = conditions["naf_by_industry"][data["industries"][found[2][6]].lower()]
                activities = {entry[0] for entry in conditions["naf_by_sector"][posting["company_sector"]]}
                if any(code.startswith(tuple(prefixes)) for code in activities):
                    self.assertTrue(posting["company_naf"].startswith(tuple(prefixes)),
                                    (company, posting["company_naf"]))
                    checked += 1
            self.assertGreater(checked, 50, locale)

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

    def test_every_industry_has_naf_activities(self):
        self.assertEqual(set(INDUSTRY_NAF), set(build_companies.INDUSTRY_SECTORS))
        naf_by_industry = _load_conditions()["fr_FR"]["naf_by_industry"]
        self.assertEqual(naf_by_industry, dict(sorted(INDUSTRY_NAF.items())))

    def test_naf_weights(self):
        naf = {"49.41A": "", "49.41B": "", "50.30Z": "", "84.11Z": "", "52.10A": "", "52.10B": "", "52.21Z": ""}
        employment = {"H494": 400, "H503": 3, "H52": 100, "H521": 60}
        weights = build_occupations.naf_weights(naf, employment)
        self.assertEqual((weights["49.41A"], weights["50.30Z"]), (200, 3))  # a group, shared by its sub-classes
        self.assertEqual(weights["52.10A"], 30)
        self.assertEqual(weights["52.21Z"], 40)  # no group figure: the rest of its division
        self.assertIsNone(weights["84.11Z"])  # no figures at all

    def test_nace_classes_of_naf_prefixes(self):
        self.assertTrue(build_occupations.matches("70.22", "70.22Z"))
        self.assertTrue(build_occupations.matches("49.41", "49.4"))
        self.assertTrue(build_occupations.matches("88.10A", "88.10A"))
        self.assertFalse(build_occupations.matches("88.10B", "88.10A"))
        # A NACE class for each prefix: '62' -> '62.00', '49.4' -> '49.40', '70.22Z' -> '70.22'.
        classes = {prefix[:5] + "00.00"[len(prefix[:5]):]: "" for prefixes in INDUSTRY_NAF.values()
                   for prefix in prefixes}
        cut = build_occupations.naf_by_industry(classes)
        self.assertEqual(cut["airlines/aviation"], ["51", "52.23"])
        self.assertEqual(cut["management consulting"], ["70.22"])
        self.assertEqual(cut, _load_conditions()["de_DE"]["naf_by_industry"])

    def test_activity_fit(self):
        occupations = [{"isco_code": "6221", "sectors": ["Agri"]}, {"isco_code": "9999", "sectors": ["Agri"]}]
        naf_sectors = {"Agri": [["01.16Z"], ["01.62Z"], ["03.21Z"]]}
        isco_naf = {"6221": {"03.21Z": 990, "01.62Z": 3, "78.20Z": 50}, "9999": {"78.20Z": 10}}
        fit = build_occupations.activity_fit(occupations, naf_sectors, isco_naf)
        # 01.62Z: 0.3% of the occupation's employees in the sector, left out; no figures for 9999.
        self.assertEqual(fit, {"6221": {"Agri": [[2, 997]]}})
        nace = build_occupations.activity_fit(occupations, {"Agri": [["01.62"], ["03.21"]]}, isco_naf)
        self.assertEqual(nace["6221"]["Agri"], [[1, 997]])

    def test_fold(self):
        self.assertEqual(build_companies.fold("Düsseldorf"), "dusseldorf")
        self.assertEqual(build_companies.fold("Levallois-Perret "), "levallois perret")

    def _index(self):
        cities = {"countries": {country: {"cities": []} for country in build_companies.COUNTRY_CODES}}
        cities["countries"]["France"]["cities"] = [["Paris", 48.8534, 2.3488, 2138551, "Paris"],
                                                   ["Neuilly-sur-Seine", 48.8846, 2.2697, 60361, "Neuilly-sur-Seine"]]
        cities["countries"]["United States"]["cities"] = [["New York City", 40.7143, -74.006, 8804190],
                                                          ["Bentonville", 36.3729, -94.2088, 54164]]
        geonames = {"FR": [(48.8534, 2.3488, ["Paris", "Paris", "Lutece"], "11"),
                           (48.8932, 2.2879, ["Levallois-Perret", "Levallois-Perret"], "11")],
                    "US": [(40.7143, -74.006, ["New York City", "New York City", "New York"], "NY"),
                           (36.3729, -94.2088, ["Bentonville", "Bentonville"], "AR")]}
        return build_companies.city_index(cities, geonames)

    def test_city_index(self):
        index = self._index()
        self.assertEqual(index["United States"]["names"]["new york"], 0)
        self.assertFalse(build_companies.alternate_names("NYC"))  # codes left out
        self.assertTrue(build_companies.alternate_names("Brunswick"))
        self.assertEqual(index["United States"]["states"], ["New York", "Arkansas"])
        # A district left out of cities.json.gz: the nearest city, also by the last word of its name.
        self.assertEqual(index["France"]["names"]["levallois perret"], 1)
        self.assertEqual(index["France"]["suffixes"]["perret"], 1)

    def test_headquarters_city(self):
        index = self._index()
        regions = collections.defaultdict(set, {"France": {"paris", "ile de france"}})

        def city(name, locality, country="France", found=()):
            row = {"name": name, "locality": locality}
            return build_companies.headquarters_city(row, country, index, regions, list(found))

        self.assertEqual(city("acme", "paris, ile-de-france, france"), (0, None))
        self.assertEqual(city("acme", "perret, ile-de-france, france"), (1, None))
        self.assertEqual(city("acme", "ile-de-france, ile-de-france, france"), (None, None))
        self.assertEqual(city("acme", "france, aquitaine, france"), (None, None))
        self.assertEqual(city("acme", "vitré, bretagne, france"), ("Vitré", None))
        # Wikidata headquarters in the country (a name also a LinkedIn region: Paris), else LinkedIn's.
        self.assertEqual(city("acme", "france, aquitaine, france", found=[["Paris", 48.8567, 2.3522, "FR"]]),
                         (0, None))
        self.assertEqual(city("acme", "vitré, bretagne, france", found=[["Rome", 41.9, 12.5, "IT"]]),
                         ("Vitré", None))
        self.assertEqual(city("walmart", "withee, wisconsin, united states", "United States"), (1, "Arkansas"))
        self.assertEqual(city("acme", "new york, new york, united states", "United States"), (0, "New York"))

    @unittest.skipUnless(os.path.exists(build_companies.GEONAMES_PATH), "needs DATAS/geonames")
    def test_headquarters_fixes_are_cities(self):
        with gzip.open(build_companies.CITIES_PATH, "rt", encoding="utf-8") as f:
            index = build_companies.city_index(json.load(f), build_companies.read_geonames())
        for (country, _name), city in build_companies.HEADQUARTERS_FIXES.items():
            self.assertIn(build_companies.fold(city), index[country]["names"], city)

    def test_large_groups_have_a_city(self):
        data = _load_companies()
        for country, entry in data["countries"].items():
            rows = [row for grouped in entry["by_class"].values() for row in grouped[7]]
            self.assertGreater(sum(isinstance(row[3], int) for row in rows), 0.9 * len(rows), country)
        walmart = data["by_name"]["United States"]["walmart"][2]
        self.assertEqual((_load_cities()["united states"]["cities"][walmart[3]][0], walmart[4]),
                         ("Bentonville", "Arkansas"))

    def test_job_shares(self):
        shares = build_companies.shares(collections.Counter({0: 100, 7: 1}))
        self.assertAlmostEqual(sum(shares), 1, places=4)
        self.assertGreater(shares[7], shares[0])  # one large group employs more than 100 micro firms


if __name__ == "__main__":
    unittest.main()
