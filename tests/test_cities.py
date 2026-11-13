"""
Tests for the job locations: GeoNames cities (faker_jobs/data/cities.json.gz)
picked by population, and scripts/build_cities.py where DATAS/ is available.
"""
import collections
import gzip
import json
import os
import sys
import unittest

from faker import Faker

from faker_jobs import _CITIES_PATH, JobsProvider, _load_cities

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import build_cities  # noqa: E402


class CitiesDataTests(unittest.TestCase):
    def test_every_country_has_cities(self):
        cities = _load_cities()
        self.assertEqual(len(cities), 244)
        for entry in cities.values():
            self.assertTrue(entry["cities"], entry["country"])
            for row in entry["cities"]:
                self.assertTrue(-90 <= row[1] <= 90 and -180 <= row[2] <= 180, row)
        self.assertGreater(len(cities["france"]["cities"]), 400)
        self.assertGreater(len(cities["united states"]["cities"]), 2000)

    def test_local_names_only_in_the_countries_of_the_locales(self):
        languages = {code: set(names) for code, names in build_cities.LOCAL_LANGUAGES.items()}
        for key, entry in _load_cities().items():
            local = [row[4] for row in entry["cities"] if len(row) > 4]
            self.assertTrue(all(len(row) in (4, 5) for row in entry["cities"]), key)
            for names in local:
                self.assertIsInstance(names, dict)
                self.assertTrue(names)
            if key in ("france", "germany", "spain", "italy", "belgium", "switzerland", "austria",
                       "luxembourg", "canada", "mexico", "chile", "colombia", "portugal", "the netherlands",
                       "poland", "brazil"):
                self.assertTrue(local, key)
            else:
                self.assertFalse(local, key)
        self.assertEqual(languages["CH"], {"fr", "de", "it"})
        geneva = next(row for row in _load_cities()["switzerland"]["cities"] if row[0] == "Geneva")
        self.assertEqual(geneva[4], {"fr": "Genève", "de": "Genf", "it": "Ginevra"})
        # Country names in the languages of the occupations, where not the English one.
        self.assertEqual(_load_cities()["germany"]["names"]["fr"], "Allemagne")
        self.assertEqual(_load_cities()["the netherlands"]["names"]["fr"], "Pays-Bas")
        self.assertNotIn("de", _load_cities()["china"]["names"])  # 'China' as in English
        # Only the names that differ from the English one.
        paris = next(row for row in _load_cities()["france"]["cities"] if row[0] == "Paris")
        self.assertEqual(len(paris), 4)

    def test_no_districts(self):
        names = {row[0] for row in _load_cities()["france"]["cities"]}
        self.assertIn("Paris", names)
        self.assertFalse([name for name in names if name.startswith(("Paris ", "Marseille ", "Lyon "))])


class LocationTests(unittest.TestCase):
    def test_picked_by_population(self):
        Faker.seed(11)
        fake = Faker("fr_FR")
        fake.add_provider(JobsProvider)
        counts = collections.Counter(fake.job_location()["city"] for _ in range(3000))
        self.assertGreater(len(counts), 150)
        self.assertEqual(counts.most_common(1)[0][0], "Paris")
        self.assertGreater(counts["Paris"], counts["Annecy"] * 3)

    def test_unknown_country(self):
        fake = Faker("en_US")
        fake.add_provider(JobsProvider)
        with self.assertRaisesRegex(ValueError, "Did you mean: france"):
            fake.job_location(country="Frnace")


@unittest.skipUnless(os.path.isfile(os.path.join(build_cities.GEONAMES_DIR, "cities15000.zip")),
                     "DATAS/geonames source files not available")
class BuildCitiesTests(unittest.TestCase):
    def test_packaged_file_is_up_to_date(self):
        data = build_cities.build()
        with gzip.open(_CITIES_PATH, "rt", encoding="utf-8") as f:
            self.assertEqual(json.load(f), json.loads(json.dumps(data)),
                             msg="faker_jobs/data/cities.json.gz is stale: re-run scripts/build_cities.py")

    def test_drop_districts(self):
        rows = [["Paris", 48.85, 2.35, 2_000_000], ["Paris 15 Vaugirard", 48.84, 2.29, 230_000],
                ["Quinze-Vingts", 48.847, 2.374, 25_000], ["Boulogne-Billancourt", 48.835, 2.24, 120_000]]
        self.assertEqual([row[0] for row in build_cities.drop_districts(rows)], ["Paris", "Boulogne-Billancourt"])


if __name__ == "__main__":
    unittest.main()
