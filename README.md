# Faker Jobs Provider

**A custom [Faker](https://faker.readthedocs.io/) provider for generating realistic fake job-market data: job titles and roles with their description, skills and responsibilities, qualifications, experience and salary ranges, work types, benefits, hiring companies, locations and full job postings.**

The data is built from the [Job Description Dataset](https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset) (~1.6M synthetic postings): **147 job titles**, **376 roles**, **888 companies** with their profile, **216 locations** (one city per country, geocoded) and **25 benefits**.

On top of it, **occupations** cover every trade, not only office jobs: the
**1,923 job sheets** of the French [ROME 4.0](https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html)
directory (France Travail) in French, and the **2,045 [ESCO](https://esco.ec.europa.eu/)
occupations** mapped to them in English, with **~14,000 job titles**,
**35 activity sectors**, skills, knowledge and soft skills.

---

## 🌍 Languages

Job data from the Kaggle dataset (titles, roles, descriptions, benefits...)
is in **English**, whatever the locale. Contact names and phone numbers in
`job_posting()` come from the Faker locale, so they are localized (`fr_FR` ->
"Luc Renaud", "04 97 52 87 61").

[Occupations](#-occupations-rome--esco) follow the locale: **French** (ROME
4.0) in French locales (`fr_FR`, `fr_CA`, `fr_BE`...), **English** (ESCO) in
every other one. In French locales, `job_occupation_posting()` is entirely
French (contract, salary in EUR, diplomas, place, job boards).

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

### 🧰 Occupations (ROME / ESCO)

Occupations come from a second source, in the language of the Faker locale
(see [Languages](#-languages)), and cover every trade: healthcare,
construction, industry, logistics, hospitality, public service... Each one
belongs to one or more of **35 activity sectors**, so you can pick an
occupation that fits a sector.

```python
fake = Faker("en_US")
fake.add_provider(JobsProvider)

fake.job_activity_sector()                     # "Logistics and transport"
fake.job_occupation()                          # "plasterer"
fake.job_occupation(sector="Healthcare")       # restricted to an activity sector: "physiotherapy assistant"
fake.job_occupation_title(sector="Healthcare") # a job title as posted: "technologist in pharmacy"
fake.job_occupation_skills(count=3)            # ['assess nature of injury in emergency', 'provide first aid', ...]
fake.job_occupation_record(sector="Healthcare")
# {
#     'code': '7b74626d-b487-48a1-9e80-47faf9928210',   # ESCO concept id
#     'title': 'pharmacy technician',
#     'job_title': 'technologist in pharmacy',          # one of its job titles
#     'domain': 'Healthcare',
#     'sector': 'Healthcare', 'sectors': ['Healthcare'],
#     'description': 'Pharmacy technicians, under the supervision of a pharmacist, check incoming goods, ...',
#     'skills': ["manage healthcare users' data", 'follow clinical guidelines', ...],   # 37 skills
#     'knowledge': ['medicines for self-medication'],
#     'soft_skills': ['Active listening and empathy', 'Attention to detail', ...],
#     'qualifications': [],                    # French diplomas: French locales only
#     'executive': False,                      # a "cadre" job (from ROME)
#     'regulated': True,                       # a regulated profession
#     'riasec': ['I', 'R'],                    # Holland codes, major first
#     'transitions': ['demographic'],          # any of 'ecological', 'digital', 'demographic'
# }
fake.job_occupation_record(code="7b74626d-b487-48a1-9e80-47faf9928210")  # a given occupation
```

With a French locale, the same methods return the ROME 4.0 data in French;
`code` is then the ROME code:

```python
fake = Faker("fr_FR")
fake.add_provider(JobsProvider)

fake.job_occupation_title(sector="Bâtiment et travaux publics (BTP)")
# "Technicien / Technicienne de maintenance en matériels de chantier de travaux publics"
fake.job_occupation_title(sector="Santé", gender="F")   # "Pharmacienne assistante" ("M": masculine form)
fake.job_occupation_record(code="J1506")
# {
#     'code': 'J1506',
#     'title': 'Infirmier / Infirmière en soins généraux (IDE)',
#     'job_title': "Infirmier / Infirmière d'hospitalisation à domicile",
#     'domain': 'Santé',
#     'sector': 'Santé', 'sectors': ['Santé', 'Social'],
#     'description': None,
#     'skills': ['Appliquer un protocole de soin', ...],                                  # savoir-faire
#     'knowledge': ["Connaissance de l'écosystème sanitaire, médico-social et social", ...], # savoirs
#     'soft_skills': ['Etre force de proposition', ...],                                   # savoir-être
#     'qualifications': ["Diplôme d'Etat d'infirmier (ière)"],    # diplomas listed by the ROME sheet
#     'executive': False, 'regulated': True, 'riasec': ['S', 'I'], 'transitions': ['demographic'],
# }
```

The lists of activity sectors and occupation codes are properties of the
provider (Faker only registers methods), in the language of the Faker
instance it is given:

```python
JobsProvider(fake).job_activity_sectors   # ['Activités juridiques et comptables', ...] (35)
JobsProvider(fake).job_occupation_codes   # ['A1101', 'A1201', ...] (1,923; 2,045 in English)
```

`job_occupation_posting()` builds a full posting on an occupation: the job
title, its skills and the hiring company fit together. The company is one of
the packaged companies whose sector matches the occupation's sector (the
requested one, else its main one, else its other ones); when none does
(social work, public service, research...), it is a name made up by the
Faker locale and `company_sector` is `None`.

In French locales the whole posting is French: the job title follows the
French usage for job ads (masculine form + "(H/F)": an ad may not target a
gender), the diploma comes from the ROME sheet, and the contract, salary,
benefits, place (France by default) and job board are French:

```python
fake.job_occupation_posting(sector="Logistique et transport")
# {
#     'job_id': 854448090234722,
#     'job_title': 'Conducteur routier régional (H/F)',
#     'occupation': {'code': 'N4101', 'title': 'Conducteur / Conductrice de poids lourd', ...},
#     'skills': ["Rendre compte à l'exploitant de son activité", ...],   # 5 by default (`skills=`)
#     'qualification': 'Titre professionnel conducteur du transport routier de marchandises sur tous véhicules',
#     'experience': '3 à 6 ans', 'experience_min': 3, 'experience_max': 6,   # or 'Débutant accepté'
#     'salary_range': '24 000 € - 32 000 € brut/an', 'salary_min': 24000, 'salary_max': 32000,
#     'salary_currency': 'EUR',
#     'work_type': 'CDI',                       # CDI, CDD, Intérim, Alternance, Stage, Freelance
#     'benefits': ['Intéressement et participation', 'Tickets restaurant', ...],
#     'location': {'city': 'Lyon', 'country': 'France', ...},
#     'company': {'company': 'Transurban Group', 'sector': 'Transportation/Infrastructure', ...},
#     'company_sector': 'Logistique et transport',
#     'job_portal': 'HelloWork',                # APEC and Cadremploi for executive jobs only
#     'contact_person': 'Agathe Evrard de Lopez', 'contact': '+33 (0)3 51 39 07 57',
#     ...
# }
```

The French conditions are **illustrative**, made by hand to look plausible:
contract weights and salary ranges (by executive status) are not
statistics. In other locales, qualifications, salaries (USD), benefits, work
types, portals and locations come from the Kaggle data, in English.

ROME sheets have no description (`None`). The occupation methods are not
weighted (these sources have no posting counts) and are independent from the
Kaggle-based methods: activity sectors (occupations) are not `job_sectors`
(companies), and `job_posting()` is unchanged.

An ESCO occupation takes the sectors that cover at least 25% of the ROME job
titles mapped to it. Sectors follow ROME, which lists secondary sectors too:
a few occupations show up in a sector you would not expect (e.g. a library
clerk in healthcare).

With several locales, add the provider to each one (Faker does not proxy
`add_provider()` in multiple locale mode):

```python
fake = Faker(["fr_FR", "en_US"])
for locale in fake.locales:
    fake[locale].add_provider(JobsProvider)
fake["fr_FR"].job_occupation()   # French
fake["en_US"].job_occupation()   # English
```

To use one language whatever the Faker locale, subclass the provider:

```python
class FrenchJobsProvider(JobsProvider):
    occupations_locale = "fr_FR"   # or "en_US"
```

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
`JobPosting`, `OccupationRecord`, `OccupationPosting`. Methods added to a `Faker` instance by `add_provider()` are not
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

Occupations have their own sources and scripts:

```
DATAS/metiers/rome-4-0-métiers-×-secteurs-d-activité.xlsx   ROME 4.0 v62 (France Travail)
DATAS/esco/EURESmapping_occs_FR_v1.0.9.csv   ROME 4.0 -> ESCO 1.0.9 crosswalk (ESCO portal, France)
DATAS/esco/esco_occupations_v1.0.9.json      English ESCO data, cached by fetch_esco.py
scripts/
  fetch_esco.py                 ESCO web-service API -> the cache above (~2,000 requests, resumable)
  build_occupations.py          -> faker_jobs/data/occupations_en_US.json, occupations_fr_FR.json
                                   (also matches the companies of jobs_data.json to the ROME sectors)
```

```bash
python scripts/fetch_esco.py        # only if the crosswalk changed
python scripts/build_occupations.py # needs openpyxl (dev extra); after build_data.py
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

`tests/test_build_data.py` and `tests/test_build_occupations.py` also check
that the packaged JSON files are in sync with `DATAS/` (skipped when
`DATAS/` is not available).

---

## 📄 License

Code: MIT - see [LICENSE](LICENSE).

Occupation data:
- ROME 4.0 © France Travail, [Licence Ouverte / Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
- ESCO © European Union, reused under [Commission Decision 2011/833/EU](https://eur-lex.europa.eu/eli/dec/2011/833/oj);
  ROME 4.0 → ESCO crosswalk by France Travail, from the [ESCO portal](https://esco.ec.europa.eu/en/use-esco/eures-countries-mapping-tables).
- English labels of the 35 ROME activity sectors, 14 domains and 16 soft
  skills are translated by this project.
