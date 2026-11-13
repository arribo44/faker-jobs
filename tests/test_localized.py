"""
Tests for the generic methods (job_title, job_role_record, job_salary_range,
job_company_profile...) in the German, Spanish, French and Italian locales:
the occupations in the language, local conditions and made-up companies.
"""
import unittest

from faker import Faker

from faker_jobs import JobsProvider, _country_name


def make(locale, provider=JobsProvider):
    fake = Faker(locale)
    fake.add_provider(provider)
    return fake, provider(fake)


class LocalizedTests:
    """Shared by the localized locales (mixed into a TestCase below)."""

    locale = ""
    country = ""
    currency_sign = "€"
    # Occupation names also English ones (loanwords: sommelier, manager...).
    english_overlap = 25

    def setUp(self):
        Faker.seed(20261106)
        self.fake, self.provider = make(self.locale)
        self.conditions = self.provider._local_conditions()
        self.english = JobsProvider(Faker("en_US"))

    def test_titles_and_roles_are_occupations(self):
        titles, roles = set(self.provider.job_titles), set(self.provider.job_roles)
        self.assertGreater(len(roles), 1900)
        self.assertLess(len(roles & set(self.english.job_roles)), self.english_overlap)
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
        qualifications = {name.format(field=field) for names in self.conditions["qualifications"].values()
                          for name in names for field in self.conditions["fields_of_study"].values()}
        portals = set(self.conditions["job_portals"]["all"]) | set(self.conditions["job_portals"].get("executive", []))
        for _ in range(20):
            self.assertIn(self.fake.job_qualification(), qualifications)
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

    def test_location_in_the_country(self):
        self.assertEqual(self.fake.job_location()["country"], self.country)
        # Another country by its name in the language (Wikidata labels), its English one too.
        language = self.provider._language
        brazil = _country_name("Brazil", language)
        self.assertEqual(self.fake.job_location(country="Brazil")["country"], brazil)
        self.assertEqual(self.fake.job_location(country=brazil)["country"], brazil)

    def test_companies_in_activity_sectors(self):
        self.assertEqual(self.provider.job_sectors, self.provider.job_activity_sectors)
        sector = self.provider.job_activity_sectors[0]
        for _ in range(10):
            profile = self.fake.job_company_profile(sector=sector)
            self.assertEqual(profile["sector"], sector)
            self.assertIsNone(profile["ticker"])
            self.assertTrue(profile["website"] or profile["ceo"])  # real, or made up with a CEO
        self.assertTrue(self.fake.job_company())
        self.assertEqual(self.fake.job_company_profile(company="Acme")["company"], "Acme")
        with self.assertRaisesRegex(ValueError, "Unknown activity sector"):
            self.fake.job_company(sector="Piracy")

    def test_posting_is_local(self):
        posting = self.fake.job_posting()
        self.assertEqual(posting["salary_currency"], self.conditions["currency"])
        self.assertEqual(posting["location"]["country"], self.country)


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


class TestPortugueseLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "pt_PT", "Portugal"


class TestBrazilianSpelling(unittest.TestCase):
    def test_brazilian_portuguese(self):
        from faker_jobs.pt_br import to_brazilian

        self.assertEqual(to_brazilian("Rececionista de hotel"), "Recepcionista de hotel")
        self.assertEqual(to_brazilian("Controlo eletrónico da equipa"), "Controle eletrônico da equipe")
        self.assertEqual(to_brazilian("COMO CANDIDATAR-SE"), "COMO SE CANDIDATAR")
        self.assertEqual(to_brazilian("também, Antónia, género"), "também, Antônia, gênero")
        brazil, portugal = JobsProvider(Faker("pt_BR")), JobsProvider(Faker("pt_PT"))
        brazilian, european = set(brazil.job_titles), set(portugal.job_titles)
        self.assertIn("Recepcionista", " ".join(brazilian))
        self.assertNotIn("Rececionista", " ".join(brazilian))
        self.assertIn("Rececionista", " ".join(european))
        self.assertEqual(brazil.job_activity_sectors, portugal.job_activity_sectors)
        Faker.seed(3)
        fake = Faker("pt_BR")
        fake.add_provider(JobsProvider)
        text = fake.job_posting_text()
        self.assertNotIn("equipa", text)
        self.assertNotIn("está a recrutar", text)
        dutch = JobsProvider(Faker("nl_NL"))
        self.assertIn("directieassistent", dutch.job_roles)
        self.assertIn("executive assistant", dutch.job_titles)


class TestDutchLocalized(LocalizedTests, unittest.TestCase):
    locale, country = "nl_NL", "Nederland"
    english_overlap = 80   # English words in Dutch use (data scientist, sommelier, producer, ombudsman...)


class TestPolishLocalized(LocalizedTests, unittest.TestCase):
    locale, country, currency_sign = "pl_PL", "Polska", "zł"


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
        # Other countries by their Italian name (no Italian name of their cities: English).
        self.assertEqual(self.fake.job_location(country="Germany")["country"], "Germania")
        german = {self.fake.job_location(country="Germania")["city"] for _ in range(300)}
        self.assertIn("Munich", german)
        self.assertNotIn("München", german)


class TestGermanPlaceNames(unittest.TestCase):
    def test_local_city_names(self):
        Faker.seed(3)
        fake, _ = make("de_DE")
        cities = {fake.job_location()["city"] for _ in range(300)}
        self.assertTrue({"München", "Köln"} <= cities)
        self.assertFalse(cities & {"Munich", "Cologne"})


class TestDefaultDiplomas(unittest.TestCase):
    def test_field_of_study_follows_the_sector(self):
        Faker.seed(5)
        fake, provider = make("de_DE")
        conditions = provider._local_conditions()
        self.assertEqual(set(conditions["fields_of_study"]), set(provider.job_activity_sectors))
        with_field = 0
        for _ in range(200):
            posting = fake.job_occupation_posting(sector="IT und Telekommunikation")
            self.assertNotIn("{", posting["qualification"])
            if "Bereich" in posting["qualification"]:
                with_field += 1
                self.assertTrue(posting["qualification"].endswith(" Informatik"), posting["qualification"])
        self.assertGreater(with_field, 20)


class TestForcedOccupationLocale(unittest.TestCase):
    def test_forced_occupation_locale(self):
        class FrenchJobs(JobsProvider):
            occupations_locale = "fr_FR"

        fake, provider = make("en_US", FrenchJobs)
        self.assertTrue(fake.job_salary_range().endswith("€ brut/an"))
        self.assertEqual(fake.job_location()["country"], "France")


if __name__ == "__main__":
    unittest.main()
