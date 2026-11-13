# Faker Jobs Provider

**A custom [Faker](https://faker.readthedocs.io/) provider for generating realistic fake job-market data: job titles and occupations with their description, skills and responsibilities, qualifications, experience and salary ranges, contract types, benefits, hiring companies, locations and full job postings.**

Jobs come from **occupation directories**, covering every trade, not only
office jobs: the **1,923 job sheets** of the French [ROME 4.0](https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html)
directory (France Travail) in French, and the **2,045 [ESCO](https://esco.ec.europa.eu/)
occupations** mapped to them in English, German, Spanish, Italian, Portuguese, Dutch and Polish, with
**~14,000 job titles** in each language,
**35 activity sectors**, skills, knowledge and soft skills. Posting
conditions (contracts, diplomas, salaries from official earnings, benefits,
job boards) are those of **17 countries**: France, Germany, Spain, Italy,
the United States, and Belgium, Switzerland, Canada, Austria, Luxembourg,
Mexico, Chile, Colombia, the United Kingdom, Ireland, Australia and New
Zealand for their Faker locales (`fr_BE`, `de_CH`, `es_MX`, `en_GB`...).

Job locations are the **~29,700 cities** of 15,000 inhabitants or more of
[GeoNames](https://www.geonames.org/) in 244 countries, picked in proportion
to their population, with their local names in the countries of the
locales ('München', 'Anvers', 'Genf'). Hiring companies are **real
companies** of these 17 countries from the [People Data Labs
company dataset](https://docs.peopledatalabs.com/docs/free-company-dataset)
(LinkedIn pages), by activity sector and size class, from small businesses
to large groups.

---

## 🌍 Languages and countries

Everything follows the locale. The **language** gives the occupations:
**French** (ROME 4.0) in French locales (`fr_FR`, `fr_BE`, `fr_CA`...),
**German**, **Spanish**, **Italian**, **Portuguese**, **Dutch** or
**Polish** (ESCO) in those locales (`de_DE`, `de_AT`, `es_MX`, `it_CH`,
`pt_BR`, `nl_BE`, `pl_PL`...), **English** (ESCO) in every other one
(`en_US`, `en_GB`, `ja_JP`, `sv_SE`...). Brazilian postings use the
Portuguese of ESCO in Brazilian spelling and vocabulary ('recepcionista',
'eletrônico', 'equipe', 'ônibus': `faker_jobs/pt_br.py`, word-based).

The **country** gives the posting conditions: currency, contracts, salaries
from official earnings, minimum wage, diplomas, benefits, job boards, the
gender mark of the titles, the place of the job and its companies:

| Locales | Country | Salaries | Example (a posting of the locale) |
|---|---|---|---|
| `fr_FR` | France | Eurostat SES | Conducteur de bus (H/F), CDI, 26 500 € - 33 000 € brut/an |
| `fr_BE` | Belgium | Eurostat SES | Ingénieur CVC (H/F/X), Intérim, CESS, 24.000 € - 30.000 € brut/an, Saint-Ghislain, Le Forem, Éco-chèques |
| `fr_CH` | Switzerland | Eurostat SES (CHF) | Ingénieur CVC (H/F), Temporaire, CFC, CHF 57'500 - 77'500 brut/an, Sierre, jobs.ch, 13e salaire |
| `de_CH` | Switzerland | Eurostat SES (CHF) | Fachkraft Schutz- und Sicherheit (m/w/d), Befristet, EFZ, CHF 54'500 - 63'500 brutto/Jahr, 13. Monatslohn |
| `it_CH` | Switzerland | Eurostat SES (CHF) | agente di sicurezza (m/f), Lavoro temporaneo, AFC, CHF 54'500 - 63'500 lordi/anno, Tredicesima mensilità |
| `fr_CA` (`fr_QC`) | Canada | France × OECD | Ingénieur / Ingénieure CVC, Temps partiel, DES, 20 000 $ - 25 000 $ par année, Assurance collective |
| `de_DE` | Germany | Eurostat SES | Busfahrer (m/w/d), Unbefristet, 29.500 € - 34.000 € brutto/Jahr |
| `de_AT` | Austria | Eurostat SES | Befristet, Pflichtschulabschluss, 27.000 € - 31.500 € brutto/Jahr, Wien, karriere.at, Klimaticket |
| `de_LU` | Luxembourg | Eurostat SES | Zeitarbeit, DAP, 33.000 € - 38.500 € brutto/Jahr, Düdelingen, ADEM, Essensgutscheine |
| `es_ES` | Spain | Eurostat SES | Indefinido, 20.500 € - 26.000 € brutos/año |
| `es_MX` | Mexico | Spain × OECD | guarda de seguridad, Tiempo determinado, Secundaria, $135,000 - $160,000 MXN brutos al año, OCC Mundial |
| `es_CL` | Chile | Spain × OECD | Plazo fijo, Enseñanza media completa, $10.000.000 - $13.000.000 brutos anuales, Laborum |
| `es_CO` | Colombia | Spain × OECD | Término fijo, Bachiller, $24.500.000 - $29.000.000 anuales, Medellín, Prima extralegal |
| `it_IT` | Italy | Eurostat SES | Tempo indeterminato, RAL 26.000 € - 30.000 € |
| `pt_PT` | Portugal | Eurostat SES | Guarda (M/F), Trabalho temporário, 9.º ano, 14.000 € - 17.500 € brutos/ano, Ovar, Subsídio de alimentação |
| `pt_BR` | Brazil | ILOSTAT | Guarda, Meio período, Ensino fundamental, R$ 13.000 - R$ 16.000 por ano, Sine, Vale-refeição |
| `nl_NL` | Netherlands | Eurostat SES | beveiliger (m/v/x), Uitzendwerk, VMBO, € 25.000 - € 30.500 bruto per jaar, Leerdam, 13e maand |
| `nl_BE` | Belgium | Eurostat SES | beveiliger (m/v/x), Interim, € 30.000 - € 35.000 bruto per jaar, Kortenberg, VDAB, Ecocheques |
| `pl_PL` | Poland | Eurostat SES | pracownik ochrony osób i mienia (k/m), Umowa zlecenie, 38 500 - 48 000 zł brutto rocznie, Wieluń |
| `en_US` | United States | BLS OEWS | Full-time, 401(k) matching, $58,000 - $71,000 a year |
| `en_GB` | United Kingdom | US × OECD | corporate security guard, Part-time, GCSEs, £10,000 - £12,000 per annum, Workplace pension |
| `en_IE` | Ireland | Eurostat SES | Fixed-term contract, Leaving Certificate, €30,000 - €38,000 per annum, Dublin, IrishJobs.ie |
| `en_CA` | Canada | US × OECD | Permanent part-time, Secondary school diploma, $18,000 - $22,000 a year, Ottawa, Dental coverage |
| `en_AU` | Australia | US × OECD | Part time, Year 12, $23,000 - $29,500 + super, Brisbane, SEEK, Above-award salary |
| `en_NZ` | New Zealand | US × OECD | Part time, NCEA Level 2, $20,500 - $26,000 per annum, Wellington, KiwiSaver employer contribution |

"Eurostat SES": the country's own earnings and contract mix (Eurostat
Structure of Earnings Survey 2022 and Labour Force Survey); "France ×
OECD": those of the country of the language, scaled by the ratio of the
OECD average wages of the two countries (see [Salaries](#-occupations-rome--esco)).
**Every other country** (232 of the 244 of `job_countries`) gets neutral
conditions in the language of the occupations, with its own currency,
salaries and minimum wage: the locales of other countries (`es_AR`,
`fr_DZ`, `en_IN`, `ja_JP`, `pt_BR`, `nl_NL`...) post in their country, and
`country=` takes the conditions of the country of the job:

| Locale | Example |
|---|---|
| `ja_JP` | senior salesperson, Full-time, JPY 3,100,000 - 4,250,000 a year, Utsunomiya, Japan |
| `pt_BR` | senior salesperson, Full-time, BRL 22,000 - 27,500 a year, Macapá, Brazil |
| `en_IN` | senior salesperson, Full-time, INR 140,000 - 185,000 a year, Varanasi, India |
| `es_AR` | vendedor especializado en vehículos de motor, Indefinido, 9.000.000 - 12.000.000 ARS brutos al año, Avellaneda |
| `fr_DZ` | Technicien de mesure de la qualité de l'eau (H/F), CDI, 620 000 - 820 000 DZD brut/an, Chlef, Algeria |
| `fr_FR`, `country="Brazil"` | the same occupation, CDI, 34 500 - 45 000 BRL brut/an, Macapá, Brazil |
| `fr_FR`, `country="Belgium"` | the Belgian conditions (`fr_BE`): (H/F/X), Job étudiant, Le Forem, Belgique |

Neutral conditions have contracts, benefits and diplomas found in most
countries (Full-time / CDI / Unbefristet..., health insurance, meal
allowance...), international job boards (LinkedIn, Indeed, Glassdoor,
Jooble, Careerjet) and the ISO code of the currency in the salary. The
salaries are:
- those of the country's locales (France, Canada...), or the [Eurostat
  SES 2022](https://ec.europa.eu/eurostat/web/microdata/structure-of-earnings-survey)
  earnings for the other European countries it covers (Portugal, Poland,
  the Netherlands...: 25 more);
- else the [ILOSTAT](https://ilostat.ilo.org/) average monthly earnings of
  employees by ISCO-08 major group (~100 countries: India, Brazil,
  Argentina, South Africa...), latest year, brought to 2025 with the
  [World Bank](https://data.worldbank.org/indicator/NY.GDP.PCAP.CN) GDP per
  capita in local currency;
- else (Japan, China, Algeria...: ~70 countries) the GDP per capita times
  the median ratio of mean earnings to it, with the median earnings of
  each ISCO group; micro-states and territories take those of their
  neighbour or country (Monaco: France, Réunion: France, Jersey: United
  Kingdom), Taiwan hand-entered figures (DGBAS).

The minimum wage is ILOSTAT's (brought to the same year). Countries
without any figures (North Korea, Western Sahara, a few islands) keep the
locale's conditions. Hiring companies are made up by the Faker locale
outside the 17 countries with real ones, with the size shares of the
country of the language. These are **orders of magnitude**: the earnings
of broad groups, 2022 to 2026 depending on the source.

In the countries of several languages, the jobs of a locale are in the
regions of its language: `fr_CA` in Quebec and New Brunswick (Montréal,
Québec, Moncton), `fr_BE` in Wallonia and Brussels, `nl_BE` in Flanders
and Brussels, `fr_CH`, `de_CH` and `it_CH` in the cantons of their
language (`en_CA`: the whole of Canada). A French posting in Belgium
(`fr_FR` with `country="Belgium"`) takes the Belgian French conditions,
regions included.

Companies of a posting are in the country of the job and the activity
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
ones of the country (2,256 in the United States: IBM, Apple, Walmart,
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
#  'industry': 'Hébergement médicalisé pour personnes âgées',   # NAF label (NACE in de, es, it)
#  'city': 'Grenoble', 'state': None, 'zip': None, 'website': 'pharmacie-alliance.fr', 'ticker': None,
#  'ceo': None, 'founded': None}
```

| Method | English locales | German, Spanish, French, Italian locales |
|---|---|---|
| `job_title()`, `job_role()`, `job_role_record()`... | ESCO occupations, in English | ROME (fr) or ESCO (de, es, it) occupations, in the language |
| conditions (`job_qualification()`, `job_salary_range()`, `job_work_type()`...) | US | the country's |
| `job_location()` | the locale's country by default (the United States for `en`) | the locale's country by default, with local names (Deutschland, München, Sevilla, Roma, Anvers...) |
| `job_company()`, `job_company_profile()`, `job_companies` | companies of the country, LinkedIn industry | companies of the country, NAF (France) or NACE (other countries) activity |

Other countries are named in the language of the locale (Wikidata
labels: "Allemagne", "Germania", "Niemcy"; English in English locales),
their cities by their English name outside the countries of the language
("Munich" in a French posting); `country=` takes the English name, the ISO
code or the name in the language (`country="Deutschland"`,
`country="Allemagne"`).

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
  statistics for France, Germany, Spain, Italy, Belgium, Austria,
  Luxembourg, Ireland and Switzerland (persons employed by NACE
  section and size group 2-9, 10-49, 50-249, 250+), the Census Statistics
  of US Businesses 2022, the UK business population estimates 2026 and the
  OECD business statistics for Canada, Brazil and New Zealand (1-9 and 10+ only). Each
  official size group gets its share, split between the LinkedIn classes it
  holds as LinkedIn splits them (number of companies × typical size), as
  LinkedIn lists few small companies. About 1 posting in 10 is in a company
  of up to 10 employees in the United States, 1 in 6 in France and
  Germany, 1 in 4 in Italy; 44% (United States) to 69% (Italy) in companies of up to 250
  employees (a third or less before the official shares). Building works
  hire in small companies, energy in large groups. Sectors without official
  figures (agriculture and public administration in Europe) and countries
  without them (Mexico, Chile, Colombia, Australia: only 4-8% of their
  postings in companies of up to 10 employees) keep the LinkedIn shares; French mining, water supply and waste, confidential,
  take the split of the European Union.
- Then a **real company** of that sector and class: up to 10 per class,
  sector and country (~23,000 in all, 540 KB), with its name, website,
  founding year, headquarters city (and US state) and number of employees.
  The headquarters are those of [Wikidata](https://www.wikidata.org/) when
  it knows the company (by its LinkedIn ID) in the same country, as LinkedIn
  often gives an office or a region (Walmart: Bentonville, not Withee);
  LinkedIn's city otherwise, matched to GeoNames with its alternate names
  ("Dusseldorf", "Brunswick"); `None` when LinkedIn only gives a region or a
  country ("West Sussex"). A few large groups are placed by hand.
  Companies of 1-10 employees are left out (many are one-person businesses
  named after their owner): they are made up by the Faker locale, as the
  companies of a class with fewer than 10 companies in the dataset at
  random (so that no large group gets every job of its class) and those of
  the jobs outside the countries of the locales with conditions of their
  own. Made-up companies are in the city
  of the job, with a made-up CEO.
- Companies of up to 500 employees hire in their headquarters city when it
  is a city of `job_location()`; larger ones anywhere in the country.
- `company_size` is the company's number of employees; `industry` its
  LinkedIn industry in English locales; elsewhere an activity of the
  sector (`company_naf`, and its label as `industry`): a sub-class of the
  French NAF rév. 2 in French locales ('86.10Z'), a class of NACE Rev. 2 in
  the other countries and languages ('86.10', also the class of WZ 2008,
  CNAE-2009, ATECO 2007, CAE, SBI and PKD), one that employs the occupation and fits the
  LinkedIn industry of a real company (Air France: air transport, not
  passenger water transport; see below).

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
#     'company_naf': '49.41A',                  # NAF rév. 2 activity (NACE class in de, es, it; None in English)
#     'seniority': 'mid',                       # 'junior' (< 3 years asked), 'mid' (3-7), 'senior' (8+)
#     'job_portal': 'HelloWork',                # APEC and Cadremploi for executive jobs only
#     'contact_person': 'Agathe Evrard de Lopez', 'contact': '+33 (0)3 51 39 07 57',
#     'remote': 'on_site',                      # 'on_site', 'hybrid' or 'remote' (full remote)
#     ...
# }
```

**Remote work** (`remote`) follows the country and the job: the share of
postings offering hybrid or full remote work is the country's share of
employees working from home, usually or sometimes (Eurostat LFS 2025, 37
European countries; the EU's elsewhere), times a factor of the occupation's
ISCO major group (hand-made: about 2 for managers and professionals, 0.1 to
0.2 for manual jobs). About 30% of the French postings, 45% of the Dutch
ones, 8% of the Italian ones; 70% of the French postings of professionals,
1% of elementary occupations. Part of them (half the share working from
home "usually") are full remote. The posting text says it.

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

The other countries of [Languages and countries](#-languages-and-countries)
get their own conditions in the same way (Job étudiant, Lehre, Honorarios,
Casual...; Chèques-repas, Halbtax-Abo, Vales de despensa, KiwiSaver...; Le
Forem, jobs.ch, OCC Mundial, SEEK...). Where ROME sheets list French
diplomas (CAP, BTS...), Belgian, Swiss and Canadian postings ask for local
ones (CESS, CFC, DEC...); their companies get the NACE class of their NAF
activity ('86.10'). The other countries get neutral conditions in the
language with their own economy (see
[Languages and countries](#-languages-and-countries)).

**Salaries follow the occupation.** The occupation's ISCO-08 major group
(`isco_group`, from ESCO) gives its mean gross annual earnings in the
country: [Eurostat SES 2022](https://ec.europa.eu/eurostat/web/microdata/structure-of-earnings-survey)
by major group and NACE section of the company (that of its NAF / NACE
activity, else that of the occupation's sector; France, Germany,
Spain, Italy, Belgium, Switzerland in CHF, Austria, Luxembourg, Ireland),
[BLS OEWS](https://www.bls.gov/oes/) by SOC major group (United
States). Countries without such a survey (Canada, Mexico, Chile, Colombia,
the United Kingdom, Australia, New Zealand) take the earnings of the
country of their language (France, Spain or the United States) times the
ratio of the [OECD average annual wages](https://www.oecd.org/en/data/indicators/average-wages.html)
of the two countries in national currency, the same year (2022 with
Eurostat, 2025 with BLS): a Mexican salary is the Spanish one × 7.3, in
MXN. Amounts are rounded to 500 or 1,000 (10 times more in MXN, 1,000 times
in CLP and COP). That mean is then adjusted:
- to the experience asked, by the ratio of the matching age band (under
  30, 30-49, 50 and over) to the group's mean;
- to the contract: about 30% of a full-time salary for an internship, 55%
  for an apprenticeship, half for part-time;
- and kept above the minimum wage for a full-time employee (the OECD
  statutory minimum wage of the year of the earnings outside France,
  Germany, Spain, Italy and the United States; none in Austria and
  Switzerland, where collective agreements set the wages).

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
(the countries of the Eurostat earnings): the weight of the temporary contracts is
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
and the countries with OECD-scaled earnings keep the national mix for
every occupation.

Benefit rules, job boards, default diplomas and their fields of study are
hand-made and **illustrative** (`scripts/posting_conditions.py`).

The activities of each sector are chosen by hand (`NAF_BY_SECTOR` in
`scripts/build_occupations.py`; NACE classes are those of the NAF
sub-classes) and picked **for the occupation**: by the employees of its
ISCO unit group in each activity, from the 2022 French census (INSEE
detailed file: profession × NAF sub-class of the employees, professions
mapped to ISCO-08 by the INSEE PCS 2020 × ISCO matrix), so an aquaculture
worker works in aquaculture or sea fishing, not fibre crops, and a nurse
mostly in hospitals. The French figures are used for German, Spanish and
Italian postings too. Then a real company whose LinkedIn industry has that
activity (`scripts/naf_industries.py`, hand-made: "logistics and supply
chain" -> 49.4 road freight, 52 warehousing and support), else a made-up
one. Occupations without census figures in the sector get an activity by
**employment**: each sub-class or class weighs the persons employed in its
NACE group in the country (Eurostat structural business statistics),
shared by the sub-classes or classes of the group, so road freight comes up
about 30 times more often than passenger water transport (the median weight
of the sector for public administration and associations, which have no
figures), among those that fit the LinkedIn industry of a real company.

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

Job ids are 15 or 16-digit numbers by default; a template gives them your
own format (a string):

```python
fake.job_id("JOB-{year}-######")        # 'JOB-2026-417776'
fake.job_id("{country}-{date:%y%m}-****")   # 'FR-2611-NG5B'
fake.job_id("REQ{n:05d}", n=42)         # 'REQ00042'
fake.job_posting(id_template="{country}-{date:%Y%m%d}-###")["job_id"]   # 'JP-20250124-907'
```

| In the template | Gives |
| --- | --- |
| `#` / `?` / `*` | a random digit / uppercase letter / either |
| `{year}`, `{month}`, `{day}`, `{date}` | the posting date (`date=`, default today; in postings, their date), with format specs: `{month:02d}`, `{date:%y%m%d}` |
| `{country}` | the ISO code of the country of the job (`country=`, default the locale's): `FR` |
| `{locale}` | the Faker locale: `fr_FR` |
| `{n}` | the posting's number (`n=`; from 1 in datasets): `{n:06d}` |

Other characters are kept. `job_posting()`, `job_occupation_posting()`,
`job_dataset()` and `make_dataset()` take `id_template=`; in datasets the
ids are unique (a template with too few random characters raises an error).

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
#     'remote': 'hybrid',
# }
```

It is `job_occupation_posting()` in the `JobPosting` shape: use that one for
the NAF / NACE code and company sector.

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

### 📊 Datasets: employers and their postings

`job_dataset()` builds a whole dataset: a pool of employers and the
postings they publish over a period, as two flat tables linked by
`company_id`, ready for a CSV, JSON Lines or pandas export.

```python
fake = Faker("fr_FR")
fake.add_provider(JobsProvider)

data = fake.job_dataset(postings=10_000, companies=800, start_date="2025-01-01", end_date="2026-10-31")
data.companies[0]
# {'company_id': 'C00001', 'locale': 'fr_FR', 'name': 'Stehlin & Associés Avocats',
#  'sector': 'Activités juridiques et comptables', 'industry': 'Activités juridiques',
#  'activity_code': '69.10Z', 'employees': 101, 'city': 'Paris', 'country': 'France',
#  'website': 'stehlin-legal.com', 'founded': 1989, 'real': True}
data.postings[0]
# {'job_id': 4737973820883535, 'company_id': 'C00069', 'locale': 'fr_FR',
#  'job_title': 'Courtier en banque (H/F)', 'occupation_code': 'C1208', 'isco_code': '3324', ...,
#  'work_type': 'CDD', 'remote': 'on_site', 'salary_min': 28500, 'salary_max': 35500, 'salary_currency': 'EUR',
#  'city': 'Périgueux', 'country': 'France', 'job_portal': 'Le Bon Coin Emploi',
#  'posted_date': '2026-10-06', 'closed_date': '2026-10-18', 'status': 'expired', 'repost_of': None,
#  'skills': 'Ecouter les besoins des clients; ...', 'benefits': 'Horaires flexibles; ...',
#  'contact_person': 'Claire Martin', 'contact_email': 'claire.martin@stehlin-legal.com', 'contact': '...'}

data.to_csv("out/")             # out/companies.csv, out/postings.csv
data.to_jsonl("out/")           # out/companies.jsonl, out/postings.jsonl
companies, postings = data.to_dataframes()   # needs pandas
```

- **Employers** (`companies`, default: one per 10 postings) are hiring
  companies of the locale's country, as in the postings: real or made up,
  by size class from the official shares of jobs, spread between the
  sectors by the demand of their occupations. Each keeps its name, city,
  size and activity in all its postings; those of up to 500 employees hire
  in their city. The pool grows when a sector has none of them.
- **Postings**: an occupation by demand, then an employer of its sector,
  favouring those whose activity employs the occupation. An employer
  publishes several postings (a few dozen for the busiest of a pool of 150
  for 1,500 postings).
- **Salaries over time**: those of the postings on `end_date`; earlier
  postings are lower by the country's yearly growth of the GDP per capita in
  local currency (World Bank, latest 5 years: about 5% a year in France, 7%
  in the United States, much more where inflation is high).
- **Lifecycle**: a publication date in the period (seasonal contracts from
  March to September), a closing date about a month later (log-normal) and
  a status on `end_date`: `open` (still on line, no closing date), `filled`
  (70% of the others) or `expired`.
- **Republications**: 8% of the postings (`repost_rate`) are published again
  on another job board a few days later, with a new `job_id` and
  `repost_of` the first one's, as on job boards: a test case for
  deduplication.
- **Recruiters**: each employer has its own (1 up to 50 employees, 2 up to
  500, 3 up to 5,000, else 4), with an e-mail address at the company's
  domain (its website, or one made of its name: `claire.martin@samson.fr`);
  each posting names one of them.

**Candidates and applications**: `candidates=2000` adds a pool of job
seekers and their applications to the postings, two more tables linked by
`candidate_id` and `job_id` (`candidates.csv`, `applications.csv`):

```python
data = fake.job_dataset(postings=1000, candidates=2000, applications=10)
data.candidates[0]
# {'candidate_id': 'P000001', 'locale': 'fr_FR', 'name': 'Alphonse Michel', 'email': 'alphonse.michel@voila.fr',
#  'phone': '03 64 60 83 77', 'city': 'Rennes', 'country': 'France', 'occupation_code': 'D1116',
#  'occupation': 'Négociant / Négociante en bétail', 'job_title': 'Chevillard / Chevillarde', ...,
#  'experience_years': 6, 'qualification': 'Bac pro ...', 'skills': '...; ...',
#  'desired_salary': 41500, 'salary_currency': 'EUR', 'availability': '1_month'}
data.applications[0]
# {'application_id': 'A0000001', 'job_id': 8207814926684802, 'candidate_id': 'P001093',
#  'applied_date': '2025-09-01', 'match_score': 48, 'status': 'rejected', 'status_date': '2025-09-15'}
data.to_dataframe("applications")       # any table as a DataFrame (needs pandas)
```

- **Candidates** have an occupation picked by demand, the title they look
  for, years of experience for its skill level, a diploma, some of its
  skills, the salary they ask (around the local earnings of the occupation
  at their experience), their availability, a personal e-mail address.
  `fake.job_candidate()` returns one (`CandidateRecord`).
- **Applications**: about `applications` a posting (a mean, spread), from
  candidates of the same occupation, else of its ISCO unit group, its
  sector or any, preferring the posting's city; each with a **match score**
  (0-100: skills in common 40, experience in the range asked 25, salary
  within the offer 20, place 15).
- **Statuses follow the posting**: a filled posting hires one applicant
  (better scores more likely; a candidate is hired once at most while the
  pool has free ones), the others are `rejected` or `withdrawn`; an expired
  one rejects all; an open one has applications `in_review`, at
  `interview` or already `rejected`.

**Dirty data**: `dirty=0.1` adds defects of real-world job data to 10% of
the rows, to test cleaning, validation and deduplication pipelines; each one
is listed in `data.defects` (and `defects.csv`), the ground truth of a
cleaning:

```python
data = fake.job_dataset(postings=1000, dirty=0.1)
data.defects[:2]
# [{'table': 'postings', 'id': '7660917990749480', 'field': 'posted_date', 'kind': 'date_format',
#   'original': '2025-06-08'},            # the posting now reads '08.06.2025'
#  {'table': 'postings', 'id': '9073136867723843', 'field': None, 'kind': 'duplicate',
#   'original': '4393629242208145'}]      # a copy of that posting, not flagged by repost_of
```

| Kind | Defect |
| --- | --- |
| `typo` | a letter swapped, dropped or doubled in the job title or the city |
| `case`, `whitespace` | job title in upper / lower case, extra spaces or tabs |
| `missing` | salaries, city, qualification, contact, experience or benefits left empty |
| `monthly_salary` | a monthly amount in the yearly salary fields |
| `swapped_salary` | the minimum salary above the maximum |
| `date_format` | `posted_date` as '13/11/2026', '11/13/2026', '13.11.2026', '2026/11/13' or '13 Nov 2026' |
| `duplicate` | the posting again under another id, a day or two later, maybe with a case or spacing change |
| `name_variant` | a company again under another id and a variant of its name (upper case, legal form, typo), with a third of its postings |
| `missing` (companies) | website, founding year or city left empty |

`make_dataset()` mixes locales, each in its country and language, with
company ids prefixed by the locale; `seed` makes it reproducible:

```python
from faker_jobs.dataset import make_dataset

data = make_dataset({"fr_FR": 0.6, "de_DE": 0.3, "pl_PL": 0.1}, postings=10_000, seed=42)
```

From the command line:

```bash
python -m faker_jobs export out/ --locale fr_FR --postings 10000 --companies 800 --seed 42
python -m faker_jobs export out/ --locale fr_FR:0.6 --locale de_DE:0.4 --format jsonl \
    --start-date 2025-01-01 --end-date 2026-10-31
python -m faker_jobs export out/ --id-template "JOB-{year}-{n:06d}"   # job ids from a template
python -m faker_jobs export out/ --dirty 0.1                          # 10% of the rows with a defect
python -m faker_jobs export out/ --candidates 2000 --applications 12  # candidates and applications
```

10,000 postings take a few seconds.

### 🔤 Type hints

The package ships type information (`py.typed`) and `TypedDict`s describing
the returned dicts: `RoleRecord`, `LocationRecord`, `CompanyProfile`,
`JobPosting`, `OccupationRecord`, `OccupationPosting`, and the rows of the
datasets, `CompanyRow` and `PostingRow` (`faker_jobs.dataset`). Methods added to a `Faker` instance by `add_provider()` are not
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
python -m faker_jobs                  # a demo of the methods, in English
python -m faker_jobs --locale fr_FR   # in other locales (repeat --locale)
python -m faker_jobs export --help    # write a dataset (see Datasets)
```

---

## 🧱 Data layout

The source files in `DATAS/` are not published in this repository: the
package only needs the generated files of `faker_jobs/data/`. They are
only needed to rebuild them.

The cities come from GeoNames:

```
DATAS/geonames/cities15000.zip, countryInfo.txt   GeoNames dump (download.geonames.org/export/dump/)
DATAS/geonames/alt_<code>.zip                     alternatenames/<code>.zip of FR, DE, ES, IT, PT, NL, PL, BE,
                                                  CH, AT, LU, CA, MX, CL, CO, BR: local and English names
DATAS/wikidata/country_names.json                 country names in fr, de, es, it, pt, nl, pl (Wikidata labels)
scripts/
  build_cities.py [--download] [--fetch-country-names]
                                -> faker_jobs/data/cities.json.gz (~500 KB)
```

Occupations have their own sources and scripts:

```
DATAS/metiers/rome-4-0-métiers-×-secteurs-d-activité.xlsx   ROME 4.0 v62 (France Travail)
DATAS/esco/EURESmapping_occs_FR_v1.0.9.csv   ROME 4.0 -> ESCO 1.0.9 crosswalk (ESCO portal, France)
DATAS/esco/esco_occupations_v1.0.9.json      English ESCO data, cached by fetch_esco.py
DATAS/esco/esco_occupations_v1.0.9_{de,es,it,pt,nl,pl}.json   same in German, Spanish, Italian, Portuguese,
                                             Dutch, Polish
DATAS/bmo/Base-open-data-BMO-2026.xlsx       BMO 2026 recruitment projects (France Travail, data.gouv.fr)
DATAS/bmo/Dares_FAP2021_Table_passage_ROME.xlsx   FAP 2021 -> ROME table (DARES; its site blocks
                                             scripts: download it in a browser or from the Web Archive)
DATAS/naf/naf2008_liste_n5.xls               NAF rév. 2 sub-classes (INSEE)
DATAS/nace/labels.json                       NACE Rev. 2 classes in German, Spanish, Italian, by fetch_activities.py
DATAS/insee_rp/RP2022_indreg.parquet         2022 census detailed file "Individus localisés à la région"
                                             (INSEE, ~620 MB: --download)
DATAS/insee_rp/Matrice_PCS_ISCO.csv          PCS 2020 -> ISCO-08 matrix (INSEE)
DATAS/insee_rp/isco_naf.json                 employees by ISCO unit group and NAF sub-class, by fetch_activities.py
DATAS/salaries/eurostat_ses2022.json         Eurostat SES 2022 earnings, cached by fetch_salaries.py
DATAS/salaries/bls_oews.json                 BLS OEWS mean wages, cached by fetch_salaries.py
DATAS/salaries/eurostat_lfs.json             Eurostat LFS 2025 temporary, part-time, self-employed workers
                                             by ISCO group, cached by fetch_salaries.py
DATAS/salaries/oecd_wages.json               OECD average annual wages and minimum wages, national currency,
                                             cached by fetch_salaries.py
DATAS/salaries/ilostat.json                  ILOSTAT monthly earnings by ISCO group and minimum wages, by
                                             fetch_salaries.py
DATAS/salaries/worldbank_gdp.json            World Bank GDP per capita (current LCU), by fetch_salaries.py
scripts/
  fetch_esco.py [language]      ESCO web-service API -> the caches above (~2,000 requests each, resumable)
  fetch_salaries.py             Eurostat, BLS, OECD, ILOSTAT and World Bank APIs -> the caches above
  fetch_activities.py [--download]   census + matrix -> isco_naf.json; EU Vocabularies SPARQL -> labels.json
  posting_conditions.py         local contracts, benefits, job boards, diplomas by locale and country
  rome_labels.py                ROME sectors, domains and soft skills in English, German, Spanish, Italian
  build_occupations.py          -> faker_jobs/data/occupations_{de_DE,en_US,es_ES,fr_FR,it_IT,nl_NL,pl_PL,pt_PT}.json.gz
                                   and faker_jobs/data/conditions.json (posting conditions of the 20
                                   locales, plain JSON; a country locale only holds what differs
                                   from its language's: `base`)
                                   and faker_jobs/data/countries.json (economy of 232 countries,
                                   neutral conditions of each language; needs countryInfo.txt)
                                   (with the ROME code of each sector, the key of companies.json.gz)
```

The hiring companies come from People Data Labs, their sizes from official statistics:

```
DATAS/7millionscompanies/companies_sorted.csv   People Data Labs Free Company Dataset (7.2 million rows, 1 GB)
DATAS/business_sizes/us_state_naics_detailedsizes_2022.xlsx, us_naicssector_large_emplsize_2022.xlsx
                                             Census SUSB 2022 (census.gov, no API: --download)
DATAS/business_sizes/BPE_2026_detailed_tables.xlsx   UK business population estimates 2026 (gov.uk)
DATAS/business_sizes/sizes.json              employment by size group and NACE section, by fetch_business_sizes.py
                                             (Eurostat, Census, UK and OECD SDBS figures)
DATAS/wikidata/headquarters.json             Wikidata headquarters of the companies (by LinkedIn ID), cached by
                                             build_companies.py --fetch-headquarters
scripts/
  fetch_business_sizes.py [--download]   Eurostat (sbs_sc_ovw) and OECD SDBS APIs + the spreadsheets above
                                         -> sizes.json
  build_companies.py [csv] [--fetch-headquarters]
                                -> faker_jobs/data/companies.json.gz (~540 KB; after build_cities.py,
                                   build_occupations.py and fetch_business_sizes.py; --fetch-headquarters
                                   queries Wikidata for the companies missing from the cache)
```

```bash
for l in en de es it; do python scripts/fetch_esco.py $l; done   # only if the crosswalk changed
pip install -e ".[build]"         # openpyxl, xlrd and pyarrow, to read the xlsx/xls/parquet sources
python scripts/fetch_activities.py   # only for a new census (--download it, ~620 MB)
python scripts/build_cities.py      # first: build_companies.py matches cities to its output
python scripts/build_occupations.py
python scripts/fetch_business_sizes.py   # only when newer statistics are out (--download the spreadsheets)
python scripts/build_companies.py --fetch-headquarters   # Wikidata only for new companies
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
- BMO 2026 © France Travail, FAP 2021 → ROME table © DARES, NAF rév. 2,
  2022 census and PCS 2020 × ISCO-08 matrix © INSEE:
  [Licence Ouverte / Etalab 2.0](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
- NACE Rev. 2 labels in German, Spanish, Italian, Portuguese, Dutch and Polish: [EU Vocabularies](https://op.europa.eu/en/web/eu-vocabularies)
  © European Union, reused under Commission Decision 2011/833/EU.
- Earnings and labour figures: Eurostat SES 2022 and LFS 2025 © European
  Union (reuse authorised, source acknowledged); BLS OEWS, U.S. Bureau of Labor Statistics (public domain).
- Employment by enterprise size: Eurostat structural business statistics
  (sbs_sc_ovw) © European Union (reuse authorised, source acknowledged);
  Statistics of US Businesses 2022, U.S. Census Bureau (public domain);
  Business population estimates 2026, Department for Business and Trade,
  [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- English, German, Spanish, Italian, Portuguese, Dutch and Polish labels of the 35 ROME activity
  sectors, 14 domains and 16 soft skills are translated by this project.

Cities: [GeoNames](https://www.geonames.org/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Hiring companies: [People Data Labs Free Company Dataset](https://docs.peopledatalabs.com/docs/free-company-dataset),
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (a sample of it,
names capitalized and industries mapped to activity sectors by this project);
headquarters from [Wikidata](https://www.wikidata.org/) ([CC0](https://creativecommons.org/publicdomain/zero/1.0/)).
