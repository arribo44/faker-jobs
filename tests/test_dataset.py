"""
Tests for job_dataset(), make_dataset() and `python -m faker_jobs export`:
employers and their postings as two linked tables, with a lifecycle.
"""
import collections
import csv
import datetime
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from faker import Faker

from faker_jobs import JobsProvider
from faker_jobs.__main__ import main
from faker_jobs.candidates import APPLICATION_FIELDS, CANDIDATE_FIELDS
from faker_jobs.dataset import COMPANY_FIELDS, POSTING_FIELDS, SINGLE_SITE_EMPLOYEES, JobDataset, make_dataset

START, END = datetime.date(2025, 1, 1), datetime.date(2026, 10, 31)


def make(locale="fr_FR", seed=20261113):
    Faker.seed(seed)
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    return fake


class DatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make().job_dataset(postings=1500, companies=150, start_date=START, end_date=END)
        cls.companies = {row["company_id"]: row for row in cls.data.companies}

    def test_tables(self):
        self.assertEqual(len(self.data.postings), 1500)
        self.assertGreaterEqual(len(self.data.companies), 150)
        self.assertTrue(all(tuple(row) == COMPANY_FIELDS for row in self.data.companies))
        self.assertTrue(all(tuple(row) == POSTING_FIELDS for row in self.data.postings))
        self.assertEqual(len(self.companies), len(self.data.companies))  # unique ids
        self.assertEqual(len({row["job_id"] for row in self.data.postings}), 1500)
        self.assertTrue(all(row["company_id"] in self.companies for row in self.data.postings))

    def test_employers_publish_several_postings(self):
        counts = collections.Counter(row["company_id"] for row in self.data.postings)
        self.assertGreater(counts.most_common(1)[0][1], 20)
        self.assertGreater(len(counts), 100)

    def test_employers_are_consistent(self):
        real = [row for row in self.data.companies if row["real"]]
        self.assertTrue(real)
        self.assertEqual(len({(row["name"], row["website"]) for row in real}), len(real))
        for row in self.data.postings:
            company = self.companies[row["company_id"]]
            self.assertEqual(row["sector"], company["sector"])
            self.assertEqual(row["salary_currency"], "EUR")
            self.assertEqual(row["country"], "France")
            if company["employees"] <= SINGLE_SITE_EMPLOYEES:
                self.assertEqual(row["city"], company["city"], company)

    def test_lifecycle(self):
        statuses = collections.Counter(row["status"] for row in self.data.postings)
        self.assertEqual(set(statuses), {"open", "filled", "expired"})
        self.assertGreater(statuses["filled"], statuses["expired"])
        for row in self.data.postings:
            posted = datetime.date.fromisoformat(row["posted_date"])
            self.assertTrue(START <= posted <= END, row)
            if row["status"] == "open":
                self.assertIsNone(row["closed_date"])
            else:
                closed = datetime.date.fromisoformat(row["closed_date"])
                self.assertTrue(posted < closed <= END, row)
        seasonal = [row for row in self.data.postings if row["work_type"] == "CDD saisonnier" and not row["repost_of"]]
        self.assertTrue(seasonal)
        self.assertTrue(all(3 <= int(row["posted_date"][5:7]) <= 9 for row in seasonal))

    def test_recruiters(self):
        by_company = collections.defaultdict(set)
        for row in self.data.postings:
            by_company[row["company_id"]].add((row["contact_person"], row["contact_email"], row["contact"]))
        for company_id, contacts in by_company.items():
            company = self.companies[company_id]
            self.assertLessEqual(len(contacts), 1 if company["employees"] <= 50 else 4, company)
            domains = {email.split("@")[1] for _, email, _ in contacts}
            self.assertEqual(len(domains), 1, contacts)
            if company["website"]:
                self.assertIn(domains.pop(), company["website"].lower())
            for _name, email, _ in contacts:
                self.assertRegex(email, r"^[a-z0-9.]+@[a-z0-9.-]+\.[a-z]+$")
        self.assertTrue(any(len(contacts) > 1 for contacts in by_company.values()))

    def test_reposts(self):
        by_id = {row["job_id"]: row for row in self.data.postings}
        reposts = [row for row in self.data.postings if row["repost_of"] is not None]
        self.assertTrue(60 < len(reposts) < 200, len(reposts))
        for row in reposts:
            first = by_id[row["repost_of"]]
            self.assertEqual((row["company_id"], row["job_title"], row["salary_min"]),
                             (first["company_id"], first["job_title"], first["salary_min"]))
            self.assertNotEqual(row["job_portal"], first["job_portal"])
            self.assertGreaterEqual(row["posted_date"], first["posted_date"])

    def test_export(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.data.to_csv(directory)
            self.assertEqual([os.path.basename(path) for path in paths], ["companies.csv", "postings.csv"])
            with open(paths[1], encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1500)
            self.assertEqual(tuple(rows[0]), POSTING_FIELDS)
            paths = self.data.to_jsonl(directory)
            with open(paths[0], encoding="utf-8") as f:
                companies = [json.loads(line) for line in f]
            self.assertEqual(companies, self.data.companies)


class DatasetOptionsTests(unittest.TestCase):
    def test_reproducible(self):
        first = make(seed=7).job_dataset(postings=200)
        self.assertEqual(make(seed=7).job_dataset(postings=200), first)
        self.assertEqual(make_dataset("de_DE", 100, seed=3), make_dataset("de_DE", 100, seed=3))

    def test_defaults(self):
        data = make("en_US").job_dataset(postings=300)
        self.assertGreaterEqual(len(data.companies), 30)
        self.assertEqual(data.postings[0]["salary_currency"], "USD")
        self.assertEqual(make().job_dataset(postings=0), JobDataset())
        data = make().job_dataset(postings=50, repost_rate=0)
        self.assertFalse(any(row["repost_of"] for row in data.postings))

    def test_dirty(self):
        clean = make_dataset({"fr_FR": 0.5, "de_DE": 0.5}, 1000, seed=3)
        self.assertEqual(clean.defects, [])
        data = make_dataset({"fr_FR": 0.5, "de_DE": 0.5}, 1000, seed=3, dirty=0.1)
        self.assertEqual(make_dataset({"fr_FR": 0.5, "de_DE": 0.5}, 1000, seed=3, dirty=0.1), data)
        kinds = collections.Counter(defect["kind"] for defect in data.defects)
        self.assertLessEqual({"typo", "missing", "monthly_salary", "date_format", "duplicate", "name_variant"},
                             set(kinds))
        duplicates = [defect for defect in data.defects if defect["kind"] == "duplicate"]
        self.assertEqual(len(data.postings), 1000 + len(duplicates))
        self.assertTrue(80 < sum(kinds.values()) - kinds["name_variant"] / 2 < 160)
        postings = {str(row["job_id"]): row for row in data.postings}
        companies = {row["company_id"]: row for row in data.companies}
        self.assertEqual(len(postings), len(data.postings))  # ids stay unique
        self.assertTrue(all(row["company_id"] in companies for row in data.postings))
        for defect in data.defects:
            if defect["table"] == "companies":
                row = companies[defect["id"]]
                if defect["field"] == "name":
                    self.assertNotEqual(row["name"], defect["original"])
                continue
            row = postings[defect["id"]]
            if defect["kind"] == "duplicate":
                first = postings[defect["original"]]
                self.assertEqual((row["company_id"], row["occupation_code"], row["repost_of"]),
                                 (first["company_id"], first["occupation_code"], None))
            elif defect["kind"] == "missing":
                self.assertIn(row[defect["field"]], (None, ""))
            elif defect["kind"] == "monthly_salary":
                self.assertAlmostEqual(row[defect["field"]], int(defect["original"]) / 12, delta=10)
            elif defect["kind"] == "date_format":
                self.assertNotRegex(row["posted_date"], r"^\d{4}-\d{2}-\d{2}$")
            else:
                self.assertNotEqual(str(row[defect["field"]]), defect["original"])
        with tempfile.TemporaryDirectory() as directory:
            paths = data.to_csv(directory)
            self.assertEqual([os.path.basename(path) for path in paths],
                             ["companies.csv", "postings.csv", "defects.csv"])
        with self.assertRaises(ValueError):
            make().job_dataset(postings=10, dirty=1.5)

    def test_salaries_over_time(self):
        data = make_dataset("es_AR", 600, start_date="2024-11-01", end_date="2026-10-31", seed=2)
        first = sorted(row["salary_min"] for row in data.postings if row["posted_date"] < "2025-07-01")
        last = sorted(row["salary_min"] for row in data.postings if row["posted_date"] >= "2026-03-01")
        self.assertLess(first[len(first) // 2], last[len(last) // 2] * 0.6)  # inflation in Argentina
        self.assertEqual({row["remote"] for row in data.postings}, {"on_site", "hybrid", "remote"})
        same_day = make_dataset("fr_FR", 50, start_date="2026-10-31", end_date="2026-10-31", seed=2)
        for row in same_day.postings:
            self.assertEqual(row["salary_min"] % 500, 0)
            self.assertLessEqual(row["salary_min"], row["salary_max"])

    def test_id_template(self):
        data = make().job_dataset(postings=300, start_date=START, end_date=END, id_template="JOB-{year}-{n:06d}")
        self.assertEqual([row["job_id"] for row in data.postings[:2]],
                         [f"JOB-{data.postings[0]['posted_date'][:4]}-000001",
                          f"JOB-{data.postings[1]['posted_date'][:4]}-000002"])
        reposts = [row for row in data.postings if row["repost_of"]]
        self.assertTrue(reposts)
        self.assertTrue(all(isinstance(row["repost_of"], str) for row in reposts))
        mixed = make_dataset({"fr_FR": 0.5, "de_DE": 0.5}, postings=100, seed=1, id_template="{country}{n:04d}")
        self.assertEqual([mixed.postings[i]["job_id"] for i in (0, 49, 50, 99)],
                         ["FR0001", "FR0050", "DE0051", "DE0100"])
        few = make().job_dataset(postings=100, id_template="{country}-###")
        self.assertEqual(len({row["job_id"] for row in few.postings}), 100)  # unique, drawn again when used
        with self.assertRaises(ValueError):
            make().job_dataset(postings=50, id_template="JOB-#")
        with self.assertRaises(ValueError):
            make().job_dataset(postings=5, id_template="")

    def test_several_locales(self):
        data = make_dataset({"fr_FR": 0.6, "pl_PL": 0.4}, postings=500, companies=100, seed=1)
        counts = collections.Counter(row["locale"] for row in data.postings)
        self.assertEqual(counts, {"fr_FR": 300, "pl_PL": 200})
        self.assertTrue(all(row["company_id"].startswith(f"{row['locale']}-") for row in data.postings))
        self.assertEqual({row["salary_currency"] for row in data.postings if row["locale"] == "pl_PL"}, {"PLN"})

    def test_bad_arguments(self):
        fake = make()
        for kwargs in ({"postings": -1}, {"companies": 1.5}, {"repost_rate": 1},
                       {"start_date": "2026-01-01", "end_date": "2025-01-01"}):
            with self.assertRaises(ValueError, msg=kwargs):
                fake.job_dataset(**kwargs)
        with self.assertRaises(ValueError):
            make_dataset({"fr_FR": -1})


class CandidatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = make().job_dataset(postings=800, candidates=1200, start_date=START, end_date=END)
        cls.postings = {row["job_id"]: row for row in cls.data.postings}
        cls.candidates = {row["candidate_id"]: row for row in cls.data.candidates}

    def test_tables(self):
        self.assertEqual(len(self.candidates), 1200)
        self.assertTrue(all(tuple(row) == CANDIDATE_FIELDS for row in self.data.candidates))
        self.assertTrue(all(tuple(row) == APPLICATION_FIELDS for row in self.data.applications))
        self.assertTrue(5 < len(self.data.applications) / 800 < 15)
        self.assertEqual(len({row["application_id"] for row in self.data.applications}), len(self.data.applications))
        pairs = [(row["job_id"], row["candidate_id"]) for row in self.data.applications]
        self.assertEqual(len(set(pairs)), len(pairs))  # one application of a candidate to a posting
        for row in self.data.applications:
            self.assertIn(row["job_id"], self.postings)
            self.assertIn(row["candidate_id"], self.candidates)
            self.assertTrue(0 <= row["match_score"] <= 100)

    def test_candidates(self):
        for row in self.data.candidates:
            self.assertEqual((row["country"], row["salary_currency"]), ("France", "EUR"))
            self.assertRegex(row["email"], r"^[a-z0-9.]+@[a-z0-9.-]+$")
            self.assertGreater(row["desired_salary"], 15000)
            self.assertIn(row["availability"], {"immediate", "1_month", "3_months", "6_months"})

    def test_statuses_follow_the_postings(self):
        by_posting = collections.defaultdict(list)
        for row in self.data.applications:
            by_posting[row["job_id"]].append(row)
        hired = [row["candidate_id"] for row in self.data.applications if row["status"] == "hired"]
        self.assertEqual(len(hired), len(set(hired)))  # hired once at most
        for job_id, posting in self.postings.items():
            rows = by_posting[job_id]
            statuses = collections.Counter(row["status"] for row in rows)
            posted = posting["posted_date"]
            last = posting["closed_date"] or END.isoformat()
            for row in rows:
                self.assertTrue(posted <= row["applied_date"] <= last, (posting, row))
                self.assertTrue(row["applied_date"] <= row["status_date"] <= last, (posting, row))
            if posting["status"] == "filled":
                self.assertEqual(statuses["hired"], 1, rows)
            else:
                self.assertEqual(statuses["hired"], 0)
            if posting["status"] == "expired":
                self.assertLessEqual(set(statuses), {"rejected", "withdrawn"})
        scores = collections.defaultdict(list)
        for row in self.data.applications:
            scores[row["status"] == "hired"].append(row["match_score"])
        self.assertGreater(sum(scores[True]) / len(scores[True]), sum(scores[False]) / len(scores[False]))

    def test_applicants_fit_the_posting(self):
        same = sum(self.candidates[row["candidate_id"]]["isco_code"] == self.postings[row["job_id"]]["isco_code"]
                   or self.candidates[row["candidate_id"]]["sector"] == self.postings[row["job_id"]]["sector"]
                   for row in self.data.applications)
        self.assertGreater(same / len(self.data.applications), 0.8)

    def test_options(self):
        self.assertEqual(make().job_dataset(postings=50).candidates, [])
        data = make_dataset({"fr_FR": 0.5, "de_DE": 0.5}, 200, candidates=100, applications=3, seed=2, dirty=0.1)
        self.assertEqual({row["candidate_id"][:6] for row in data.candidates}, {"fr_FR-", "de_DE-"})
        self.assertTrue(1 < len(data.applications) / 200 < 5)
        with tempfile.TemporaryDirectory() as directory:
            names = [os.path.basename(path) for path in data.to_csv(directory)]
        self.assertEqual(names, ["companies.csv", "postings.csv", "candidates.csv", "applications.csv",
                                 "defects.csv"])
        for kwargs in ({"candidates": -1}, {"applications": -2}, {"candidates": 1.5}):
            with self.assertRaises(ValueError, msg=kwargs):
                make().job_dataset(postings=10, **kwargs)
        candidate = make("de_DE").job_candidate(code=data.postings[-1]["occupation_code"], country="Austria")
        self.assertEqual((candidate["country"], candidate["occupation_code"]),
                         ("Österreich", data.postings[-1]["occupation_code"]))


class ExportCommandTests(unittest.TestCase):
    def test_export_command(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            main(["export", directory, "--locale", "es_ES", "--postings", "80", "--seed", "4", "--format", "jsonl"])
            self.assertIn("80 postings", output.getvalue())
            with open(os.path.join(directory, "postings.jsonl"), encoding="utf-8") as f:
                rows = [json.loads(line) for line in f]
        self.assertEqual(len(rows), 80)
        self.assertEqual({row["locale"] for row in rows}, {"es_ES"})

    def test_demo(self):
        with redirect_stdout(io.StringIO()) as output:
            main([])
        self.assertEqual(output.getvalue().count("Demo ("), 1)
        self.assertIn("Demo (en_US)", output.getvalue())
        with redirect_stdout(io.StringIO()) as output:
            main(["--locale", "fr_FR", "--locale", "pl_PL"])
        self.assertIn("Demo (fr_FR)", output.getvalue())
        self.assertIn("Demo (pl_PL)", output.getvalue())
        self.assertNotIn("Demo (en_US)", output.getvalue())

    def test_export_id_template(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            main(["export", directory, "--postings", "20", "--seed", "4", "--id-template", "REQ-{n:03d}"])
            with open(os.path.join(directory, "postings.csv"), encoding="utf-8", newline="") as f:
                ids = [row["job_id"] for row in csv.DictReader(f)]
        self.assertEqual(ids[:3], ["REQ-001", "REQ-002", "REQ-003"])

    def test_export_dirty(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            main(["export", directory, "--postings", "200", "--seed", "4", "--dirty", "0.2"])
            with open(os.path.join(directory, "defects.csv"), encoding="utf-8", newline="") as f:
                defects = list(csv.DictReader(f))
        self.assertGreater(len(defects), 20)

    def test_export_candidates(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as output:
            main(["export", directory, "--postings", "100", "--seed", "4", "--candidates", "80"])
            self.assertIn("80 candidates", output.getvalue())
            self.assertTrue(os.path.exists(os.path.join(directory, "applications.csv")))

    def test_export_errors(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["export", directory, "--locale", "fr_FR:x"])


if __name__ == "__main__":
    unittest.main()
