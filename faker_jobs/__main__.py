"""
Main module for faker_jobs: `python -m faker_jobs` prints a demo of the
provider in English (en_US), or in the locales given with --locale;
`python -m faker_jobs export` writes a dataset of employers and their
postings (see faker_jobs/dataset.py):

    python -m faker_jobs
    python -m faker_jobs --locale fr_FR --locale de_DE
    python -m faker_jobs export out/ --locale fr_FR --postings 10000 --companies 800 --seed 42
    python -m faker_jobs export out/ --locale fr_FR:0.6 --locale de_DE:0.4 --format jsonl
    python -m faker_jobs export out/ --id-template "JOB-{year}-{n:06d}"
    python -m faker_jobs export out/ --dirty 0.1
    python -m faker_jobs export out/ --candidates 2000 --applications 12
"""
import argparse
import sys

from faker import Faker

from faker_jobs import JobsProvider
from faker_jobs.dataset import make_dataset


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
    print(f"  qualification: {jobs.job_qualification()}")
    print(f"  experience: {jobs.job_experience()}")
    print(f"  salary: {jobs.job_salary_range()}")
    print(f"  work type: {jobs.job_work_type()}")
    print(f"  benefits: {', '.join(jobs.job_benefits())}")

    print("\n--- Company / location ---")
    print(f"  {jobs.job_company_profile()}")
    print(f"  {jobs.job_location()}")

    print("\n--- Occupations (ROME 4.0 / ESCO, in the locale's language) ---")
    for _ in range(3):
        sector = jobs.job_activity_sector()
        print(f"  - {sector}: {jobs.job_occupation_title(sector=sector)}")
    occupation = jobs.job_occupation_record()
    print(f"  {occupation['code']} {occupation['title']} ({occupation['sector']})")
    print(f"  skills: {'; '.join(jobs.job_occupation_skills(code=occupation['code'], count=3))}")
    occupation_posting = jobs.job_occupation_posting()
    naf = occupation_posting["company_naf"]
    print(f"  posting: {occupation_posting['job_title']} at {occupation_posting['company']['company']} "
          f"({occupation_posting['company_sector']}, {occupation_posting['company_size']} employees"
          f"{f', NAF {naf} ' + str(occupation_posting['company']['industry']) if naf else ''}), "
          f"demand {occupation_posting['occupation']['demand']}")
    print(f"  {occupation_posting['work_type']}, {occupation_posting['experience']}, "
          f"{occupation_posting['salary_range']} ({occupation_posting['seniority']})")

    print("\n--- Job posting ---")
    posting = jobs.job_posting()
    print(f"  #{posting['job_id']} {posting['job_title']} ({posting['work_type']}) at {posting['company']['company']}")
    print(f"  {posting['role']}: {posting['responsibilities'][:80]}...")
    print(f"  {posting['location']['city']}, {posting['location']['country']} - {posting['salary_range']}")
    print(f"  Posted {posting['job_posting_date']} on {posting['job_portal']}, "
          f"contact: {posting['contact_person']} {posting['contact']}")

    print("\n--- Posting text ---")
    print(jobs.job_posting_text(occupation_posting))


def parse_locales(values: list[str]) -> dict[str, float]:
    """{locale: share} of the --locale options ('fr_FR' or 'fr_FR:0.6')."""
    locales = {}
    for value in values:
        locale, _, share = value.partition(":")
        try:
            locales[locale] = float(share) if share else 1.0
        except ValueError:
            raise argparse.ArgumentTypeError(f"bad --locale {value!r}: expected LOCALE or LOCALE:SHARE") from None
    return locales


def export(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="python -m faker_jobs export",
                                     description="Write a dataset of employers and their job postings.")
    parser.add_argument("directory", help="output directory (companies.csv and postings.csv, or .jsonl)")
    parser.add_argument("--locale", action="append", default=[],
                        help="Faker locale, or LOCALE:SHARE of the postings; repeat it to mix (default en_US)")
    parser.add_argument("--postings", type=int, default=1000, help="number of postings (default 1000)")
    parser.add_argument("--companies", type=int, default=None, help="number of employers (default postings / 10)")
    parser.add_argument("--start-date", default="-2y", help="first publication date (ISO date or '-2y')")
    parser.add_argument("--end-date", default="today", help="last publication date, and the date of the status")
    parser.add_argument("--repost-rate", type=float, default=0.08, help="share of republished postings")
    parser.add_argument("--format", choices=("csv", "jsonl"), default="csv")
    parser.add_argument("--seed", type=int, default=None, help="random seed (reproducible output)")
    parser.add_argument("--id-template", default=None,
                        help="job ids from a template: # digit, ? letter, * either, {year} {month} {day} "
                        "{date:%%y%%m%%d} {country} {locale} {n:06d} (default: 15-16 digit numbers)")
    parser.add_argument("--dirty", type=float, default=0.0,
                        help="share of the rows with a defect of real-world data (0 to 1; default 0), "
                        "listed in defects.csv")
    parser.add_argument("--candidates", type=int, default=0,
                        help="number of job seekers applying to the postings (candidates.csv, applications.csv)")
    parser.add_argument("--applications", type=float, default=10.0,
                        help="mean number of applications a posting (default 10)")
    args = parser.parse_args(argv)
    try:
        locales = parse_locales(args.locale or ["en_US"])
        dataset = make_dataset(locales, args.postings, args.companies, args.start_date, args.end_date,
                               args.repost_rate, args.seed, args.id_template, args.dirty,
                               args.candidates, args.applications)
    except (ValueError, AttributeError, argparse.ArgumentTypeError) as error:
        parser.error(str(error))  # AttributeError: an unknown Faker locale
    paths = dataset.to_csv(args.directory) if args.format == "csv" else dataset.to_jsonl(args.directory)
    extra = f", {len(dataset.candidates)} candidates, {len(dataset.applications)} applications" \
        if dataset.candidates else ""
    print(f"{len(dataset.companies)} companies, {len(dataset.postings)} postings{extra} -> {', '.join(paths)}")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["export"]:
        export(argv[1:])
        return
    parser = argparse.ArgumentParser(
        prog="python -m faker_jobs",
        description="Print a demo of the provider; 'python -m faker_jobs export --help' writes datasets.",
    )
    parser.add_argument("--locale", action="append", default=[],
                        help="Faker locale of the demo; repeat it for several (default en_US)")
    args = parser.parse_args(argv)
    for locale in args.locale or ["en_US"]:
        try:
            demo(locale)
        except AttributeError:
            parser.error(f"unknown Faker locale {locale!r}")


if __name__ == "__main__":
    main()
