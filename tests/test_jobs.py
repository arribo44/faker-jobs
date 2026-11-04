"""
Unit tests for the JobsProvider.
"""
import datetime
import unittest
from collections import Counter

from faker import Faker

from faker_jobs import JobsProvider


class TestJobsProvider(unittest.TestCase):
    def setUp(self):
        # Fixed seed: every test sees the same draws on every run, so a
        # failure is reproducible instead of showing up once in a while.
        Faker.seed(20261104)
        self.fake = Faker("fr_FR")
        self.fake.add_provider(JobsProvider)
        self.provider = JobsProvider(self.fake)

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

    # -- titles / roles -----------------------------------------------------------

    def test_job_title_is_known(self):
        for _ in range(50):
            self.assertIn(self.fake.job_title(), self.provider.job_titles)
            self.assertIn(self.fake.job_title(weighted=False), self.provider.job_titles)

    def test_job_role_restricted_to_title(self):
        roles = {role["role"] for role in self.provider._data["roles_by_title"]["Web Developer"]}
        for _ in range(30):
            self.assertIn(self.fake.job_role(job_title="web developer"), roles)

    def test_unknown_title_or_role_raises(self):
        with self.assertRaises(ValueError):
            self.fake.job_role(job_title="Dragon Tamer")
        with self.assertRaises(ValueError):
            self.fake.job_role_record(role="Dragon Tamer")
        with self.assertRaises(ValueError):
            self.fake.job_role_record(job_title="Accountant", role="Frontend Web Developer")

    def test_role_record_lookup(self):
        record = self.fake.job_role_record(role="frontend web developer")
        self.assertEqual(record["role"], "Frontend Web Developer")
        self.assertEqual(record["job_title"], "Web Developer")
        self.assertTrue(record["description"] and record["skills"] and record["responsibilities"])
        self.assertEqual(self.fake.job_description(role="Frontend Web Developer"), record["description"])
        self.assertEqual(self.fake.job_skills(role="Frontend Web Developer"), record["skills"])
        self.assertEqual(self.fake.job_responsibilities(role="Frontend Web Developer"), record["responsibilities"])

    def test_weighted_roles_follow_popularity(self):
        # UX/UI Designer is by far the most posted job title in the source data.
        counts = Counter(self.fake.job_title() for _ in range(3000))
        self.assertEqual(counts.most_common(1)[0][0], "UX/UI Designer")
        uniform = Counter(self.fake.job_title(weighted=False) for _ in range(3000))
        self.assertLess(uniform["UX/UI Designer"], counts["UX/UI Designer"] / 2)

    # -- qualifications / experience / salary ----------------------------------------

    def test_qualification(self):
        code = self.fake.job_qualification()
        self.assertIn(code, self.provider._data["qualifications"])
        self.assertIn(self.fake.job_qualification(full_name=True), self.provider._data["qualifications"].values())
        self.assertEqual(self.fake.job_qualification_name("mba"), "Master of Business Administration")
        with self.assertRaises(ValueError):
            self.fake.job_qualification_name("XYZ")

    def test_experience_and_salary_ranges(self):
        for _ in range(100):
            low, high = self.fake.job_experience_range()
            self.assertTrue(0 <= low < high <= 15)
            low, high = self.fake.job_salary_bounds()
            self.assertTrue(55000 <= low < high <= 130000)
        self.assertRegex(self.fake.job_experience(), r"^\d+ to \d+ Years$")
        self.assertRegex(self.fake.job_salary_range(), r"^\$\d+K-\$\d+K$")

    # -- work type / benefits / portals -------------------------------------------------

    def test_work_type_and_portal(self):
        self.assertIn(self.fake.job_work_type(), {"Contract", "Full-Time", "Intern", "Part-Time", "Temporary"})
        self.assertIn(self.fake.job_portal(), self.provider._data["job_portals"])

    def test_benefits_are_distinct(self):
        for weighted in (True, False):
            benefits = self.fake.job_benefits(weighted=weighted)
            self.assertEqual(len(benefits), 5)
            self.assertEqual(len(set(benefits)), 5)
            self.assertTrue(set(benefits) <= set(self.provider._data["benefits"]))
        self.assertEqual(self.fake.job_benefits(count=0), [])
        self.assertEqual(len(self.fake.job_benefits(count=25)), 25)

    def test_invalid_benefit_count_raises(self):
        for count in (-1, 26, 2.5, True):
            with self.assertRaises(ValueError, msg=count):
                self.fake.job_benefits(count=count)

    # -- locations / companies -------------------------------------------------------

    def test_location(self):
        location = self.fake.job_location()
        self.assertIn(location["country"], self.provider.job_countries)
        self.assertTrue(-90 <= location["latitude"] <= 90 and -180 <= location["longitude"] <= 180)
        # With multiple cities per country, verify we get a French city
        french_loc = self.fake.job_location(country="france")
        self.assertEqual(french_loc["country"], "France")
        french_cities = [loc["city"] for loc in self.provider._data["locations"] if loc["country"] == "France"]
        self.assertIn(french_loc["city"], french_cities)
        with self.assertRaises(ValueError):
            self.fake.job_location(country="Atlantis")

    def test_company(self):
        profile = self.fake.job_company_profile(company="3m")
        self.assertEqual(profile["company"], "3M")
        self.assertEqual(profile["ticker"], "MMM")
        for _ in range(20):
            self.assertEqual(self.fake.job_company_profile(sector="energy")["sector"], "Energy")
        self.assertIn("Energy", self.provider.job_sectors)
        with self.assertRaises(ValueError):
            self.fake.job_company(sector="Piracy")
        with self.assertRaises(ValueError):
            self.fake.job_company_profile(company="Acme Unknown Corp")

    def test_missing_company_fields_are_none(self):
        values = [value for company in self.provider._data["companies"] for value in company.values()]
        self.assertNotIn("", values)
        self.assertIn(None, values)

    def test_company_size(self):
        self.assertTrue(12646 <= self.fake.job_company_size() <= 134834)

    # -- postings -------------------------------------------------------------------

    def test_job_id(self):
        self.assertTrue(10**14 <= self.fake.job_id() < 10**16)

    def test_posting_date(self):
        today = datetime.date.today()
        date = self.fake.job_posting_date()
        self.assertTrue(today - datetime.timedelta(days=731) <= date <= today)
        fixed = datetime.date(2024, 5, 1)
        self.assertEqual(self.fake.job_posting_date(start_date=fixed, end_date=fixed), fixed)

    def test_job_posting_is_consistent(self):
        posting = self.fake.job_posting(job_title="Web Developer", country="France", sector="Retail")
        self.assertEqual(posting["job_title"], "Web Developer")
        # With multiple cities per country, verify it's a French city
        self.assertEqual(posting["location"]["country"], "France")
        self.assertEqual(posting["company"]["sector"], "Retail")
        record = self.fake.job_role_record(role=posting["role"])
        self.assertEqual(posting["description"], record["description"])
        self.assertEqual(posting["experience"], f"{posting['experience_min']} to {posting['experience_max']} Years")
        self.assertEqual(posting["salary_range"],
                         f"${posting['salary_min'] // 1000}K-${posting['salary_max'] // 1000}K")
        self.assertEqual(posting["salary_currency"], "USD")
        self.assertIsInstance(posting["job_posting_date"], datetime.date)

    def test_contact_comes_from_locale(self):
        # fr_FR phone numbers start with +33 or 0; en_US ones never do with "0x xx".
        for _ in range(20):
            self.assertRegex(self.fake.job_posting()["contact"], r"^(\+33|0)")

    def test_seed_reproducibility(self):
        Faker.seed(42)
        first = self.fake.job_posting()
        Faker.seed(42)
        self.assertEqual(self.fake.job_posting(), first)


if __name__ == "__main__":
    unittest.main()
