"""
Tests for the country locales with posting conditions of their own over
those of their language (fr_BE, fr_CH, fr_CA, de_AT, de_CH, de_LU, it_CH,
es_MX, es_CL, es_CO, en_GB, en_IE, en_CA, en_AU, en_NZ): currency, contracts,
salaries, job boards, diplomas, places and companies of the country.
"""
import re
import unittest

from faker import Faker

from faker_jobs import JobsProvider, _conditions_locale, _load_companies, _load_conditions

# Faker locale -> (country of job_countries, its local name, currency, occupation locale).
COUNTRIES = {
    "fr_BE": ("Belgium", "Belgique", "EUR", "fr_FR"),
    "fr_CH": ("Switzerland", "Suisse", "CHF", "fr_FR"),
    "fr_CA": ("Canada", "Canada", "CAD", "fr_FR"),
    "de_AT": ("Austria", "Österreich", "EUR", "de_DE"),
    "de_CH": ("Switzerland", "Schweiz", "CHF", "de_DE"),
    "de_LU": ("Luxembourg", "Luxemburg", "EUR", "de_DE"),
    "it_CH": ("Switzerland", "Svizzera", "CHF", "it_IT"),
    "es_MX": ("Mexico", "México", "MXN", "es_ES"),
    "es_CL": ("Chile", "Chile", "CLP", "es_ES"),
    "es_CO": ("Colombia", "Colombia", "COP", "es_ES"),
    "en_GB": ("United Kingdom", "United Kingdom", "GBP", "en_US"),
    "en_IE": ("Ireland", "Ireland", "EUR", "en_US"),
    "en_CA": ("Canada", "Canada", "CAD", "en_US"),
    "en_AU": ("Australia", "Australia", "AUD", "en_US"),
    "en_NZ": ("New Zealand", "New Zealand", "NZD", "en_US"),
}


def make(locale, provider=JobsProvider):
    fake = Faker(locale)
    fake.add_provider(provider)
    return fake, provider(fake)


class CountryConditionsTests(unittest.TestCase):
    def setUp(self):
        Faker.seed(20261113)

    def test_every_country_locale_is_tested(self):
        own = {locale for locale, entry in _load_conditions().items() if "base" in entry}
        self.assertEqual(own, set(COUNTRIES))

    def test_postings_are_in_the_country(self):
        for locale, (country, local_name, currency, base) in COUNTRIES.items():
            with self.subTest(locale=locale):
                fake, provider = make(locale)
                conditions = provider._local_conditions()
                self.assertEqual(conditions["country"], country)
                self.assertEqual(provider._occupations["meta"]["language"], base[:2])
                # The rest comes from the occupation locale of the language.
                base_conditions = _load_conditions()[base]
                self.assertEqual(conditions["fields_of_study"], base_conditions["fields_of_study"])
                self.assertEqual(conditions["sector_codes"], base_conditions["sector_codes"])
                portals = set(conditions["job_portals"]["all"])
                for _ in range(15):
                    posting = fake.job_posting()
                    self.assertEqual(posting["location"]["country"], local_name)
                    self.assertEqual(posting["salary_currency"], currency)
                    self.assertIn(posting["work_type"], conditions["contracts"])
                    self.assertIn(posting["job_portal"], portals)
                    self.assertTrue(set(posting["benefits"]) <= set(conditions["benefits"]))
                    self.assertLess(posting["salary_min"], posting["salary_max"])
                    self.assertNotIn("{", posting["qualification"])
                self.assertEqual(fake.job_location()["country"], local_name)
                self.assertTrue(provider.job_companies)

    def test_contract_names_follow_the_country(self):
        self.assertIn("Indépendant", _load_conditions()["fr_BE"]["contracts"])
        self.assertIn("Permanent", _load_conditions()["fr_CA"]["contracts"])
        self.assertIn("Lehre", _load_conditions()["de_AT"]["contracts"])
        self.assertIn("Honorarios", _load_conditions()["es_MX"]["contracts"])
        self.assertIn("Casual", _load_conditions()["en_AU"]["contracts"])

    def test_salary_wording(self):
        patterns = {
            "fr_BE": r"^\d{1,3}(\.\d{3})* € - \d{1,3}(\.\d{3})* € brut/an$",
            "fr_CH": r"^CHF \d{1,3}('\d{3})* - \d{1,3}('\d{3})* brut/an$",
            "fr_CA": r"^\d{1,3}( \d{3})* \$ - \d{1,3}( \d{3})* \$ par année$",
            "de_CH": r"^CHF \d{1,3}('\d{3})* - \d{1,3}('\d{3})* brutto/Jahr$",
            "es_MX": r"^\$\d{1,3}(,\d{3})* - \$\d{1,3}(,\d{3})* MXN brutos al año$",
            "en_GB": r"^£\d{1,3}(,\d{3})* - £\d{1,3}(,\d{3})* per annum$",
            "en_AU": r"^\$\d{1,3}(,\d{3})* - \$\d{1,3}(,\d{3})* \+ super$",
        }
        for locale, pattern in patterns.items():
            fake, _ = make(locale)
            for _ in range(10):
                self.assertRegex(fake.job_salary_range(), pattern, msg=locale)

    def test_salaries_are_in_the_local_currency(self):
        # Mean full-time salary of professionals (ISCO 2), from the national earnings.
        expected = {"fr_BE": (40_000, 120_000), "de_CH": (80_000, 200_000), "en_GB": (35_000, 100_000),
                    "es_MX": (150_000, 600_000), "es_CO": (25_000_000, 120_000_000),
                    "es_CL": (10_000_000, 50_000_000), "en_IE": (40_000, 120_000)}
        for locale, (low, high) in expected.items():
            mean = _load_conditions()[locale]["salary"]["base"]["2"]["*"]
            self.assertTrue(low < mean < high, msg=(locale, mean))

    def test_amounts_are_rounded_to_the_currency(self):
        fake, _ = make("es_CO")
        for _ in range(20):
            low, high = fake.job_salary_bounds()
            self.assertEqual((low % 500_000, high % 500_000), (0, 0), msg=(low, high))

    def test_minimum_wage(self):
        self.assertIsNone(_load_conditions()["de_CH"]["minimum_wage"])  # set by collective agreements
        self.assertIsNone(_load_conditions()["de_AT"]["minimum_wage"])
        minimum = _load_conditions()["en_GB"]["minimum_wage"]
        self.assertGreater(minimum, 20_000)
        fake, provider = make("en_GB")
        conditions = provider._local_conditions()
        for _ in range(50):
            posting = fake.job_occupation_posting(sector="Hotels and restaurants")
            spec = conditions["contracts"][posting["work_type"]]
            if spec["salary_factor"] == 1 and spec["employee"]:
                self.assertGreaterEqual(posting["salary_min"], minimum)

    def test_contract_mix_from_the_labour_force_survey(self):
        # Countries with Eurostat earnings adapt their mix to the ISCO group; the others do not.
        weights = _load_conditions()["fr_BE"]["contract_weights"]
        self.assertNotEqual(weights["2"], weights["9"])
        weights = _load_conditions()["es_MX"]["contract_weights"]
        self.assertEqual(weights["2"], weights["9"])

    def test_source_of_the_salaries(self):
        self.assertIn("Eurostat SES 2022", _load_conditions()["fr_CH"]["salary_source"])
        self.assertIn("OECD", _load_conditions()["fr_CA"]["salary_source"])


class FrenchSpeakingCountriesTests(unittest.TestCase):
    def setUp(self):
        Faker.seed(7)

    def test_gender_mark_of_the_country(self):
        fake, _ = make("fr_BE")
        self.assertTrue(fake.job_posting()["job_title"].endswith(" (H/F/X)"))
        fake, _ = make("fr_CH")
        self.assertTrue(fake.job_posting()["job_title"].endswith(" (H/F)"))
        fake, _ = make("fr_CA")
        for _ in range(20):
            self.assertNotRegex(fake.job_posting()["job_title"], r"\((H/F|H/F/X)\)$")

    def test_local_diplomas_instead_of_the_french_ones(self):
        for locale in ("fr_BE", "fr_CH", "fr_CA"):
            fake, provider = make(locale)
            conditions = provider._local_conditions()
            diplomas = {name.format(field=field) for names in conditions["qualifications"].values()
                        for name in names for field in conditions["fields_of_study"].values()}
            for _ in range(30):
                self.assertIn(fake.job_posting()["qualification"], diplomas, msg=locale)

    def test_nace_class_outside_france(self):
        fake, _ = make("fr_BE")
        codes = {fake.job_occupation_posting()["company_naf"] for _ in range(30)} - {None}
        self.assertTrue(codes)
        self.assertTrue(all(re.fullmatch(r"\d\d\.\d\d", code) for code in codes), codes)
        fake, _ = make("fr_FR")
        self.assertRegex(fake.job_occupation_posting()["company_naf"], r"^\d\d\.\d\d[A-Z]$")

    def test_local_city_names(self):
        fake, _ = make("fr_BE")
        cities = {fake.job_location()["city"] for _ in range(300)}
        self.assertTrue({"Bruxelles", "Anvers"} <= cities)
        self.assertFalse(cities & {"Brussels", "Antwerp", "Antwerpen"})
        fake, _ = make("fr_CA")
        self.assertIn("Montréal", {fake.job_location()["city"] for _ in range(300)})

    def test_quebec_alias(self):
        self.assertEqual(_conditions_locale("fr_QC"), "fr_CA")
        self.assertEqual(_conditions_locale("fr-CA"), "fr_CA")
        self.assertIsNone(_conditions_locale("fr_FR"))
        self.assertIsNone(_conditions_locale("en_IN"))
        self.assertIsNone(_conditions_locale(None))


class SwissLocalesTests(unittest.TestCase):
    def test_city_names_in_each_language(self):
        Faker.seed(11)
        names = {}
        for locale in ("fr_CH", "de_CH", "it_CH"):
            fake, _ = make(locale)
            names[locale] = {fake.job_location()["city"] for _ in range(300)}
        self.assertIn("Genève", names["fr_CH"])
        self.assertIn("Genf", names["de_CH"])
        self.assertIn("Ginevra", names["it_CH"])
        self.assertIn("Zürich", names["de_CH"])

    def test_same_salaries_in_every_language(self):
        conditions = _load_conditions()
        self.assertEqual(conditions["fr_CH"]["salary"], conditions["de_CH"]["salary"])
        self.assertEqual(conditions["de_CH"]["salary"], conditions["it_CH"]["salary"])


class CompaniesOfTheCountryTests(unittest.TestCase):
    def test_real_companies_of_the_country(self):
        countries = _load_companies()["countries"]
        for locale, (country, *_rest) in COUNTRIES.items():
            self.assertIn(country, countries, msg=locale)
        Faker.seed(3)
        fake, provider = make("de_AT")
        names = set(provider.job_companies)
        real = [posting["company"]["company"] for posting in (fake.job_posting() for _ in range(60))
                if posting["company"]["company"] in names]
        self.assertTrue(real)


class OtherLocalesTests(unittest.TestCase):
    def test_forced_occupation_locale_keeps_the_base_country(self):
        class FrenchJobs(JobsProvider):
            occupations_locale = "fr_FR"

        fake, provider = make("fr_BE", FrenchJobs)
        self.assertEqual(provider._local_conditions()["country"], "France")
        self.assertEqual(fake.job_location()["country"], "France")

    def test_language_without_country_conditions(self):
        # es_AR has no conditions of its own yet: those of Spain.
        fake, provider = make("es_AR")
        self.assertEqual(provider._local_conditions()["country"], "Spain")
        self.assertEqual(fake.job_posting()["salary_currency"], "EUR")


if __name__ == "__main__":
    unittest.main()
