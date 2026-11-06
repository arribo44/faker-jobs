"""
Tests for the locale-aware occupation methods (ROME 4.0 in French locales,
ESCO otherwise).
"""
import unittest

from faker import Faker

from faker_jobs import (
    CompanyProfile,
    JobsProvider,
    OccupationPosting,
    OccupationRecord,
    _gender_form,
    _occupation_locale,
)


def make_faker(locale):
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    return fake


def make_provider(locale):
    # Faker only registers methods: the list properties are read on the provider.
    return JobsProvider(Faker(locale))


class TestOccupationLocale(unittest.TestCase):
    def test_french_locales_use_rome(self):
        for locale in ("fr_FR", "fr_CA", "fr_CH", "fr-BE"):
            self.assertEqual(_occupation_locale(locale), "fr_FR", msg=locale)

    def test_other_locales_use_esco(self):
        for locale in ("en_US", "en_GB", "de_DE", None):
            self.assertEqual(_occupation_locale(locale), "en_US", msg=locale)

    def test_faker_locale_selects_the_data(self):
        self.assertIn("Santé", make_provider("fr_FR").job_activity_sectors)
        self.assertIn("Healthcare", make_provider("en_US").job_activity_sectors)
        self.assertIn("Healthcare", make_provider("de_DE").job_activity_sectors)

    def test_rome_codes_in_french_esco_ids_otherwise(self):
        self.assertIn("M1805", make_provider("fr_FR").job_occupation_codes)
        self.assertNotIn("M1805", make_provider("en_US").job_occupation_codes)

    def test_multi_locale_proxy_uses_each_locale(self):
        # Faker does not proxy add_provider() in multiple locale mode: add it to each locale.
        fake = Faker(["fr_FR", "en_US"])
        for locale in fake.locales:
            fake[locale].add_provider(JobsProvider)
        self.assertEqual(fake["fr_FR"].job_occupation_record(code="M1805")["sector"],
                         "Informatique et télécommunication")
        self.assertIn(fake["en_US"].job_occupation_record()["sector"], make_provider("en_US").job_activity_sectors)

    def test_occupations_locale_override(self):
        class FrenchJobs(JobsProvider):
            occupations_locale = "fr_FR"

        self.assertIn("Santé", FrenchJobs(Faker("en_US")).job_activity_sectors)

    def test_bad_occupations_locale(self):
        class BadJobs(JobsProvider):
            occupations_locale = "de_DE"

        # Faker reads the provider's properties on registration: the error shows up there.
        with self.assertRaisesRegex(ValueError, "occupations_locale"):
            Faker("en_US").add_provider(BadJobs)


class OccupationTests:
    """Shared by both locales (mixed into a TestCase below)."""

    locale = ""

    def setUp(self):
        Faker.seed(20261106)
        self.fake = make_faker(self.locale)
        self.provider = JobsProvider(self.fake)

    def test_35_activity_sectors_each_with_occupations(self):
        sectors = self.provider.job_activity_sectors
        self.assertEqual(len(sectors), 35)
        self.assertEqual(sectors, sorted(sectors))
        for sector in sectors:
            self.assertTrue(self.fake.job_occupation(sector=sector), msg=sector)

    def test_activity_sector_is_known(self):
        for _ in range(20):
            self.assertIn(self.fake.job_activity_sector(), self.provider.job_activity_sectors)

    def test_record_is_complete(self):
        for _ in range(50):
            record = self.fake.job_occupation_record()
            self.assertEqual(set(record), set(OccupationRecord.__annotations__))
            self.assertIn(record["code"], self.provider.job_occupation_codes)
            self.assertTrue(record["title"] and record["job_title"] and record["domain"])
            self.assertEqual(record["sector"], record["sectors"][0])
            self.assertTrue(set(record["sectors"]) <= set(self.provider.job_activity_sectors))

    def test_sector_restricts_the_occupation(self):
        sector = self.provider.job_activity_sectors[0]
        for _ in range(30):
            record = self.fake.job_occupation_record(sector=sector)
            self.assertEqual(record["sector"], sector)
            self.assertIn(sector, record["sectors"])

    def test_sector_is_case_insensitive(self):
        sector = self.provider.job_activity_sectors[0]
        self.assertEqual(self.fake.job_occupation_record(sector=f"  {sector.upper()} ")["sector"], sector)

    def test_unknown_sector_suggests(self):
        sector = self.provider.job_activity_sectors[0]
        with self.assertRaisesRegex(ValueError, "Did you mean"):
            self.fake.job_occupation(sector=sector[:-1])

    def test_record_by_code(self):
        code = self.provider.job_occupation_codes[0]
        record = self.fake.job_occupation_record(code=code.lower())
        self.assertEqual(record["code"], code)

    def test_unknown_code(self):
        with self.assertRaises(ValueError):
            self.fake.job_occupation_record(code="nope")

    def test_code_outside_sector(self):
        record = self.fake.job_occupation_record()
        other = next(s for s in self.provider.job_activity_sectors if s not in record["sectors"])
        with self.assertRaises(ValueError):
            self.fake.job_occupation_record(code=record["code"], sector=other)

    def test_job_title_belongs_to_occupation_titles(self):
        titles = {self.fake.job_occupation_title() for _ in range(200)}
        self.assertGreater(len(titles), 150)

    def test_skills_are_distinct_and_from_the_occupation(self):
        record = max((self.fake.job_occupation_record() for _ in range(20)), key=lambda r: len(r["skills"]))
        skills = self.fake.job_occupation_skills(code=record["code"], count=3)
        self.assertEqual(len(skills), 3)
        self.assertEqual(len(set(skills)), 3)
        self.assertTrue(set(skills) <= set(record["skills"]))
        self.assertEqual(sorted(self.fake.job_occupation_skills(code=record["code"], count=10_000)),
                         sorted(record["skills"]))

    def test_bad_skill_count(self):
        for count in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                self.fake.job_occupation_skills(count=count)

    def test_record_rome_attributes(self):
        for _ in range(30):
            record = self.fake.job_occupation_record()
            self.assertIsInstance(record["executive"], bool)
            self.assertIsInstance(record["regulated"], bool)
            self.assertTrue(set(record["riasec"]) <= set("RIASEC") and 1 <= len(record["riasec"]) <= 2)
            self.assertTrue(set(record["transitions"]) <= {"ecological", "digital", "demographic"})

    def test_title_gender_validation(self):
        with self.assertRaises(ValueError):
            self.fake.job_occupation_title(gender="X")

    def test_record_lists_are_copies(self):
        code = self.provider.job_occupation_codes[0]
        self.fake.job_occupation_record(code=code)["skills"].append("x")
        self.assertNotIn("x", self.fake.job_occupation_record(code=code)["skills"])

    # -- postings ---------------------------------------------------------------

    def test_posting_is_complete(self):
        for _ in range(30):
            posting = self.fake.job_occupation_posting()
            self.assertEqual(set(posting), set(OccupationPosting.__annotations__))
            self.assertEqual(set(posting["company"]), set(CompanyProfile.__annotations__))
            occupation = posting["occupation"]
            self.assertIn(self._posted_title_source(posting["job_title"], occupation["code"]),
                          self._titles(occupation["code"]))
            self.assertTrue(set(posting["skills"]) <= set(occupation["skills"]))
            self.assertEqual(len(posting["skills"]), min(5, len(occupation["skills"])))

    def _posted_title_source(self, job_title, code):
        """The occupation title a posting's job title was made from (overridden in French)."""
        return job_title

    def _titles(self, code):
        return self.provider._occupations["occupation_by_code"][code.lower()]["titles"]

    def test_posting_company_fits_the_occupation(self):
        fitted = 0
        for _ in range(50):
            posting = self.fake.job_occupation_posting()
            if posting["company_sector"] is None:
                self.assertIsNone(posting["company"]["sector"])
                self.assertTrue(posting["company"]["company"])
            else:
                fitted += 1
                self.assertIn(posting["company_sector"], posting["occupation"]["sectors"])
                self.assertIn(posting["company"]["company"],
                              self.provider._occupations["companies_by_sector"][posting["company_sector"]])
        self.assertGreater(fitted, 25)

    def test_posting_prefers_the_requested_sector(self):
        sectors = self.provider._occupations["companies_by_sector"]
        sector = max(sectors, key=lambda name: len(sectors[name]))
        for _ in range(20):
            posting = self.fake.job_occupation_posting(sector=sector)
            self.assertEqual(posting["occupation"]["sector"], sector)
            self.assertEqual(posting["company_sector"], sector)

    def test_posting_without_fitting_company_makes_one_up(self):
        sectors = self.provider._occupations["companies_by_sector"]
        lonely = next(occupation for occupation in self.provider._occupations["occupations"]
                      if not any(sectors.get(sector) for sector in occupation["sectors"]))
        posting = self.fake.job_occupation_posting(code=lonely["code"])
        self.assertIsNone(posting["company_sector"])
        self.assertIsNone(posting["company"]["ticker"])

    def test_posting_options(self):
        posting = self.fake.job_occupation_posting(country="France", skills=2)
        self.assertEqual(posting["location"]["country"], "France")
        self.assertLessEqual(len(posting["skills"]), 2)
        with self.assertRaises(ValueError):
            self.fake.job_occupation_posting(skills=-1)


class TestRomeOccupations(OccupationTests, unittest.TestCase):
    locale = "fr_FR"

    def test_rome_sheet(self):
        record = self.fake.job_occupation_record(code="J1506")
        self.assertEqual(record["title"], "Infirmier / Infirmière en soins généraux (IDE)")
        self.assertEqual(record["sector"], "Santé")
        self.assertIsNone(record["description"])
        self.assertTrue(record["skills"] and record["knowledge"] and record["soft_skills"])

    def test_1923_occupations(self):
        self.assertEqual(len(self.provider.job_occupation_codes), 1923)

    def _posted_title_source(self, job_title, code):
        # "Conducteur routier régional (H/F)" comes from "Conducteur routier régional / Conductrice ...".
        self.assertTrue(job_title.endswith(" (H/F)"), msg=job_title)
        masculine = job_title.removesuffix(" (H/F)")
        return next(title for title in self._titles(code) if _gender_form(title, "M") == masculine)

    def test_diplomas_are_qualifications_not_knowledge(self):
        record = self.fake.job_occupation_record(code="J1506")
        self.assertIn("Diplôme d'Etat d'infirmier (ière)", record["qualifications"])
        self.assertNotIn("Diplôme d'Etat d'infirmier (ière)", record["knowledge"])
        self.assertTrue(record["regulated"])

    def test_gendered_titles(self):
        # Every ROME title with both forms splits, except the few with several " / ".
        titles = [title for code in self.provider.job_occupation_codes for title in self._titles(code)]
        double = [title for title in titles if " / " in title]
        unsplit = [title for title in double if " / " in _gender_form(title, "F")]
        # Left as is: alternatives, not genders ("Responsable d'atelier en chimie / Pharmacie").
        self.assertLess(len(unsplit), 20)
        masculine = self.fake.job_occupation_title(sector="Santé", gender="M")
        feminine = self.fake.job_occupation_title(sector="Santé", gender="F")
        self.assertNotIn(" / ", masculine + feminine)

    def test_french_posting_conditions(self):
        portals = set()
        for _ in range(60):
            posting = self.fake.job_occupation_posting()
            occupation = posting["occupation"]
            self.assertEqual(posting["salary_currency"], "EUR")
            self.assertTrue(posting["salary_range"].endswith("€ brut/an"))
            self.assertLess(posting["salary_min"], posting["salary_max"])
            self.assertGreaterEqual(posting["salary_min"], 35_000 if occupation["executive"] else 22_000)
            self.assertEqual(posting["location"]["country"], "France")
            self.assertIn(posting["work_type"], {"CDI", "CDD", "Intérim", "Alternance", "Stage", "Freelance"})
            if occupation["qualifications"]:
                self.assertIn(posting["qualification"], occupation["qualifications"])
            if not occupation["executive"]:
                self.assertNotIn(posting["job_portal"], {"APEC", "Cadremploi"})
            self.assertEqual(posting["experience"] == "Débutant accepté", posting["experience_min"] == 0)
            portals.add(posting["job_portal"])
        self.assertGreater(len(portals), 5)
        self.assertEqual(self.fake.job_occupation_posting(country="Belgium")["location"]["country"], "Belgium")


class TestGenderForm(unittest.TestCase):
    def test_forms(self):
        cases = {
            "Conducteur / Conductrice d'engins agricoles": ("Conducteur d'engins agricoles",
                                                            "Conductrice d'engins agricoles"),
            "Conducteur routier régional / Conductrice routière régionale": ("Conducteur routier régional",
                                                                             "Conductrice routière régionale"),
            "Garde Forestier / Forestière": ("Garde Forestier", "Garde Forestière"),
            "Homme / Femme de pied": ("Homme de pied", "Femme de pied"),
            "Steward / Hôtesse de train": ("Steward de train", "Hôtesse de train"),
            "Homme sage-femme / Sage-femme": ("Homme sage-femme", "Sage-femme"),
            "Caviste affineur / Affineuse": ("Caviste affineur", "Caviste affineuse"),
            "Auxiliaire Vétérinaire Qualifié / Qualifiée (AVQ)": ("Auxiliaire Vétérinaire Qualifié (AVQ)",
                                                                  "Auxiliaire Vétérinaire Qualifiée (AVQ)"),
        }
        for title, (masculine, feminine) in cases.items():
            self.assertEqual(_gender_form(title, "M"), masculine)
            self.assertEqual(_gender_form(title, "F"), feminine)

    def test_other_shapes_are_unchanged(self):
        for title in ("Tractoriste agricole", "Chef / Cheffe de service infrastructure / Environnement",
                      "Analyste biologie/microbiologie en industrie"):
            self.assertEqual(_gender_form(title, "F"), title)


class TestEscoOccupations(OccupationTests, unittest.TestCase):
    locale = "en_US"

    def test_esco_occupations_have_english_descriptions(self):
        records = [self.fake.job_occupation_record() for _ in range(30)]
        self.assertTrue(all(record["description"] for record in records))
        self.assertGreater(len(self.provider.job_occupation_codes), 2000)

    def test_english_titles_ignore_gender(self):
        Faker.seed(1)
        title = self.fake.job_occupation_title(gender="F")
        Faker.seed(1)
        self.assertEqual(self.fake.job_occupation_title(), title)

    def test_english_posting_keeps_kaggle_conditions(self):
        posting = self.fake.job_occupation_posting()
        self.assertEqual(posting["salary_currency"], "USD")
        self.assertEqual(posting["occupation"]["qualifications"], [])


if __name__ == "__main__":
    unittest.main()
