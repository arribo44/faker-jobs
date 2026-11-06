"""
Tests for the generic methods (job_title, job_role_record, job_salary_range,
job_company_profile...) in the German, Spanish, French and Italian locales:
they use the occupations and local conditions, not the English Kaggle data.
"""
import unittest

from faker import Faker

from faker_jobs import JobsProvider


def make(locale, provider=JobsProvider):
    fake = Faker(locale)
    fake.add_provider(provider)
    return fake, provider(fake)


class LocalizedTests:
    """Shared by the localized locales (mixed into a TestCase below)."""

    locale = ""
    country = ""
    currency_sign = "€"

    def setUp(self):
        Faker.seed(20261106)
        self.fake, self.provider = make(self.locale)
        self.conditions = self.provider._local_conditions()
        self.kaggle = JobsProvider(Faker("en_US"))

    def test_titles_and_roles_are_occupations(self):
        titles, roles = set(self.provider.job_titles), set(self.provider.job_roles)
        self.assertGreater(len(roles), 1900)
        self.assertLess(len(titles & set(self.kaggle.job_titles)), 10)   # loanwords only (Data Scientist)
        for _ in range(30):
            title = self.fake.job_title()
            self.assertIn(title, titles)
            self.assertIn(self.fake.job_role(job_title=title), roles)

    def test_role_record_is_an_occupation(self):
        record = self.fake.job_role_record()
        occupation = self.provider._occupations["occupation_by_title"][record["role"].lower()]
        self.assertIn(record["job_title"], occupation["titles"])
        self.assertTrue(record["description"] and record["skills"] and record["responsibilities"])
        for activity in record["responsibilities"].split("; "):
            self.assertIn(activity, occupation["skills"])
        same = self.fake.job_role_record(role=record["role"], job_title=record["job_title"])
        self.assertEqual((same["role"], same["job_title"]), (record["role"], record["job_title"]))
        self.assertTrue(self.fake.job_description(role=record["role"]))
        self.assertTrue(self.fake.job_skills(role=record["role"]))
        self.assertTrue(self.fake.job_responsibilities(role=record["role"]))

    def test_unknown_title_or_role(self):
        with self.assertRaisesRegex(ValueError, "Unknown job title"):
            self.fake.job_role(job_title="Software Engineer zz")
        with self.assertRaisesRegex(ValueError, "Unknown role"):
            self.fake.job_role_record(role="Frontend Web Developer zz")
        first, last = self.provider._occupations["occupations"][0], self.provider._occupations["occupations"][-1]
        job_title = next(title for title in first["titles"] if title not in last["titles"])
        with self.assertRaisesRegex(ValueError, "does not belong"):
            self.fake.job_role_record(job_title=job_title, role=last["title"])

    def test_local_conditions(self):
        qualifications = {name for names in self.conditions["qualifications"].values() for name in names}
        portals = set(self.conditions["job_portals"]["all"]) | set(self.conditions["job_portals"].get("executive", []))
        for _ in range(20):
            qualification = self.fake.job_qualification()
            self.assertIn(qualification, qualifications)
            self.assertEqual(self.fake.job_qualification_name(qualification.lower()), qualification)
            self.assertIn(self.fake.job_work_type(), self.conditions["contracts"])
            self.assertIn(self.fake.job_portal(), portals)
            low, high = self.fake.job_salary_bounds()
            self.assertLess(low, high)
            self.assertIn(self.currency_sign, self.fake.job_salary_range())
            low, high = self.fake.job_experience_range()
            self.assertLessEqual(low, high)
            self.assertTrue(self.fake.job_experience())
            self.assertNotIn("Years", self.fake.job_experience())
        benefits = self.fake.job_benefits()
        self.assertEqual(len(benefits), self.conditions["benefits_per_posting"])
        self.assertTrue(set(benefits) <= set(self.conditions["benefits"]))
        self.assertEqual(self.fake.job_benefits(count=0), [])
        with self.assertRaises(ValueError):
            self.fake.job_benefits(count=len(self.conditions["benefits"]) + 1)
        with self.assertRaisesRegex(ValueError, "Unknown qualification"):
            self.fake.job_qualification_name("MBA")

    def test_location_in_the_country(self):
        self.assertEqual(self.fake.job_location()["country"], self.country)
        self.assertEqual(self.fake.job_location(country="Belgium")["country"], "Belgium")

    def test_companies_made_up_in_activity_sectors(self):
        self.assertEqual(self.provider.job_sectors, self.provider.job_activity_sectors)
        kaggle = set(self.provider.job_companies)
        sector = self.provider.job_activity_sectors[0]
        profile = self.fake.job_company_profile(sector=sector)
        self.assertEqual(profile["sector"], sector)
        self.assertNotIn(profile["company"], kaggle)
        self.assertIsNone(profile["ticker"])
        self.assertTrue(profile["ceo"])
        self.assertTrue(self.fake.job_company())
        self.assertEqual(self.fake.job_company_profile(company="Acme")["company"], "Acme")
        with self.assertRaisesRegex(ValueError, "Unknown activity sector"):
            self.fake.job_company(sector="Piracy")

    def test_kaggle_posting_stays_kaggle(self):
        posting = self.fake.job_posting(source="kaggle")
        self.assertEqual(posting["salary_currency"], "USD")
        self.assertIn(posting["job_title"], self.kaggle.job_titles)
        self.assertIn(posting["company"]["company"], set(self.kaggle.job_companies))


class TestFrenchLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "fr_FR", "France"

    def test_french_values(self):
        self.assertIn(self.fake.job_work_type(), {"CDI", "CDD", "CDD saisonnier", "Intérim", "Alternance",
                                                  "Stage", "Freelance"})
        self.assertTrue(self.fake.job_salary_range().endswith("€ brut/an"))
        # ROME sheets have no description: the activities stand for it, as in job_posting().
        record = self.fake.job_role_record(role="Développeur / Développeuse informatique")
        self.assertEqual(record["description"], record["responsibilities"])

    def test_french_company_has_a_naf_activity(self):
        profile = self.fake.job_company_profile(sector="Santé")
        naf_labels = {naf[1] for naf in self.provider._local_conditions()["naf_by_sector"]["Santé"]}
        self.assertIn(profile["industry"], naf_labels)


class TestGermanLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "de_DE", "Deutschland"


class TestSpanishLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "es_ES", "España"


class TestItalianLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "it_IT", "Italia"

    def test_local_place_names(self):
        cities = {self.fake.job_location()["city"] for _ in range(200)}
        self.assertIn("Roma", cities)
        self.assertFalse(cities & {"Rome", "Milan", "Naples"})
        # The English name and the local one both pick the country.
        self.assertEqual(self.fake.job_location(country="Italy")["country"], "Italia")
        self.assertEqual(self.fake.job_location(country="italia")["country"], "Italia")
        self.assertEqual(self.fake.job_occupation_posting()["location"]["country"], "Italia")
        # Other countries keep the names of the location data.
        self.assertEqual(self.fake.job_location(country="Germany")["country"], "Germany")


class TestEnglishKeepsKaggle(unittest.TestCase):
    def test_english_locales_are_not_localized(self):
        for locale in ("en_US", "en_GB", "nl_NL"):
            fake, provider = make(locale)
            self.assertIsNone(provider._localized(), msg=locale)
            self.assertIn(fake.job_title(), provider._data["job_titles"])
            self.assertTrue(fake.job_salary_range().startswith("$"))


class KaggleJobs(JobsProvider):
    use_kaggle_data = True


class TestUseKaggleData(unittest.TestCase):
    def test_opt_out(self):
        fake, provider = make("fr_FR", KaggleJobs)
        self.assertIsNone(provider._localized())
        self.assertIn(fake.job_title(), provider._data["job_titles"])
        self.assertTrue(fake.job_salary_range().startswith("$"))
        # The occupation methods stay French.
        self.assertEqual(fake.job_occupation_posting()["salary_currency"], "EUR")

    def test_forced_occupation_locale_is_localized(self):
        class FrenchJobs(JobsProvider):
            occupations_locale = "fr_FR"

        fake, provider = make("en_US", FrenchJobs)
        self.assertIsNotNone(provider._localized())
        self.assertTrue(fake.job_salary_range().endswith("€ brut/an"))


if __name__ == "__main__":
    unittest.main()
