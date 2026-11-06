# Faker Jobs Provider

**A custom [Faker](https://faker.readthedocs.io/) provider for generating realistic fake job-market data: job titles and roles with their description, skills and responsibilities, qualifications, experience and salary ranges, work types, benefits, hiring companies, locations and full job postings.**

The data is built from the [Job Description Dataset](https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset) (~1.6M synthetic postings): **147 job titles**, **376 roles**, **888 companies** with their profile, **216 locations** (one city per country, geocoded) and **25 benefits**.

On top of it, **occupations** cover every trade, not only office jobs: the
**1,923 job sheets** of the French [ROME 4.0](https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html)
directory (France Travail) in French, and the **2,045 [ESCO](https://esco.ec.europa.eu/)
occupations** mapped to them in English, German, Spanish and Italian, with **~14,000 job titles**,
**35 activity sectors**, skills, knowledge and soft skills.

---

## 🌍 Languages

Job data from the Kaggle dataset (titles, roles, descriptions, benefits...)
is in **English**, whatever the locale. Contact names and phone numbers in
postings come from the Faker locale, so they are localized (`fr_FR` ->
"Luc Renaud", "04 97 52 87 61").

[Occupations](#-occupations-rome--esco) follow the locale: **French** (ROME
4.0) in French locales (`fr_FR`, `fr_CA`, `fr_BE`...), **German**, **Spanish**
or **Italian** (ESCO) in those locales (`de_DE`, `de_AT`, `es_ES`, `es_MX`,
`it_IT`...), **English** (ESCO) in every other one. `job_posting()` is built
on them by default. In French locales, postings are entirely French
(contract, salary in EUR, diplomas, place, job boards).

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
`job_role()`, `job_role_record()` or `job_posting(source="kaggle")` for a uniform pick.

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
#     'isco_code': '3213', 'isco_group': '3',  # ISCO-08 unit and major group (skill level, salary)
#     'demand': 689,                           # estimated yearly recruitment projects in France (BMO 2026)
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
#     'isco_code': '2221', 'isco_group': '2',
#     'demand': 1489,
# }
```

The lists of activity sectors and occupation codes are properties of the
provider (Faker only registers methods), in the language of the Faker
instance it is given:

```python
JobsProvider(fake).job_activity_sectors   # ['Activités juridiques et comptables', ...] (35)
JobsProvider(fake).job_occupation_codes   # ['A1101', 'A1201', ...] (1,923; 2,045 in English)
```

Occupations are picked by **demand**: in proportion to their estimated
yearly recruitment projects in France (`demand`), from France Travail's
[BMO 2026](https://www.data.gouv.fr/datasets/enquete-besoins-en-main-doeuvre-bmo)
survey, so cooks, farm workers and care assistants come up far more often
than air traffic controllers. `weighted=False` picks uniformly, in every
`job_occupation*` method:

```python
fake.job_occupation()                  # weighted by demand
fake.job_occupation(weighted=False)    # uniform
```

BMO counts recruitment projects by job family (FAP 2021): each family's
projects are shared evenly between its ROME sheets with the
[DARES FAP 2021 → ROME table](https://dares.travail-emploi.gouv.fr/donnees/la-nomenclature-des-familles-professionnelles-2021).
That table only knows the 532 ROME codes older than ROME 4.0: the other
sheets get the mean weight of their ROME group (same 3-character prefix),
and the weights are scaled back to the BMO total (2.2 million projects). An
ESCO occupation gets the weight of its ROME sheets, shared by mapped job
titles. These are French figures in every locale, and an **estimate**: use
them as a popularity weight, not as statistics.

`job_occupation_posting()` builds a full posting on an occupation: the job
title, its skills and the hiring company fit together, in the occupation's
sector (the requested one, else its main one). In non-French locales the
company is one of the packaged companies of that sector; when none is
(social work, public service, research..., about 1 posting in 5), it is a
name made up by the Faker locale and `company_sector` is `None`. In French
locales the company is made up by the Faker locale, with an activity of the
occupation's sector from the French NAF rév. 2 classification
(`company_naf`, e.g. '86.10Z', and its label as `industry`).

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
#     'benefits': ['Intéressement et participation', 'Tickets restaurant', ...],   # fit the job and contract
#     'location': {'city': 'Lyon', 'country': 'France', ...},
#     'company': {'company': 'Lemaire SARL', 'sector': 'Logistique et transport',
#                 'industry': 'Transports routiers de fret interurbains', 'city': 'Lyon', 'ceo': 'Paul Gomez', ...},
#     'company_sector': 'Logistique et transport',
#     'company_naf': '49.41A',                  # NAF rév. 2 activity of the sector (None outside French locales)
#     'seniority': 'mid',                       # 'junior' (< 3 years asked), 'mid' (3-7), 'senior' (8+)
#     'job_portal': 'HelloWork',                # APEC and Cadremploi for executive jobs only
#     'contact_person': 'Agathe Evrard de Lopez', 'contact': '+33 (0)3 51 39 07 57',
#     ...
# }
```

Benefits fit the job: remote work and flexible hours only for office jobs
(banking and insurance, communication, business support) or executive ones,
a company car only for executives, no bonus or profit-sharing for interns,
no employee benefit for freelancers.

German, Spanish, Italian and US postings get **local conditions** too, in
their language: contracts (Unbefristet, Zeitarbeit, Ausbildung...;
Indefinido, Fijo discontinuo, Prácticas...; Tempo indeterminato,
Somministrazione, Apprendistato...; Full-time, Part-time, Internship...),
diplomas, benefits (Betriebliche Altersvorsorge, Seguro médico privado,
Buoni pasto, 401(k) matching...), job boards (StepStone, InfoJobs, Subito
Lavoro, ZipRecruiter...) and a city of the country:

| Locale | Example |
|---|---|
| `de_DE` | Lastkraftwagenfahrer (m/w/d), Unbefristet, "Berufseinsteiger willkommen", 29.500 € - 34.000 € brutto/Jahr |
| `es_ES` | operadora de máquina afiladora, Indefinido, "De 1 a 2 años de experiencia", 20.500 € - 26.000 € brutos/año |
| `it_IT` | conducente di autocarri (m/f), Tempo indeterminato, "Anche prima esperienza", RAL 26.000 € - 30.000 € |
| `en_US` | boatbuilder, Full-time, "4-7 years of experience", $58,000 - $71,000 a year |

The US conditions only apply to `en_US`: the other locales that use the
English data (`en_GB`, `nl_NL`...) keep the Kaggle conditions (USD,
worldwide places), as `job_posting(source="kaggle")`.

**Salaries follow the occupation.** The occupation's ISCO-08 major group
(`isco_group`, from ESCO) gives its mean gross annual earnings in the
country: [Eurostat SES 2022](https://ec.europa.eu/eurostat/web/microdata/structure-of-earnings-survey)
by major group and NACE section of the company (France, Germany, Spain,
Italy), [BLS OEWS](https://www.bls.gov/oes/) by SOC major group (United
States). That mean is then adjusted:
- to the experience asked, by the ratio of the matching age band (under
  30, 30-49, 50 and over) to the group's mean;
- to the contract: about 30% of a full-time salary for an internship, 55%
  for an apprenticeship, half for part-time;
- and kept above the minimum wage for a full-time employee.

The experience asked and the default diploma follow the skill level of the
group (managers and professionals, technicians, other jobs). Expect a
specialist doctor to earn far more than a kitchen assistant, and a senior
more than a junior; but the figures are 2022 (Eurostat) or latest-year
(BLS) means of broad groups, not the pay of the exact job: an
**estimate**. Contract weights, benefit rules, job boards and default
diplomas are hand-made and **illustrative** (`scripts/posting_conditions.py`).

The NAF activities of each sector are chosen by hand (`NAF_BY_SECTOR` in
`scripts/build_occupations.py`) and picked at random within the sector: a
wastewater plant manager may work for a waste treatment company.

ROME sheets have no description (`None`). The occupation methods are
independent from the Kaggle-based methods: activity sectors (occupations) are not `job_sectors`
(companies).

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
    occupations_locale = "fr_FR"   # or "en_US", "de_DE", "es_ES", "it_IT"
```

### 📋 Job postings

```python
fake.job_id()                           # 2482944066971281
fake.job_posting_date()                 # a date within the last two years
fake.job_posting_date(start_date="-30d")   # anything Faker's date_between() accepts
```

`job_posting()` builds a posting on a ROME / ESCO
[occupation](#-occupations-rome--esco), in the language of the Faker locale
(every trade, picked by demand), with the same keys as the Kaggle postings:

```python
fake = Faker("fr_FR")
fake.add_provider(JobsProvider)

fake.job_posting()
fake.job_posting(sector="Santé", country="France")   # an activity sector
fake.job_posting(code="J1506")                       # a given occupation
# {
#     'source': 'occupations',
#     'occupation': {'code': 'J1506', 'title': 'Infirmier / Infirmière en soins généraux (IDE)', ...},
#     'job_title': 'Infirmier en gériatrie (H/F)',
#     'role': 'Infirmier / Infirmière en soins généraux (IDE)',   # the occupation
#     'description': ...,        # ESCO description; for ROME sheets (none), the main activities
#     'responsibilities': 'Appliquer un protocole de soin; ...',   # the occupation's skills (activities)
#     'skills': "Connaissance de l'écosystème sanitaire, ..., Etre force de proposition",   # knowledge, soft skills
#     'salary_range': '27 000 € - 33 000 € brut/an', 'salary_currency': 'EUR', 'work_type': 'CDI',
#     ...                        # the other keys as below
# }
```

It is `job_occupation_posting()` in the `JobPosting` shape: use that one for
the NAF code and company sector. `source="kaggle"` gives the postings of the
Kaggle data, in English (office jobs, worldwide), as before 0.2; `job_title`
and `role` need it:

```python
fake.job_posting(source="kaggle")
fake.job_posting(job_title="Web Developer", country="France", sector="Retail", source="kaggle")
# {
#     'source': 'kaggle',
#     'occupation': None,
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
DATAS/esco/esco_occupations_v1.0.9_{de,es,it}.json   same in German, Spanish, Italian
DATAS/bmo/Base-open-data-BMO-2026.xlsx       BMO 2026 recruitment projects (France Travail, data.gouv.fr)
DATAS/bmo/Dares_FAP2021_Table_passage_ROME.xlsx   FAP 2021 -> ROME table (DARES; its site blocks
                                             scripts: download it in a browser or from the Web Archive)
DATAS/naf/naf2008_liste_n5.xls               NAF rév. 2 sub-classes (INSEE)
DATAS/salaries/eurostat_ses2022.json         Eurostat SES 2022 earnings, cached by fetch_salaries.py
DATAS/salaries/bls_oews.json                 BLS OEWS mean wages, cached by fetch_salaries.py
scripts/
  fetch_esco.py [language]      ESCO web-service API -> the caches above (~2,000 requests each, resumable)
  fetch_salaries.py             Eurostat and BLS APIs -> the salary caches above
  posting_conditions.py         local contracts, benefits, job boards, diplomas by locale
  rome_labels.py                ROME sectors, domains and soft skills in English, German, Spanish, Italian
  build_occupations.py          -> faker_jobs/data/occupations_{de_DE,en_US,es_ES,fr_FR,it_IT}.json.gz (gzipped)
                                   (also matches the companies of jobs_data.json to the ROME sectors)
```

```bash
for l in en de es it; do python scripts/fetch_esco.py $l; done   # only if the crosswalk changed
python scripts/build_occupations.py # needs openpyxl and xlrd (dev extra); after build_data.py
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
- BMO 2026 © France Travail, FAP 2021 → ROME table © DARES, NAF rév. 2 ©
  INSEE: [Licence Ouverte / Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
- Earnings: Eurostat SES 2022 © European Union (reuse authorised, source
  acknowledged); BLS OEWS, U.S. Bureau of Labor Statistics (public domain).
- English, German, Spanish and Italian labels of the 35 ROME activity
  sectors, 14 domains and 16 soft skills are translated by this project.
