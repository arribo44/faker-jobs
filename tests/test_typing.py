"""
Typing checks for the public API.

Run by pytest (the TypedDicts must describe exactly the keys the provider
really returns) and by mypy (the documented ways of getting typed results
must type-check, see the README's "Type hints" section).
"""
import datetime
import unittest
from typing import assert_type

from faker import Faker

from faker_jobs import CompanyProfile, JobPosting, JobsProvider, LocationRecord, RoleRecord


def make_faker() -> Faker:
    fake = Faker("fr_FR")
    fake.add_provider(JobsProvider)
    return fake


class TestTypedDictsMatchRuntime(unittest.TestCase):
    def setUp(self) -> None:
        Faker.seed(1)
        self.fake = make_faker()

    def test_role_record_keys(self) -> None:
        self.assertEqual(set(self.fake.job_role_record()), set(RoleRecord.__annotations__))

    def test_location_keys(self) -> None:
        self.assertEqual(set(self.fake.job_location()), set(LocationRecord.__annotations__))

    def test_company_profile_keys(self) -> None:
        self.assertEqual(set(self.fake.job_company_profile()), set(CompanyProfile.__annotations__))

    def test_job_posting_keys(self) -> None:
        posting = self.fake.job_posting()
        self.assertEqual(set(posting), set(JobPosting.__annotations__))
        self.assertEqual(set(posting["location"]), set(LocationRecord.__annotations__))
        self.assertEqual(set(posting["company"]), set(CompanyProfile.__annotations__))


class TestDocumentedTypedUsage(unittest.TestCase):
    """The two ways of getting typed results documented in the README.
    assert_type() is a no-op at runtime; mypy checks it statically."""

    def test_annotating_the_result_of_a_faker_call(self) -> None:
        fake = make_faker()
        posting: JobPosting = fake.job_posting()
        assert_type(posting["salary_min"], int)
        assert_type(posting["benefits"], list[str])

    def test_calling_the_provider_directly(self) -> None:
        jobs = JobsProvider(make_faker())
        assert_type(jobs.job_role_record(), RoleRecord)
        assert_type(jobs.job_location(), LocationRecord)
        assert_type(jobs.job_company_profile(), CompanyProfile)
        posting = jobs.job_posting()
        assert_type(posting, JobPosting)
        assert_type(posting["company"], CompanyProfile)
        assert_type(posting["job_posting_date"], datetime.date)
        assert_type(jobs.job_salary_bounds(), tuple[int, int])
        assert_type(jobs.job_title(), str)


if __name__ == "__main__":
    unittest.main()
