"""
Tests for the Portuguese, Dutch and Polish occupations (ESCO) and the
conditions of Portugal, the Netherlands, Poland, Brazil (pt_BR) and
Dutch-speaking Belgium (nl_BE).
"""
import re
import unittest

from faker import Faker

from faker_jobs import OCCUPATION_LOCALES, JobsProvider, _load_conditions


def make(locale):
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    return fake, JobsProvider(fake)


class NewLanguagesTests(unittest.TestCase):
    def setUp(self):
        Faker.seed(20261113)

    def test_occupation_locales(self):
        self.assertTrue({"pt_PT", "nl_NL", "pl_PL"} <= set(OCCUPATION_LOCALES))
        english = set(make("en_US")[1].job_occupation_codes)
        for locale, language, sector in (("pt_PT", "pt", "Saúde"), ("nl_NL", "nl", "Gezondheidszorg"),
                                         ("pl_PL", "pl", "Ochrona zdrowia")):
            fake, provider = make(locale)
            self.assertEqual(provider._occupations["meta"]["language"], language)
            self.assertEqual(set(provider.job_occupation_codes), english)  # the same ESCO occupations
            self.assertIn(sector, provider.job_activity_sectors)
            self.assertNotIn(fake.job_role(), set(make("en_US")[1].job_roles))

    def test_gender_marks(self):
        for locale, mark in (("pt_PT", "(M/F)"), ("nl_NL", "(m/v/x)"), ("pl_PL", "(k/m)"), ("nl_BE", "(m/v/x)")):
            fake, _ = make(locale)
            titles = [fake.job_posting()["job_title"] for _ in range(10)]
            self.assertTrue(all(title.endswith(f" {mark}") for title in titles), titles)
        fake, _ = make("pt_BR")
        self.assertFalse(any(fake.job_posting()["job_title"].endswith("(M/F)") for _ in range(10)))

    def test_local_conditions(self):
        cases = {
            "pt_PT": ("Portugal", "EUR", r"^\d{1,3}(\.\d{3})* € - \d{1,3}(\.\d{3})* € brutos/ano$"),
            "nl_NL": ("Nederland", "EUR", r"^€ \d{1,3}(\.\d{3})* - € \d{1,3}(\.\d{3})* bruto per jaar$"),
            "pl_PL": ("Polska", "PLN", r"^\d{1,3}( \d{3})* - \d{1,3}( \d{3})* zł brutto rocznie$"),
            "pt_BR": ("Brasil", "BRL", r"^R\$ \d{1,3}(\.\d{3})* - R\$ \d{1,3}(\.\d{3})* por ano$"),
            "nl_BE": ("België", "EUR", r"^€ \d{1,3}(\.\d{3})* - € \d{1,3}(\.\d{3})* bruto per jaar$"),
        }
        for locale, (country, currency, salary) in cases.items():
            fake, provider = make(locale)
            conditions = provider._local_conditions()
            for _ in range(15):
                posting = fake.job_posting()
                self.assertEqual(posting["location"]["country"], country, locale)
                self.assertEqual(posting["salary_currency"], currency, locale)
                self.assertRegex(posting["salary_range"], salary)
                self.assertIn(posting["work_type"], conditions["contracts"])
                self.assertIn(posting["job_portal"], conditions["job_portals"]["all"])
            self.assertTrue(provider.job_companies, locale)

    def test_local_city_names(self):
        for locale, names in (("pl_PL", {"Warszawa", "Kraków"}), ("pt_PT", {"Lisboa"}), ("nl_NL", {"Den Haag"}),
                              ("nl_BE", {"Antwerpen", "Brussel"})):
            fake, _ = make(locale)
            cities = {fake.job_location()["city"] for _ in range(400)}
            self.assertTrue(names <= cities, (locale, names - cities))

    def test_nace_activities(self):
        for locale in ("pt_PT", "nl_NL", "pl_PL"):
            fake, _ = make(locale)
            codes = {fake.job_occupation_posting()["company_naf"] for _ in range(20)} - {None}
            self.assertTrue(codes and all(re.fullmatch(r"\d\d\.\d\d", code) for code in codes), (locale, codes))

    def test_salaries(self):
        conditions = _load_conditions()
        self.assertIn("Eurostat SES", conditions["nl_BE"]["salary_source"])
        self.assertIn("ILOSTAT", conditions["pt_BR"]["salary_source"])
        self.assertEqual(conditions["nl_BE"]["salary"], conditions["fr_BE"]["salary"])

    def test_neutral_conditions_in_the_new_languages(self):
        for locale, country, currency, ending in (("pt_PT", "Angola", "AOA", " AOA brutos por ano"),
                                                  ("nl_NL", "Suriname", "SRD", " bruto per jaar"),
                                                  ("pl_PL", "Ukraine", "UAH", " UAH brutto rocznie")):
            fake, _ = make(locale)
            posting = fake.job_posting(country=country)
            self.assertEqual(posting["salary_currency"], currency, locale)
            self.assertTrue(posting["salary_range"].endswith(ending), posting["salary_range"])

    def test_posting_text(self):
        for locale, word in (("pt_PT", "Remuneração"), ("nl_NL", "Salaris"), ("pl_PL", "Wynagrodzenie")):
            fake, _ = make(locale)
            self.assertIn(word, fake.job_posting_text())


if __name__ == "__main__":
    unittest.main()
