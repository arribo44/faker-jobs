"""
Unit tests for the JobsProvider: registration, the generic methods in an
English locale (ESCO occupations, US conditions, Kaggle cities and
companies) and job_posting().
"""
import datetime
import json
import unittest

from faker import Faker

from faker_jobs import _DATA_PATH, JobsProvider, _load_cities


class TestJobsProvider(unittest.TestCase):
    def setUp(self):
        # Fixed seed: every test sees the same draws on every run, so a
        # failure is reproducible instead of showing up once in a while.
        Faker.seed(20261104)
        self.fake = Faker("en_US")
        self.fake.add_provider(JobsProvider)
        self.provider = JobsProvider(self.fake)
        self.conditions = self.provider._local_conditions()

    # -- registration -----------------------------------------------------------

    def test_faker_builtins_are_not_shadowed(self):
        fake = Faker("en_US")
        builtin_job = fake.job
        builtin_company = fake.company
        fake.add_provider(JobsProvider)
        self.assertIs(fake.job.__func__, builtin_job.__func__)
        self.assertIs(fake.company.__func__, builtin_company.__func__)

    def test_methods_are_registered_on_faker(self):
        for name in ("job_title", "job_role", "job_role_record", "job_posting", "job_benefits", "job_location"):
            self.assertTrue(callable(getattr(self.fake, name)), msg=name)

    def test_no_kaggle_job_data_is_shipped(self):
        with open(_DATA_PATH, encoding="utf-8") as f:
            self.assertEqual(set(json.load(f)), {"meta", "companies", "ranges"})
        self.assertFalse(hasattr(JobsProvider, "use_kaggle_data"))

    # -- titles / roles -----------------------------------------------------------

    def test_titles_and_roles_are_occupations(self):
        titles, roles = set(self.provider.job_titles), set(self.provider.job_roles)
        self.assertGreater(len(roles), 2000)
        for _ in range(30):
            title = self.fake.job_title()
            self.assertIn(title, titles)
            self.assertIn(self.fake.job_role(job_title=title), roles)
            self.assertIn(self.fake.job_title(weighted=False), titles)

    def test_role_record_lookup(self):
        record = self.fake.job_role_record(role="Accountant")
        self.assertEqual(record["role"], "accountant")
        self.assertTrue(record["description"] and record["skills"] and record["responsibilities"])
        occupation = self.provider._occupations["occupation_by_title"]["accountant"]
        self.assertIn(record["job_title"], occupation["titles"])
        for activity in record["responsibilities"].split("; "):
            self.assertIn(activity, occupation["skills"])
        self.assertEqual(self.fake.job_description(role="accountant"), record["description"])
        self.assertTrue(self.fake.job_skills(role="accountant"))
        self.assertTrue(self.fake.job_responsibilities(role="accountant"))

    def test_unknown_title_or_role_raises(self):
        with self.assertRaisesRegex(ValueError, "Unknown job title"):
            self.fake.job_role(job_title="Dragon Tamer")
        with self.assertRaisesRegex(ValueError, "Unknown role"):
            self.fake.job_role_record(role="Dragon Tamer")
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.fake.job_role_record(job_title="accountant", role="pizzaiolo")

    # -- conditions (US) ----------------------------------------------------------

    def test_us_conditions(self):
        qualifications = {name.format(field=field) for names in self.conditions["qualifications"].values()
                          for name in names for field in self.conditions["fields_of_study"].values()}
        portals = set(self.conditions["job_portals"]["all"]) | set(self.conditions["job_portals"].get("executive", []))
        for _ in range(30):
            self.assertIn(self.fake.job_qualification(), qualifications)
            self.assertIn(self.fake.job_work_type(), self.conditions["contracts"])
            self.assertIn(self.fake.job_portal(), portals)
            low, high = self.fake.job_experience_range()
            self.assertLessEqual(low, high)
            low, high = self.fake.job_salary_bounds()
            self.assertLess(low, high)
        self.assertRegex(self.fake.job_salary_range(), r"^\$[\d,]+ - \$[\d,]+ a year$")
        self.assertTrue(self.fake.job_experience())

    def test_benefits_are_distinct(self):
        benefits = self.fake.job_benefits()
        self.assertEqual(len(benefits), self.conditions["benefits_per_posting"])
        self.assertEqual(len(set(benefits)), len(benefits))
        self.assertTrue(set(benefits) <= set(self.conditions["benefits"]))
        self.assertEqual(self.fake.job_benefits(count=0), [])
        everything = len(self.conditions["benefits"])
        self.assertEqual(len(self.fake.job_benefits(count=everything)), everything)

    def test_invalid_benefit_count_raises(self):
        for count in (-1, len(self.conditions["benefits"]) + 1, 2.5, True):
            with self.assertRaises(ValueError, msg=count):
                self.fake.job_benefits(count=count)

    # -- locations / companies (Kaggle) ------------------------------------------------

    def test_location(self):
        for _ in range(20):
            self.assertEqual(self.fake.job_location()["country"], "USA")
        location = self.fake.job_location(country="france")
        self.assertEqual(location["country"], "France")
        self.assertIn(location["country"], self.provider.job_countries)
        self.assertTrue(-90 <= location["latitude"] <= 90 and -180 <= location["longitude"] <= 180)
        self.assertIn(location["city"], [row[0] for row in _load_cities()["france"]["cities"]])
        self.assertEqual(len(self.provider.job_countries), 216)
        self.assertEqual(self.provider.job_countries, sorted(set(self.provider.job_countries)))
        with self.assertRaisesRegex(ValueError, "Unknown country"):
            self.fake.job_location(country="Atlantis")

    def test_company(self):
        profile = self.fake.job_company_profile(company="3m")
        self.assertEqual(profile["company"], "3M")
        self.assertEqual(profile["ticker"], "MMM")
        for _ in range(20):
            self.assertEqual(self.fake.job_company_profile(sector="energy")["sector"], "Energy")
        self.assertIn("Energy", self.provider.job_sectors)
        self.assertIn(self.fake.job_company(), self.provider.job_companies)
        with self.assertRaises(ValueError):
            self.fake.job_company(sector="Piracy")
        with self.assertRaises(ValueError):
            self.fake.job_company_profile(company="Acme Unknown Corp")

    def test_missing_company_fields_are_none(self):
        values = [value for company in self.provider._data["companies"] for value in company.values()]
        self.assertNotIn("", values)
        self.assertIn(None, values)

    def test_company_size(self):
        sizes = [self.fake.job_company_size() for _ in range(300)]
        self.assertGreaterEqual(min(sizes), 1)
        self.assertTrue(any(size <= 50 for size in sizes))
        self.assertTrue(any(size > 10000 for size in sizes))

    # -- postings -------------------------------------------------------------------

    def test_job_id(self):
        self.assertTrue(10**14 <= self.fake.job_id() < 10**16)

    def test_posting_date(self):
        today = datetime.date.today()
        date = self.fake.job_posting_date()
        self.assertTrue(today - datetime.timedelta(days=731) <= date <= today)
        fixed = datetime.date(2024, 5, 1)
        self.assertEqual(self.fake.job_posting_date(start_date=fixed, end_date=fixed), fixed)

    def test_job_posting_is_an_occupation(self):
        posting = self.fake.job_posting()
        occupation = posting["occupation"]
        self.assertEqual(posting["role"], occupation["title"])
        self.assertTrue(posting["description"] and posting["skills"] and posting["responsibilities"])
        for activity in posting["responsibilities"].split("; "):
            self.assertIn(activity, occupation["skills"])
        self.assertEqual(posting["salary_currency"], "USD")
        self.assertEqual(posting["location"]["country"], "USA")
        self.assertIsInstance(posting["job_posting_date"], datetime.date)

    def test_job_posting_options(self):
        posting = self.fake.job_posting(role="accountant", country="France")
        self.assertEqual(posting["role"], "accountant")
        self.assertEqual(posting["location"]["country"], "France")
        title = self.provider._occupations["occupation_by_title"]["accountant"]["titles"][-1]
        posting = self.fake.job_posting(job_title=title)
        self.assertEqual(posting["job_title"], title)
        code = posting["occupation"]["code"]
        self.assertEqual(self.fake.job_posting(code=code)["occupation"]["code"], code)
        sector = self.provider.job_activity_sectors[0]
        self.assertIn(sector, self.fake.job_posting(sector=sector)["occupation"]["sectors"])

    def test_job_posting_errors(self):
        with self.assertRaisesRegex(ValueError, "either code"):
            self.fake.job_posting(code="x", role="accountant")
        with self.assertRaisesRegex(ValueError, "Unknown role"):
            self.fake.job_posting(role="Dragon Tamer")
        with self.assertRaisesRegex(ValueError, "not in activity sector"):
            self.fake.job_posting(role="accountant", sector="Agriculture and livestock")
        with self.assertRaises(TypeError):
            self.fake.job_posting(source="kaggle")

    def test_contact_comes_from_locale(self):
        fake = Faker("fr_FR")
        fake.add_provider(JobsProvider)
        # fr_FR phone numbers start with +33 or 0.
        for _ in range(20):
            self.assertRegex(fake.job_posting()["contact"], r"^(\+33|0)")

    def test_seed_reproducibility(self):
        Faker.seed(42)
        first = self.fake.job_posting()
        Faker.seed(42)
        self.assertEqual(self.fake.job_posting(), first)


class TestOtherLocalesUseUsConditions(unittest.TestCase):
    def test_locales_without_conditions(self):
        us = JobsProvider(Faker("en_US"))._local_conditions()
        for locale in ("en_GB", "nl_NL", "ja_JP"):
            fake = Faker(locale)
            fake.add_provider(JobsProvider)
            provider = JobsProvider(fake)
            self.assertIs(provider._local_conditions(), us, msg=locale)
            self.assertIn(fake.job_title(), provider.job_titles)
            posting = fake.job_posting()
            self.assertEqual(posting["salary_currency"], "USD", msg=locale)
            # en_GB: jobs and companies in the United Kingdom (US conditions).
            self.assertEqual(posting["location"]["country"], "UK" if locale == "en_GB" else "USA", msg=locale)


if __name__ == "__main__":
    unittest.main()
