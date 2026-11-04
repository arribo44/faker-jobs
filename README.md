# Faker Jobs Provider

**A custom [Faker](https://faker.readthedocs.io/) provider for generating realistic fake job-market data: job titles and roles with their description, skills and responsibilities, qualifications, experience and salary ranges, work types, benefits, hiring companies, locations and full job postings.**

The data is built from the [Job Description Dataset](https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset) (~1.6M synthetic postings): **147 job titles**, **376 roles**, **888 companies** with their profile, **216 locations** (one city per country, geocoded) and **25 benefits**.

---

## 🌍 Languages

Job data (titles, roles, descriptions, benefits...) is in **English**,
whatever the locale. Contact names and phone numbers in `job_posting()` come
from the Faker locale, so they are localized (`fr_FR` -> "Luc Renaud",
"04 97 52 87 61").

---

## 📦 Installation

Requires Python 3.11+ and Faker 20+.

```bash
cd FAKER_JOBS
pip install -e .
```

---

## 🚀 Usage

```python
from faker import Faker
from faker_jobs import JobsProvider

fake = Faker("fr_FR")          # or "en_US"...
fake.add_provider(JobsProvider)
```

Every method is prefixed with `job_`, so adding the provider leaves Faker's
own `job()` (a random job title from Faker's job provider) and `company()`
untouched.

Unknown names (job title, role, country, company, sector, qualification)
and invalid arguments raise `ValueError`. Name lookups are case-insensitive.

### 💼 Job titles & roles

A **job title** is a family of **roles** ("Web Developer" -> "Frontend Web
Developer", "Backend Developer"...). Each role has its own description,
skills and responsibilities.

```python
fake.job_title()                        # "Software Engineer"
fake.job_role()                         # "Interaction Designer"
fake.job_role(job_title="Web Developer")   # "Frontend Web Developer"

fake.job_role_record()
# {
#     'job_title': 'Event Manager',
#     'role': 'Conference Manager',
#     'description': 'A Conference Manager coordinates and manages conferences, ...',
#     'skills': 'Event planning Conference logistics Budget management ...',
#     'responsibilities': 'Specialize in conference and convention planning. ...',
# }
fake.job_role_record(role="Frontend Web Developer")   # a specific role

fake.job_description(role="Tax Accountant")   # or a random role's
fake.job_skills()
fake.job_responsibilities()
```

Job titles and roles are picked **in proportion to how often they are
posted** in the source data: UX/UI designers come up ~4.7 times more often
than the median job title. Pass `weighted=False` to `job_title()`,
`job_role()`, `job_role_record()` or `job_posting()` for a uniform pick.

### 🎓 Qualifications, experience, salary

```python
fake.job_qualification()                # "MBA"
fake.job_qualification(full_name=True)  # "Master of Business Administration"
fake.job_qualification_name("B.Tech")   # "Bachelor of Technology"

fake.job_experience()                   # "2 to 12 Years"
fake.job_experience_range()             # (2, 12)

fake.job_salary_range()                 # "$59K-$104K"  (yearly, USD)
fake.job_salary_bounds()                # (59000, 104000)
```

Ranges follow the source data: minimum experience 0-5 years, maximum 8-15;
salaries from $55K-$65K up to $80K-$130K.

### 📝 Work type, benefits, portals

```python
fake.job_work_type()                    # "Full-Time", "Part-Time", "Contract", "Temporary" or "Intern"
fake.job_benefits()                     # 5 distinct benefits, as in every source posting
fake.job_benefits(count=3)              # ['Health Insurance', 'Parental Leave', 'Profit-Sharing']
fake.job_benefits(weighted=False)       # uniform pick (default: in proportion to the source data)
fake.job_portal()                       # "Indeed", "LinkedIn", "Randstad", "Adecco"...
```

### 🏢 Companies & locations

```python
fake.job_company()                      # "Siemens AG"
fake.job_company(sector="Energy")       # restricted to a sector (see the `job_sectors` property)
fake.job_company_profile()
# {
#     'company': '3M', 'sector': 'Conglomerate', 'industry': 'Chemicals',
#     'city': 'St. Paul', 'state': 'Minnesota', 'zip': '55144',
#     'website': 'www.3m.com', 'ticker': 'MMM', 'ceo': 'Michael F. Roman',
# }
fake.job_company_profile(company="3M")  # a specific company
fake.job_company_size()                 # 57916 (employees)

fake.job_location()
# {'city': 'Georgetown', 'country': 'Guyana', 'latitude': 6.8033, 'longitude': -58.1455}
fake.job_location(country="France")     # {'city': 'Paris', 'country': 'France', ...}
```

Company profile fields missing from the source data (no state outside the
US, no CEO for some companies...) are `None`.

### 📋 Job postings

```python
fake.job_id()                           # 2482944066971281
fake.job_posting_date()                 # a date within the last two years
fake.job_posting_date(start_date="-30d")   # anything Faker's date_between() accepts

fake.job_posting()
fake.job_posting(job_title="Web Developer", country="France", sector="Retail")
# {
#     'job_id': 9486177616759356,
#     'job_title': 'UX/UI Designer',
#     'role': 'Interaction Designer',
#     'description': '...', 'skills': '...', 'responsibilities': '...',
#     'qualification': 'MCA',
#     'experience': '5 to 15 Years', 'experience_min': 5, 'experience_max': 15,
#     'salary_range': '$63K-$80K', 'salary_min': 63000, 'salary_max': 80000,
#     'salary_currency': 'USD',
#     'work_type': 'Part-Time',
#     'benefits': ['Professional Development', ...],
#     'location': {'city': 'Manama', 'country': 'Bahrain', ...},
#     'company': {'company': 'Ferguson plc', 'sector': ..., ...},
#     'company_size': 90587,
#     'job_portal': 'FlexJobs',
#     'job_posting_date': datetime.date(2025, 6, 1),
#     'contact_person': 'Luc Renaud',       # from the Faker locale
#     'contact': '04 97 52 87 61',          # from the Faker locale
# }
```

### 🔤 Type hints

The package ships type information (`py.typed`) and `TypedDict`s describing
the returned dicts: `RoleRecord`, `LocationRecord`, `CompanyProfile`,
`JobPosting`. Methods added to a `Faker` instance by `add_provider()` are not
visible to type checkers, so either annotate the result or call the
provider directly:

```python
from faker_jobs import JobPosting, JobsProvider

# 1. Annotate the result of a call on the Faker instance
posting: JobPosting = fake.job_posting()

# 2. Or call the provider directly: everything is then typed automatically
jobs = JobsProvider(fake)
jobs.job_posting()["salary_min"]        # int
```

---

## 🎯 Demo

```bash
python -m faker_jobs
```

---

## 🧱 Data layout

The source files in `DATAS/` are not published in this repository: the
package only needs the generated `faker_jobs/data/jobs_data.json`. They are
only needed to rebuild it.

```
DATAS/                          curated source files (not published)
  faker_job_descriptions.csv    job titles, roles, descriptions, skills, responsibilities
  role_popularity.csv           postings per role         } measured on the full
  faker_benefits.csv            postings per benefit      } postings file by
  posting_ranges.csv            min/max of numeric fields } scripts/build_job_stats.py
  faker_qualifications.csv, faker_contract.csv, faker_job_portal.csv
  faker_locations.csv           one city per country (geocode_locations.py)
  faker_firms.csv               companies and profiles (transform_firms.py)
  job_descriptions2.csv         full postings file, 1.7 GB
scripts/
  build_job_stats.py            job_descriptions2.csv -> the 3 statistics files
  build_data.py                 DATAS/*.csv -> faker_jobs/data/jobs_data.json
faker_jobs/data/jobs_data.json  packaged data (~450 KB)
```

After changing anything in `DATAS/`:

```bash
python scripts/build_job_stats.py   # only if job_descriptions2.csv changed (~1 min)
python scripts/build_data.py
```

---

## 🧪 Tests

```bash
pip install -e ".[dev]"
pytest
ruff check faker_jobs tests scripts
mypy faker_jobs tests/test_typing.py
```

`tests/test_build_data.py` also checks that the packaged JSON is in sync
with `DATAS/` (skipped when `DATAS/` is not available).

---

## 📄 License

MIT - see [LICENSE](LICENSE).
