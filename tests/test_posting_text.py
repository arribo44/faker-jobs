"""
Tests for job_posting_text(): the full text of a posting, in the language
of the occupation data.
"""
import unittest

from faker import Faker

from faker_jobs import JobsProvider
from faker_jobs.posting_text import TEXTS

LOCALES = {"fr_FR": "fr", "en_US": "en", "en_GB": "en", "de_DE": "de", "es_ES": "es", "it_IT": "it"}


def make_faker(locale):
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    return fake


class PostingTextTests(unittest.TestCase):
    def setUp(self):
        Faker.seed(20261108)

    def test_every_language_has_the_same_texts(self):
        keys = set(TEXTS["en"]) - {"list_separator", "lower_soft_skills"}
        for language, texts in TEXTS.items():
            with self.subTest(language=language):
                self.assertLessEqual(keys, set(texts))
                self.assertEqual(len(texts["months"]), 12)
                self.assertEqual(set(texts["transitions"]), {"ecological", "digital", "demographic"})

    def test_text_holds_the_posting_facts(self):
        for locale, language in LOCALES.items():
            fake = make_faker(locale)
            for _ in range(20):
                posting = fake.job_occupation_posting()
                text = fake.job_posting_text(posting)
                with self.subTest(locale=locale, job_title=posting["job_title"]):
                    first = text.splitlines()[0]
                    self.assertEqual(first.lower(), posting["job_title"].lower())
                    for value in (posting["company"]["company"], posting["location"]["city"],
                                  posting["salary_range"], posting["work_type"], posting["qualification"],
                                  posting["experience"], posting["contact_person"], posting["contact"],
                                  str(posting["job_id"]), posting["job_portal"]):
                        self.assertIn(value, text)
                    for skill in posting["skills"]:
                        self.assertIn(skill[1:], text)
                    for benefit in posting["benefits"]:
                        self.assertIn(benefit, text)
                    self.assertNotIn("{", text)
                    self.assertNotIn("None", text)
                    months = TEXTS[language]["months"]
                    self.assertIn(months[posting["job_posting_date"].month - 1], text)

    def test_job_posting_shape_is_accepted(self):
        for locale in LOCALES:
            fake = make_faker(locale)
            posting = fake.job_posting()
            text = fake.job_posting_text(posting)
            with self.subTest(locale=locale):
                for activity in posting["responsibilities"].split("; "):
                    self.assertIn(activity[1:], text)
                self.assertIn(posting["salary_range"], text)

    def test_markdown(self):
        fake = make_faker("fr_FR")
        text = fake.job_posting_text(markdown=True)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("# "))
        self.assertTrue(lines[1].startswith("**") and lines[1].endswith("**"))
        self.assertEqual(sum(line.startswith("## ") for line in lines), 5)
        plain = make_faker("fr_FR").job_posting_text()
        self.assertNotIn("## ", plain)
        self.assertNotIn("**", plain)

    def test_default_posting_and_seed(self):
        texts = []
        for _ in range(2):
            Faker.seed(7)
            texts.append(make_faker("de_DE").job_posting_text())
        self.assertEqual(texts[0], texts[1])
        self.assertIn("(m/w/d)", texts[0].splitlines()[0])

    def test_rome_sheets_without_description(self):
        fake = make_faker("fr_FR")
        posting = fake.job_occupation_posting()
        self.assertIsNone(posting["occupation"]["description"])
        self.assertIn(f"fiche ROME {posting['occupation']['code']}", fake.job_posting_text(posting))

    def test_german_soft_skills_keep_their_capital(self):
        fake = make_faker("de_DE")
        for _ in range(10):
            text = fake.job_posting_text()
            line = next((line for line in text.splitlines() if line.startswith("- Persönliche Stärken: ")), None)
            if line:
                self.assertTrue(line.split(": ", 1)[1][0].isupper())


if __name__ == "__main__":
    unittest.main()
