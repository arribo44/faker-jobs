"""
Main module for faker_jobs
Allows running the package as a module: python -m faker_jobs
"""
from faker import Faker

from faker_jobs import JobsProvider


def demo(locale: str) -> None:
    fake = Faker(locale)
    fake.add_provider(JobsProvider)
    # Typed handle on the provider: fake.job_role() & co. are added
    # dynamically by Faker, so type checkers can't see their signatures.
    jobs = JobsProvider(fake)

    print("=" * 60)
    print(f"Faker Jobs Provider - Demo ({locale})")
    print("=" * 60)

    print("\n--- Job titles / roles ---")
    for _ in range(5):
        title = jobs.job_title()
        print(f"  - {title}: {jobs.job_role(job_title=title)}")

    print("\n--- Role record ---")
    for key, value in jobs.job_role_record().items():
        print(f"  {key}: {value}")

    print("\n--- Requirements / conditions ---")
    qualification = jobs.job_qualification()
    print(f"  qualification: {qualification} ({jobs.job_qualification_name(qualification)})")
    print(f"  experience: {jobs.job_experience()}")
    print(f"  salary: {jobs.job_salary_range()}")
    print(f"  work type: {jobs.job_work_type()}")
    print(f"  benefits: {', '.join(jobs.job_benefits())}")

    print("\n--- Company / location ---")
    print(f"  {jobs.job_company_profile()}")
    print(f"  {jobs.job_location()}")

    print("\n--- Job posting ---")
    posting = jobs.job_posting()
    print(f"  #{posting['job_id']} {posting['role']} ({posting['work_type']}) at {posting['company']['company']}")
    print(f"  {posting['location']['city']}, {posting['location']['country']} - {posting['salary_range']}")
    print(f"  Posted {posting['job_posting_date']} on {posting['job_portal']}, "
          f"contact: {posting['contact_person']} {posting['contact']}")


def main() -> None:
    for locale in ["en_US", "fr_FR"]:
        demo(locale)


if __name__ == "__main__":
    main()
