"""
Tests for the postings outside the countries with conditions of their own:
neutral conditions in the language of the occupations, with the currency,
salaries and minimum wage of the country of the job (countries.json), for
every Faker locale and every country of `job_countries`.
"""
import unittest

from faker import Faker
from faker.config import AVAILABLE_LOCALES

from faker_jobs import JobsProvider, _load_conditions, _load_countries


def make(locale):
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    return fake, JobsProvider(fake)


def currency_of(country):
    return _load_countries()["countries"][country]["currency"]


class CountriesDataTests(unittest.TestCase):
    def test_almost_every_country_has_an_economy(self):
        _, provider = make("en_US")
        missing = set(provider.job_countries) - set(_load_countries()["countries"])
        # Uninhabited or without figures: North Korea, Western Sahara, a few islands.
        self.assertLessEqual(len(missing), 15, missing)
        self.assertIn("North Korea", missing)

    def test_economies(self):
        countries = _load_countries()["countries"]
        for country, economy in countries.items():
            base = economy["salary"]["base"]
            self.assertEqual(set(base), {str(group) for group in range(10)}, country)
            self.assertTrue(all(value["*"] > 0 for value in base.values()), country)
            # Managers and professionals earn more than elementary occupations.
            self.assertGreater(base["2"]["*"], base["9"]["*"], country)
            self.assertEqual(len(economy["currency"]), 3, country)
            self.assertTrue(economy["salary_source"], country)
        self.assertEqual(countries["Japan"]["currency"], "JPY")
        self.assertEqual(countries["Bulgaria"]["currency"], "EUR")  # euro since 2026
        self.assertEqual(countries["Liechtenstein"]["salary"], countries["Switzerland"]["salary"])
        self.assertIn("Eurostat SES", countries["Portugal"]["salary_source"])
        self.assertIn("ILOSTAT", countries["India"]["salary_source"])

    def test_the_countries_of_the_locales_keep_their_salaries(self):
        countries, conditions = _load_countries()["countries"], _load_conditions()
        self.assertEqual(countries["France"]["salary"]["base"], conditions["fr_FR"]["salary"]["base"])
        self.assertEqual(countries["Canada"]["salary"]["base"], conditions["en_CA"]["salary"]["base"])


class EveryLocaleTests(unittest.TestCase):
    def test_every_faker_locale_posts_in_a_currency_of_its_country(self):
        Faker.seed(1)
        for locale in AVAILABLE_LOCALES:
            with self.subTest(locale=locale):
                fake, provider = make(locale)
                conditions = provider._local_conditions()
                posting = fake.job_posting()
                self.assertEqual(posting["salary_currency"], conditions["currency"])
                self.assertIn(posting["location"]["country"],
                              {conditions["country"], (conditions.get("place_names") or {}).get("country")})
                self.assertLess(posting["salary_min"], posting["salary_max"])

    def test_locales_of_other_languages_get_their_country(self):
        # (locale, country, its name in the postings)
        for locale, country, shown in (("ja_JP", "Japan", "Japan"), ("pt_BR", "Brazil", "Brasil"),
                                       ("hi_IN", "India", "India"), ("zh_CN", "China", "China"),
                                       ("ar_EG", "Egypt", "Egypt"), ("fr_DZ", "Algeria", "Algérie"),
                                       ("de_LI", "Liechtenstein", "Liechtenstein"), ("zh_TW", "Taiwan", "Taiwan")):
            if locale not in AVAILABLE_LOCALES:
                continue  # fr_DZ: recent Faker versions only
            fake, provider = make(locale)
            self.assertEqual(provider._local_conditions()["country"], country, locale)
            self.assertEqual(fake.job_location()["country"], shown, locale)


class JobCountryTests(unittest.TestCase):
    def test_every_country_of_the_jobs(self):
        Faker.seed(2)
        fake, provider = make("en_US")
        countries = _load_countries()["countries"]
        for country in provider.job_countries:
            if country not in countries:
                continue
            posting = fake.job_posting(country=country)
            self.assertEqual(posting["location"]["country"], country)
            self.assertEqual(posting["salary_currency"], currency_of(country), country)

    def test_conditions_follow_the_country_of_the_job(self):
        Faker.seed(3)
        fake, provider = make("fr_FR")
        posting = fake.job_posting(country="Brazil")
        self.assertEqual(posting["salary_currency"], "BRL")
        self.assertTrue(posting["salary_range"].endswith(" BRL brut/an"), posting["salary_range"])
        self.assertNotIn(posting["job_portal"], {"France Travail", "APEC", "HelloWork"})
        # A country with conditions in the language: those (fr_BE), with its local names.
        self.assertEqual(fake.job_location(country="Belgium")["country"], "Belgique")
        self.assertEqual(fake.job_posting(country="BE")["location"]["country"], "Belgique")
        # Germany in French: neutral French conditions, German salaries.
        conditions = provider._posting_conditions("Germany")
        self.assertEqual(conditions["salary"]["base"], _load_conditions()["de_DE"]["salary"]["base"])
        self.assertIn("CDI", conditions["contracts"])
        # The locale's own country, by any name.
        self.assertIs(provider._posting_conditions("FR"), provider._local_conditions())

    def test_unknown_country(self):
        fake, _ = make("en_US")
        with self.assertRaisesRegex(ValueError, "Unknown country"):
            fake.job_posting(country="Atlantis")

    def test_country_without_economy_keeps_the_locale_conditions(self):
        fake, _ = make("en_US")
        posting = fake.job_posting(country="North Korea")
        self.assertEqual(posting["location"]["country"], "North Korea")
        self.assertEqual(posting["salary_currency"], "USD")


class NeutralConditionsTests(unittest.TestCase):
    def test_no_national_benefits_abroad(self):
        Faker.seed(4)
        fake, provider = make("ja_JP")
        conditions = provider._local_conditions()
        self.assertNotIn("401(k) matching", conditions["benefits"])
        self.assertEqual(set(conditions["job_portals"]["all"]),
                         {"LinkedIn", "Indeed", "Glassdoor", "Jooble", "Careerjet"})
        for _ in range(20):
            posting = fake.job_posting()
            self.assertRegex(posting["salary_range"], r"^JPY \d{1,3}(,\d{3})* - \d{1,3}(,\d{3})* a year$")
            # Rounded to 50,000 or 100,000 yen.
            self.assertEqual(posting["salary_min"] % 50_000, 0, posting["salary_min"])

    def test_minimum_wage(self):
        Faker.seed(5)
        fake, provider = make("en_IN")
        conditions = provider._local_conditions()
        minimum = conditions["minimum_wage"]
        self.assertTrue(minimum)
        for _ in range(40):
            posting = fake.job_occupation_posting()
            spec = conditions["contracts"][posting["work_type"]]
            if spec["salary_factor"] == 1 and spec["employee"]:
                self.assertGreaterEqual(posting["salary_min"], minimum)

    def test_companies_made_up_where_there_are_none(self):
        Faker.seed(6)
        fake, provider = make("ja_JP")
        self.assertEqual(provider.job_companies, [])
        posting = fake.job_occupation_posting()
        self.assertIsNone(posting["company"]["website"])
        self.assertEqual(posting["company"]["city"], posting["location"]["city"])
        self.assertGreater(fake.job_company_size(), 0)


if __name__ == "__main__":
    unittest.main()
