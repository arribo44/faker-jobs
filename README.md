# Faker Jobs Provider

**A custom [Faker](https://faker.readthedocs.io/) provider for generating realistic fake job-market data: job titles and occupations with their description, skills and responsibilities, qualifications, experience and salary ranges, contract types, benefits, hiring companies, locations and full job postings.**

Jobs come from **occupation directories**, covering every trade, not only
office jobs: the **1,923 job sheets** of the French [ROME 4.0](https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html)
directory (France Travail) in French, and the **2,045 [ESCO](https://esco.ec.europa.eu/)
occupations** mapped to them in English, German, Spanish and Italian, with **~14,000 job titles**,
**35 activity sectors**, skills, knowledge and soft skills. Posting
conditions (contracts, diplomas, salaries from official earnings, benefits,
job boards) are those of France, Germany, Spain, Italy and the United States.

Job locations are the **~29,700 cities** of 15,000 inhabitants or more of
[GeoNames](https://www.geonames.org/) in 244 countries, picked in proportion
to their population, with their local names in France, Germany, Spain and
Italy. Hiring companies are **~10,000 real companies** of the United States,
the United Kingdom, France, Germany, Spain and Italy from the [People Data Labs
company dataset](https://docs.peopledatalabs.com/docs/free-company-dataset)
(LinkedIn pages), by activity sector and size class, from small businesses
to large groups.

---

## 🌍 Languages

Everything follows the locale: **French** (ROME 4.0) in French locales
(`fr_FR`, `fr_CA`, `fr_BE`...), **German**, **Spanish** or **Italian** (ESCO)
in those locales (`de_DE`, `de_AT`, `es_ES`, `es_MX`, `it_IT`...), with the
conditions of France, Germany, Spain or Italy; **English** (ESCO) with the
**US** conditions in every other one (`en_US`, `en_GB`, `nl_NL`...).

Companies of a posting are in the country of the job (the United Kingdom
for `en_GB`, whose jobs are in the UK with US conditions) and the activity
sector of the job. Contact names and phone numbers always come from the
Faker locale (`fr_FR` -> "Luc Renaud", "04 97 52 87 61").

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

fake = Faker("en_US")          # or "fr_FR", "de_DE"...
fake.add_provider(JobsProvider)
```

Every method is prefixed with `job_`, so adding the provider leaves Faker's
own `job()` (a random job title from Faker's job provider) and `company()`
untouched.

Unknown names (job title, role, country, company, sector) and invalid
arguments raise `ValueError`. Name lookups are case-insensitive.

The examples below are in `en_US`; see [Other languages](#-other-languages)
for the values of the other locales.

### 💼 Job titles & roles

A **role** is an [occupation](#-occupations-rome--esco) ("accountant"); a
**job title** is one of its titles ("cost accountant", "financial reporting
accountant"...). Each occupation has its own description, skills and
activities.

```python
fake.job_title()                        # "courier"
fake.job_role()                         # "postman/postwoman"
fake.job_role(job_title="courier")      # "postman/postwoman"  (the occupation that has this title)

fake.job_role_record()
# {
#     'job_title': 'financial reporting accountant',
#     'role': 'accountant',
#     'description': 'Accountants review and analyse financial statements, budgets, ...',   # ESCO description
#     'skills': 'depreciation, statistics, ..., Teamwork, Attention to detail',            # knowledge and soft skills
#     'responsibilities': 'check accounting records; prepare trial accounting balances; ...',   # 5 activities
# }
fake.job_role_record(role="accountant")   # a specific occupation

fake.job_description(role="accountant")   # or a random occupation's
fake.job_skills()
fake.job_responsibilities()
```

Occupations are picked **in proportion to their demand** (see
[Occupations](#-occupations-rome--esco)): cooks, farm workers and care
assistants come up far more often than air traffic controllers. Pass
`weighted=False` to `job_title()`, `job_role()`, `job_role_record()` or
`job_posting()` for a uniform pick.

### 🎓 Qualifications, experience, salary

```python
fake.job_qualification()                # "Bachelor's degree in Computer Science", "Associate degree"...

fake.job_experience()                   # "4-7 years of experience" or "Entry level"
fake.job_experience_range()             # (4, 7)

fake.job_salary_range()                 # "$64,500 - $79,000 a year"  (yearly, gross)
fake.job_salary_bounds()                # (64500, 79000)
```

Salaries come from the official earnings of a random occupation's group
(see "Salaries follow the occupation" under [Occupations](#-occupations-rome--esco)).

### 📝 Contract, benefits, job boards

```python
fake.job_work_type()                    # "Full-time", "Part-time", "Contract", "Temporary", "Internship", "Freelance"
fake.job_benefits()                     # 4 distinct local benefits
fake.job_benefits(count=3)              # ['Paid parental leave', 'Vision insurance', 'Paid time off']
fake.job_portal()                       # "Indeed", "LinkedIn", "ZipRecruiter"...
```

### 🏢 Companies & locations

```python
fake.job_company()                      # "Pmg, Inc."
fake.job_company(sector="Energy")       # of an activity sector (see `job_activity_sectors`)
fake.job_company_profile(company="IBM") # a company of `job_companies` (case-insensitive)
# {
#     'company': 'IBM', 'sector': 'IT and telecommunications',
#     'industry': 'Information technology and services',   # LinkedIn industry (English locales)
#     'city': 'New York', 'state': 'New York', 'zip': None,
#     'website': 'ibm.com', 'ticker': None, 'ceo': None, 'founded': 1911,
# }
fake.job_company_profile(company="Acme")  # unknown name: a company of that name made up by the locale
fake.job_company_size()                 # 180 (employees, by size class: see below)

fake.job_location()                     # the locale's country by default (the United States here)
# {'city': 'Houston', 'country': 'United States', 'latitude': 29.7633, 'longitude': -95.3633}
fake.job_location(country="France")     # {'city': 'Paris', 'country': 'France', ...}
fake.job_location(country="Germany")    # {'city': 'Munich', ...}  (English names outside the locale's country)
```

Cities are the 29,700 cities of 15,000 inhabitants or more of GeoNames,
picked in proportion to their population (Houston comes up more often than
Boise; 2,849 cities in the United States, 462 in France, 945 in Germany).
Districts counted in their city are left out ("Paris 15 Vaugirard"), but
GeoNames lists some boroughs as cities of their own (Brooklyn).
`job_countries` lists the 244 countries, under their GeoNames English name
('United States', 'United Kingdom', 'The Netherlands'); `country=` also
takes their ISO code ('US', 'FR') and 'USA', 'UK', 'UAE'.

Companies are real companies of the locale's country from the People Data
Labs company dataset, or companies made up by the Faker locale, picked as
the hiring companies of the postings (see
[Occupations](#-occupations-rome--esco)); `job_companies` lists the real
ones of the country (2,257 in the United States: IBM, Apple, Walmart,
Microsoft...), `job_sectors` is the list of the 35 activity sectors (as
`job_activity_sectors`). `job_company_size()` picks a size
class by the share of jobs in the companies of each class in the locale's
country (official statistics: about half of the jobs in companies of up to
250 employees in France, two thirds in Italy), then a number of employees
in that class.

Company profile fields missing from the source data (no state outside the
US, no CEO for some companies...) are `None`.

### 🇫🇷 Other languages

In German, Spanish, French and Italian locales the same methods return the
occupations in the language and the local conditions:

```python
fake = Faker("fr_FR")
fake.add_provider(JobsProvider)

fake.job_title()              # "Conducteur / Conductrice de bus"  (a job title of an occupation, by demand)
fake.job_role(job_title="Conducteur / Conductrice de bus")   # "Conducteur / Conductrice de bus"  (its occupation)
fake.job_role_record()
# {
#     'job_title': 'Agent / Agente en cyno-détection de matières explosives',
#     'role': 'Agent / Agente cynotechnique en détection des explosifs',
#     'description': "Contrôler l'accès et la circulation des personnes; ...",   # ESCO description (de, es, it)
#     'skills': 'Bien-être animal, Connaissance des comportements canins, ...',  # knowledge and soft skills
#     'responsibilities': "Contrôler l'accès et la circulation des personnes; ...",   # 5 activities
# }
fake.job_qualification()      # "Bac+2 (BTS, DUT)"
fake.job_experience()         # "1 à 4 ans" or "Débutant accepté"
fake.job_salary_range()       # "26 500 € - 33 000 € brut/an"  (Eurostat earnings of a random occupation)
fake.job_work_type()          # "CDI", "CDD", "CDD saisonnier", "Intérim", "Alternance", "Stage", "Freelance"
fake.job_benefits()           # ['Tickets restaurant', 'RTT', ...]
fake.job_portal()             # "France Travail", "HelloWork", "APEC"...
fake.job_location()           # {'city': 'Nice', 'country': 'France', ...}  (the locale's country by default)
fake.job_company_profile(sector="Santé")   # as the hiring companies of the postings
# {'company': 'Pharmacie le Fournier', 'sector': 'Santé',
#  'industry': 'Hébergement médicalisé pour personnes âgées',   # NAF label (French locales)
#  'city': 'Grenoble', 'state': None, 'zip': None, 'website': 'pharmacie-alliance.fr', 'ticker': None,
#  'ceo': None, 'founded': None}
```

| Method | English locales | German, Spanish, French, Italian locales |
|---|---|---|
| `job_title()`, `job_role()`, `job_role_record()`... | ESCO occupations, in English | ROME (fr) or ESCO (de, es, it) occupations, in the language |
| conditions (`job_qualification()`, `job_salary_range()`, `job_work_type()`...) | US | the country's |
| `job_location()` | the United States by default (the United Kingdom for `en_GB`) | the locale's country by default, with local names (Deutschland, München, Sevilla, Roma...) |
| `job_company()`, `job_company_profile()`, `job_companies` | companies of the United States (United Kingdom for `en_GB`), LinkedIn industry | companies of the country, NAF activity in French |

Countries other than the locale's keep their English
name (`country="Belgium"`); the local name of the locale's country is
accepted too (`country="Deutschland"`).

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
#     'seasonal': 0.097,                       # share of those projects that are seasonal (BMO 2026)
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
sector (the requested one, else its main one) and the country of the job.

The hiring company comes from the [People Data Labs company
dataset](https://docs.peopledatalabs.com/docs/free-company-dataset) (7
million companies from their LinkedIn pages, CC BY 4.0), built by
`scripts/build_companies.py`:

- Its **size class** (1-10, 11-50, 51-200, 201-500, 501-1,000,
  1,001-5,000, 5,001-10,000, 10,001+ employees) is picked by the share of
  jobs in the companies of each class, in the sector and country, from
  **official statistics** of employment by enterprise size
  (`scripts/fetch_business_sizes.py`): Eurostat structural business
  statistics for France, Germany, Spain and Italy (persons employed by NACE
  section and size group 2-9, 10-49, 50-249, 250+), the Census Statistics
  of US Businesses 2022 and the UK business population estimates 2026. Each
  official size group gets its share, split between the LinkedIn classes it
  holds as LinkedIn splits them (number of companies × typical size), as
  LinkedIn lists few small companies. About 1 posting in 10 is in a company
  of up to 10 employees in the United States, 1 in 6 in France and
  Germany, 1 in 4 in Italy; 44% (United States) to 69% (Italy) in companies of up to 250
  employees (a third or less before the official shares). Building works
  hire in small companies, energy in large groups. Sectors without official
  figures (agriculture and public administration in Europe, mining and
  water in France) keep the LinkedIn shares.
- Then a **real company** of that sector and class: up to 10 per class,
  sector and country (~10,000 in all, 250 KB), with its name, website,
  founding year, headquarters city (and US state) and number of employees.
  Companies of 1-10 employees are left out (many are one-person businesses
  named after their owner): they are made up by the Faker locale, as the
  companies of a class with fewer than 10 companies in the dataset at
  random (so that no large group gets every job of its class) and those of
  the jobs outside these six countries. Made-up companies are in the city
  of the job, with a made-up CEO.
- Companies of up to 500 employees hire in their headquarters city when it
  is a city of `job_location()`; larger ones anywhere in the country.
- `company_size` is the company's number of employees; `industry` its
  LinkedIn industry in English locales, `None` in German, Spanish and
  Italian ones; in French locales an activity of the sector from the French
  NAF rév. 2 classification (`company_naf`, e.g. '86.10Z', and its label as
  `industry`): one that fits the LinkedIn industry of a real company (Air
  France: air transport, not passenger water transport), picked by
  employment (see below).

LinkedIn industries are mapped by hand to the 35 activity sectors
(`INDUSTRY_SECTORS` in `scripts/build_companies.py`); the dataset has some
noise (a public employment agency filed under utilities, a few wrong
websites), and its names are lower case: they are capitalized by rules
("bnp paribas" -> "BNP Paribas", "enel spa" -> "Enel SpA"), which miss some
("Aphp" for AP-HP).

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
#     'work_type': 'CDI',                       # CDI, CDD, CDD saisonnier, Intérim, Alternance, Stage, Freelance
#     'benefits': ['Intéressement et participation', 'Tickets restaurant', ...],   # fit the job and contract
#     'location': {'city': 'Lyon', 'country': 'France', ...},
#     'company': {'company': 'Trusk', 'sector': 'Logistique et transport', 'industry': 'Transports fluviaux de passagers',
#                 'city': 'Paris', 'website': 'trusk.com', 'founded': 2015, 'ceo': None, ...},
#     'company_size': 141,
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

The US conditions also serve the other locales that use the English data
(`en_GB`, `nl_NL`, `ja_JP`...): USD salaries, US job boards and a place in
the United States by default (in the United Kingdom, with British
companies, for `en_GB`).

**Salaries follow the occupation.** The occupation's ISCO-08 major group
(`isco_group`, from ESCO) gives its mean gross annual earnings in the
country: [Eurostat SES 2022](https://ec.europa.eu/eurostat/web/microdata/structure-of-earnings-survey)
by major group and NACE section of the company (that of its NAF activity
in French locales, else that of the occupation's sector; France, Germany,
Spain, Italy), [BLS OEWS](https://www.bls.gov/oes/) by SOC major group (United
States). That mean is then adjusted:
- to the experience asked, by the ratio of the matching age band (under
  30, 30-49, 50 and over) to the group's mean;
- to the contract: about 30% of a full-time salary for an internship, 55%
  for an apprenticeship, half for part-time;
- and kept above the minimum wage for a full-time employee.

The experience asked and the default diploma follow the skill level of the
group (managers and professionals, technicians, other jobs). The default
diploma (ESCO occupations, ROME sheets without diploma) often names the
field of study of the occupation's sector: "Abgeschlossene Berufsausbildung
im Bereich Logistik", "Ciclo Formativo de Grado Medio en Sanidad",
"Bachelor's degree in Computer Science", "BTS commerce". Expect a
specialist doctor to earn far more than a kitchen assistant, and a senior
more than a junior; but the figures are 2022 (Eurostat) or latest-year
(BLS) means of broad groups, not the pay of the exact job: an
**estimate**.

**Contracts follow the occupation too.** Each country has a national mix
of posting contracts (hand-made, e.g. 55% CDI, 20% CDD, 12% Intérim in
France), adapted to the occupation's ISCO major group with the
[Eurostat Labour Force Survey](https://ec.europa.eu/eurostat/web/lfs) 2025
(France, Germany, Spain, Italy): the weight of the temporary contracts is
multiplied by the ratio of the group's share of temporary employees to the
national share, the same for part-time (Teilzeit) and self-employed
(freelance) workers, capped at three times the national mix; the permanent
contract takes the rest (at least 10%). A farm worker therefore gets a
fixed-term or temp contract far more often than a manager. In French
locales, a **CDD saisonnier** is offered with the occupation's share of
seasonal recruitment projects (`seasonal`, BMO 2026): 95% of the fruit
picker postings, 1% of the software developer ones, about 30% of all
French postings, as in the BMO survey (hiring plans, which count every
seasonal hire), so the CDI is only about 40% of them. The United States
keep the national mix for every occupation.

Benefit rules, job boards, default diplomas and their fields of study are
hand-made and **illustrative** (`scripts/posting_conditions.py`).

The NAF activities of each sector are chosen by hand (`NAF_BY_SECTOR` in
`scripts/build_occupations.py`) and picked by **employment**: each
sub-class weighs the persons employed in its NACE group in France
(Eurostat structural business statistics), shared by the sub-classes of the
group, so road freight comes up about 30 times more often than passenger
water transport (the median weight of the sector for public
administration and associations, which have no figures). For a real
company, only the activities that fit its LinkedIn industry
(`scripts/naf_industries.py`, hand-made: "logistics and supply chain" ->
49.4 road freight, 52 warehousing and support) are picked, when the sector
has some. The activity is still not chosen for the occupation itself: a
wastewater plant manager may work for a waste treatment company.

ROME sheets have no description (`None`).

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
(every trade, picked by demand), with the keys of `job_role_record()`:

```python
fake = Faker("fr_FR")
fake.add_provider(JobsProvider)

fake.job_posting()
fake.job_posting(sector="Santé", country="France")   # an activity sector
fake.job_posting(code="J1506")                       # a given occupation
fake.job_posting(role="Infirmier / Infirmière en soins généraux (IDE)")   # by name (see `job_roles`)
fake.job_posting(job_title="Infirmier / Infirmière en gériatrie")          # by job title (see `job_titles`)
# {
#     'occupation': {'code': 'J1506', 'title': 'Infirmier / Infirmière en soins généraux (IDE)', ...},
#     'job_id': 9486177616759356,
#     'job_title': 'Infirmier en gériatrie (H/F)',
#     'role': 'Infirmier / Infirmière en soins généraux (IDE)',   # the occupation
#     'description': ...,        # ESCO description; for ROME sheets (none), the main activities
#     'responsibilities': 'Appliquer un protocole de soin; ...',   # the occupation's skills (activities)
#     'skills': "Connaissance de l'écosystème sanitaire, ..., Etre force de proposition",   # knowledge, soft skills
#     'qualification': "Diplôme d'Etat d'infirmier (ière)",
#     'experience': '1 à 3 ans', 'experience_min': 1, 'experience_max': 3,
#     'salary_range': '27 000 € - 33 000 € brut/an', 'salary_min': 27000, 'salary_max': 33000,
#     'salary_currency': 'EUR',
#     'work_type': 'CDI',
#     'benefits': ['Mutuelle d\'entreprise', ...],
#     'location': {'city': 'Lyon', 'country': 'France', ...},
#     'company': {'company': 'Pharmacie le Fournier', 'sector': 'Santé', ...},
#     'company_size': 180,
#     'seniority': 'junior',
#     'job_portal': 'HelloWork',
#     'job_posting_date': datetime.date(2025, 6, 1),
#     'contact_person': 'Luc Renaud',       # from the Faker locale
#     'contact': '04 97 52 87 61',          # from the Faker locale
# }
```

It is `job_occupation_posting()` in the `JobPosting` shape: use that one for
the NAF code and company sector.

`job_posting_text()` writes the full text of a posting, as published on a
job board, in the locale's language: headline, company, the job, missions,
profile, conditions and how to apply. Pass a posting from
`job_occupation_posting()` or `job_posting()` (by default it makes a new
one), and `markdown=True` for Markdown headings and bullets:

```python
fake.job_posting_text()
fake.job_posting_text(fake.job_posting(code="J1506"), markdown=True)
```

```text
Chercheur en glaciologie (H/F)
Chauvin · Bordeaux, France · CDI

Acteur du secteur Environnement, Chauvin (21 038 salariés) renforce ses équipes à Bordeaux. Activité : Services d'aménagement paysager.

DESCRIPTION DU POSTE
Vous exercerez le métier de Glaciologue (fiche ROME F1123, domaine Construction, Bâtiment et Travaux publics). Ce métier contribue à la transition écologique.

VOS MISSIONS
Vous serez notamment chargé(e) de :
- Définir des mesures de prévention des risques
- Analyser les données climatiques
...

PROFIL RECHERCHÉ
- Formation : Master mention sciences de la Terre et des planètes, environnement
- Expérience : 7 à 9 ans
- Connaissances : Gestion de groupe en expédition, Glaciologie, ...
- Savoir-être : organiser son travail selon les priorités et les objectifs ; ...

CONDITIONS DU POSTE
- Contrat : CDI
- Rémunération : 50 000 € - 69 000 € brut/an
- Lieu de travail : Bordeaux, France
- Avantages : Comité social et économique (CSE), Prime annuelle, ...

CANDIDATURE
Intéressé(e) ? Contactez Alice-Madeleine Valette au +33 (0)4 20 79 66 69, référence de l'offre : 9524798606396852.
Offre publiée le 3 mars 2025 sur Le Bon Coin Emploi.
```

The wording is hand-made (a few phrasings per section, picked at random and
reproducible with `Faker.seed()`); every fact comes from the posting.
Render a posting with a provider of the locale that made it: the text is in
the provider's language.

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
package only needs the generated files of `faker_jobs/data/`. They are
only needed to rebuild them.

The cities come from GeoNames:

```
DATAS/geonames/cities15000.zip, countryInfo.txt   GeoNames dump (download.geonames.org/export/dump/)
DATAS/geonames/alt_{FR,DE,ES,IT}.zip              alternatenames/{FR,DE,ES,IT}.zip: local and English names
scripts/
  build_cities.py [--download]  -> faker_jobs/data/cities.json.gz (~500 KB)
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
DATAS/salaries/eurostat_lfs.json             Eurostat LFS 2025 temporary, part-time, self-employed workers
                                             by ISCO group, cached by fetch_salaries.py
scripts/
  fetch_esco.py [language]      ESCO web-service API -> the caches above (~2,000 requests each, resumable)
  fetch_salaries.py             Eurostat and BLS APIs -> the salary and labour caches above
  posting_conditions.py         local contracts, benefits, job boards, diplomas by locale
  rome_labels.py                ROME sectors, domains and soft skills in English, German, Spanish, Italian
  build_occupations.py          -> faker_jobs/data/occupations_{de_DE,en_US,es_ES,fr_FR,it_IT}.json.gz (gzipped)
                                   and faker_jobs/data/conditions.json (posting conditions, plain JSON)
                                   (with the ROME code of each sector, the key of companies.json.gz)
```

The hiring companies come from People Data Labs, their sizes from official statistics:

```
DATAS/7millionscompanies/companies_sorted.csv   People Data Labs Free Company Dataset (7.2 million rows, 1 GB)
DATAS/business_sizes/us_state_naics_detailedsizes_2022.xlsx, us_naicssector_large_emplsize_2022.xlsx
                                             Census SUSB 2022 (census.gov, no API: --download)
DATAS/business_sizes/BPE_2026_detailed_tables.xlsx   UK business population estimates 2026 (gov.uk)
DATAS/business_sizes/sizes.json              employment by size group and NACE section, by fetch_business_sizes.py
scripts/
  fetch_business_sizes.py [--download]   Eurostat API (sbs_sc_ovw) + the spreadsheets above -> sizes.json
  build_companies.py [csv]      -> faker_jobs/data/companies.json.gz (~250 KB; after build_cities.py,
                                   build_occupations.py and fetch_business_sizes.py)
```

```bash
for l in en de es it; do python scripts/fetch_esco.py $l; done   # only if the crosswalk changed
pip install -e ".[build]"         # openpyxl and xlrd, to read the xlsx/xls sources
python scripts/build_cities.py      # first: build_companies.py matches cities to its output
python scripts/build_occupations.py
python scripts/fetch_business_sizes.py   # only when newer statistics are out (--download the spreadsheets)
python scripts/build_companies.py
```

---

## 🧪 Tests

```bash
pip install -e ".[dev]"
pytest
ruff check faker_jobs tests scripts
mypy faker_jobs tests/test_typing.py
```

`tests/test_cities.py` and `tests/test_build_occupations.py` also check
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
- Earnings and labour figures: Eurostat SES 2022 and LFS 2025 © European
  Union (reuse authorised, source acknowledged); BLS OEWS, U.S. Bureau of Labor Statistics (public domain).
- Employment by enterprise size: Eurostat structural business statistics
  (sbs_sc_ovw) © European Union (reuse authorised, source acknowledged);
  Statistics of US Businesses 2022, U.S. Census Bureau (public domain);
  Business population estimates 2026, Department for Business and Trade,
  [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- English, German, Spanish and Italian labels of the 35 ROME activity
  sectors, 14 domains and 16 soft skills are translated by this project.

Cities: [GeoNames](https://www.geonames.org/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Hiring companies: [People Data Labs Free Company Dataset](https://docs.peopledatalabs.com/docs/free-company-dataset),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (a sample of it,
names capitalized and industries mapped to activity sectors by this project).
