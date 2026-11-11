# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed
- Headquarters of the real companies: Wikidata's (CC0, by LinkedIn company ID: P4264 → P159) when it is in the company's country, as LinkedIn often gives an office or a region (IBM: New York City, Dassault Aviation: Paris instead of "France"); a few large groups placed by hand (Walmart: Bentonville instead of Withee, Asda: Leeds instead of "West Yorkshire", Porsche: Stuttgart). LinkedIn cities are matched to GeoNames with its alternate names and without accents ("Dusseldorf", "Brunswick", "New York", "Perret" for Levallois-Perret): 8,900 of the 10,500 companies have a city of `job_location()` instead of 7,900. A region or a country given as city ("West Sussex", "Berks", "France") gives `city` None instead of its name (~290 companies, mostly British). Cached in `DATAS/wikidata/headquarters.json` (`build_companies.py --fetch-headquarters`).
- The activity of the hiring company follows the occupation: French, German, Spanish and Italian postings pick it among the activities of the sector by the employees of the occupation's ISCO unit group in each of them, from the 2022 French census (INSEE detailed file "Individus localisés à la région": profession × NAF sub-class of the employees; professions mapped to ISCO-08 by the INSEE PCS 2020 × ISCO matrix; Licence Ouverte / Etalab 2.0). An aquaculture worker now works in aquaculture or sea fishing (99.9% of the postings, was fibre crops, cereals...), a nurse mostly in hospitals. The activity is picked first, then a real company of the class whose LinkedIn industry has it, else a made-up company (real companies: 54-63% of the postings in these locales instead of 61-68%). Occupations without census figures in the sector keep the activities picked by employment. New `scripts/fetch_activities.py` caches the figures in `DATAS/insee_rp/isco_naf.json`; the occupation files hold them by ISCO unit group and sector (`naf_by_isco`, ~40 KB more each, gzipped).
- German, Spanish and Italian postings and companies get an activity: a NACE Rev. 2 class of the sector (`company_naf`, e.g. '86.10', also the class of WZ 2008, CNAE-2009 and ATECO 2007; its label in the language as the company's `industry`, instead of None), weighted by the persons employed in its NACE group in the country (Eurostat SBS) and fitted to the LinkedIn industry of real companies, as in French locales. Their salary follows the NACE section of that activity. Labels from EU Vocabularies (Commission Decision 2011/833/EU), cached in `DATAS/nace/labels.json`; `conditions.json` gives `naf_by_sector` and `naf_by_industry` (prefixes cut to classes) for these locales.
- The `build` extra adds pyarrow (to read the census Parquet file).

---

## [0.8.0] - 2026-11-11

### Changed
- The size of the hiring companies follows official statistics of employment by enterprise size, as LinkedIn (People Data Labs) lists few small companies: Eurostat structural business statistics (France, Germany, Spain, Italy: persons employed by NACE section and size group 2-9, 10-49, 50-249, 250+), Census Statistics of US Businesses 2022 and the UK business population estimates 2026. Each official size group gets its share in the sector's NACE section, split between the LinkedIn size classes it holds as LinkedIn splits them. Postings in companies of up to 10 employees go from 3-10% to 10% (United States) to 27% (Italy); 44% (United States) to 69% (Italy) of the postings are in companies of up to 250 employees. `job_company_size()` follows the same shares. Sectors without official figures (agriculture and public administration in Europe, mining and water in France) keep the LinkedIn shares. New `scripts/fetch_business_sizes.py` caches the figures in `DATAS/business_sizes/sizes.json`.
- French postings: the NAF activity of the company is picked by employment (persons employed of its NACE group in France, Eurostat SBS, shared by the sub-classes of the group) instead of uniformly within the sector: road freight comes up ~30 times more often than passenger water transport (4.3% → 0.2% of the "Logistique et transport" postings). A real company only gets the activities of the sector that fit its LinkedIn industry (new `scripts/naf_industries.py`: 148 industries → NAF prefixes), so Air France is in air transport. `conditions.json` gives a weight to each NAF activity of `naf_by_sector` (4th element) and the NAF prefixes of each LinkedIn industry (`naf_by_industry`).
- The salary of a posting follows the NACE section of its company's NAF activity, now picked after the company (French locales).

---

## [0.7.0] - 2026-11-11

### Added
- Hiring companies from the People Data Labs Free Company Dataset (7 million companies from LinkedIn pages, CC BY 4.0): `faker_jobs/data/companies.json.gz` (~250 KB) holds about 10,000 real companies of the United States, the United Kingdom, France, Germany, Spain and Italy (up to 10 per country, activity sector and size class, from 11 employees: name, website, founding year, headquarters city, US state, number of employees, LinkedIn industry) and the share of jobs of each size class (1-10 ... 10,001+ employees) by country and sector. For 10,001+ employees, the largest groups of each sector (IBM, Apple, Walmart, Microsoft...). Built by `scripts/build_companies.py` from `DATAS/7millionscompanies/companies_sorted.csv`; LinkedIn industries are mapped by hand to the 35 activity sectors.
- `CompanyProfile.founded`: the company's founding year (None for made-up companies).
- `job_location(country=...)` also takes ISO codes ('US', 'FR') and the short names of 0.6 ('USA', 'UK', 'UAE').

### Changed
- The hiring company of `job_occupation_posting()` and `job_posting()`, in every locale: a size class is picked by the share of jobs of each class in the occupation's sector and the job's country, then a real company of that class and sector, or one made up by the Faker locale for 1-10 employees, at random in classes of fewer than 10 companies (no large group gets every job of its class), and outside the six countries. Postings now range from small businesses to large groups (30-50% of them in companies of up to 250 employees) instead of 12,600 to 135,000 employees; `company_size` is the company's own size, the same in every posting. Companies of up to 500 employees hire in their headquarters city. Every posting has a company of its sector: English postings no longer get a bare made-up name with `company_sector` None (about 1 in 5), and the Kaggle companies, all large groups with their headquarters around the world, are no longer used in postings.
- **Breaking**: `job_company()`, `job_company_profile()`, `job_companies` and `job_sectors` use these companies in every locale. `job_sectors` is the list of the 35 activity sectors (as `job_activity_sectors`) instead of the 204 Kaggle sector labels in English locales: a Kaggle label ("Financial Services") raises `ValueError`. `job_companies` lists the real companies of the locale's country. `job_company_profile(company=...)` returns that company of the country, or, for an unknown name, a company of that name made up by the Faker locale (instead of `ValueError` in English locales). `ticker` and `zip` are always None, `ceo` is None for real companies. `job_company_size()` picks a size class by the share of jobs in the locale's country.
- **Breaking**: country names are those of GeoNames: 'United States', 'United Kingdom', 'United Arab Emirates', 'South Korea', 'Czechia'... instead of the Kaggle names ('USA', 'UK', 'UAE', 'Rep. of Korea', 'Czech Republic'...); `job_countries` lists the 244 countries with a city of 15,000 inhabitants or more (216 Kaggle countries, some of them with Kaggle cities, before).
- `en_GB`: jobs are located in the United Kingdom by default, with British companies (conditions stay those of the United States).
- `conditions.json` gives the ROME code of each activity sector (`sector_codes`).
- New `build` extra (`pip install -e ".[build]"`): openpyxl and xlrd, needed only to rebuild `faker_jobs/data` from `DATAS/`; the `dev` extra includes it.

### Removed
- Every Kaggle "Job Description Dataset" file: the 888 companies of `faker_jobs/data/jobs_data.json` (188 KB), and the scripts that built them or explored the dataset (`fix_locations_encoding.py`, `geocode_locations.py`, `transform_firms.py`, `transform_job_descriptions.py`, `scripts/build_data.py`, `build_job_stats.py`, `build_sample.py`, `build_report.py`). `scripts/build_cities.py` no longer reads `DATAS/faker_locations.csv`.

---

## [0.6.0] - 2026-11-08

### Added
- `job_posting_text(posting=None, markdown=False)`: the full text of a job posting, as published on a job board, in French, English, German, Spanish or Italian (the language of the occupation data): headline, company introduction, the job (ESCO description, or the ROME sheet's name and domain), missions, profile asked (diploma, experience, knowledge, soft skills, regulated profession), conditions (contract, salary, place, benefits) and how to apply. It renders a posting from `job_occupation_posting()` or `job_posting()` (a new `job_occupation_posting()` by default), in plain text or Markdown. The wording is hand-made, with a few phrasings per section picked by the provider's random generator (`faker_jobs/posting_text.py`); every fact comes from the posting.

### Changed
- Job locations are the 29,536 cities of 15,000 inhabitants or more of GeoNames (CC BY 4.0) in the 216 countries, instead of the 457 Kaggle cities (12 in France, 20 in the USA): 462 cities in France, 945 in Germany, 497 in Spain, 531 in Italy, 2,849 in the USA. They are picked in proportion to their population, without the districts counted in their city ("Paris 15 Vaugirard"). Cities carry their English name ('Munich'), and in the locale's own country their local name for German, Spanish, French and Italian locales ('München', 'Roma'), from GeoNames instead of a short hand-made list. New `faker_jobs/data/cities.json.gz` (~500 KB), built by `scripts/build_cities.py` (`--download` fetches the GeoNames files into `DATAS/geonames/`); `jobs_data.json` keeps only the companies.
- The posting conditions (contracts, diplomas, benefits, salaries...) move from the gzipped occupation files to `faker_jobs/data/conditions.json`, plain indented JSON: changing a condition no longer rewrites the 3.6 MB of occupations, which keeps the git history small. Builds are reproducible: floats are rounded to 6 digits and every gzipped file has a fixed timestamp, so an unchanged build gives the same bytes whatever the Python version.
- `job_countries` lists every country once, sorted (it repeated a country for each of its cities).
- More default diplomas, asked by ESCO occupations and ROME sheets without diploma: national diplomas that were missing (Meister, Fachwirt, Promotion; FP Básica, Doctorado; Diploma di istituto tecnico / professionale, Dottorato; Doctoral degree, apprenticeships), and diplomas that name the field of study of the occupation's sector ("Abgeschlossene Berufsausbildung im Bereich Logistik", "Ciclo Formativo de Grado Medio en Sanidad", "Laurea magistrale in Informatica", "Bachelor's degree in Computer Science", "BTS commerce"). Fields of study are hand-made, by activity sector (`FIELDS_OF_STUDY` in `scripts/posting_conditions.py`); `job_qualification()` picks one of a random sector.

---

## [0.5.0] - 2026-11-07

### Removed
- **Breaking**: the Kaggle job data. Job titles, roles and their texts, qualifications, experience and salary ranges, work types, benefits and job portals of the Kaggle dataset are no longer shipped (`jobs_data.json`: 470 KB → 225 KB); `job_posting(source="kaggle")`, `JobsProvider.use_kaggle_data`, `job_qualification_name()`, `job_qualification(full_name=...)` and `job_benefits(weighted=...)` are gone, and `JobPosting` loses its `source` key (`occupation` is never None).

### Changed
- **Breaking**: the generic methods use the ROME / ESCO occupations and local conditions in every locale. English locales (`en_US`, `en_GB`, `nl_NL`...) get the ESCO occupations in English with the US conditions: `job_title()` / `job_role()` / `job_role_record()` are occupations, `job_qualification()`, `job_experience()`, `job_salary_range()`, `job_work_type()`, `job_benefits()` and `job_portal()` the US ones, `job_location()` a city of the USA by default. Locales without data of their own (`en_GB`, `nl_NL`, `ja_JP`...) also get the US conditions in `job_occupation_posting()`, instead of the Kaggle ones.
- `job_posting(job_title=..., role=...)` picks the occupation by one of its job titles or by its name, in every locale.
- The Kaggle dataset is kept for the 457 cities and the 888 companies, which English locales still use (`job_company_profile()`, the hiring company of the postings).

---

## [0.4.0] - 2026-11-06

### Changed
- **Breaking**: in German, Spanish, French and Italian locales the generic methods no longer return the English Kaggle data. `job_title()` / `job_titles` give the job titles of the occupations, `job_role()` / `job_roles` the occupation names, `job_role_record()` (and `job_description`, `job_skills`, `job_responsibilities`) the occupation texts as in `job_posting()`; `job_qualification()`, `job_experience()`, `job_salary_range()`, `job_salary_bounds()`, `job_work_type()`, `job_benefits()` and `job_portal()` the local conditions; `job_location()` a place of the locale's country by default; `job_company()`, `job_company_profile()` and `job_sectors` a company made up by the locale in an activity sector (with a NAF activity in French locales). English locales are unchanged. Set `use_kaggle_data = True` on a `JobsProvider` subclass for the previous behaviour.
- **Breaking**: German, Spanish and Italian postings (`job_occupation_posting()`, `job_posting()`) get a company made up by the locale, in the occupation's sector, instead of an American Kaggle company.
- **Breaking**: places in the locale's own country carry local names in those locales: `Deutschland` / `München`, `Köln`; `España` / `Sevilla`; `Italia` / `Roma`, `Milano`, `Napoli`, `Torino`, `Genova`, `Firenze`. `job_location(country=...)` accepts the local name as well as the English one.
- The demo (`python -m faker_jobs`) says which data the generic methods use and labels the `source="kaggle"` posting.

---

## [0.3.0] - 2026-11-06

### Added
- Local posting conditions for German, Spanish, Italian and US postings (`de_*`, `es_*`, `it_*`, `en_US`), as for the French ones: contract types, diplomas, benefits, job boards, a city of the country, the experience and salary in the local wording and currency (`scripts/posting_conditions.py`). Other locales keep the Kaggle conditions.
- Salaries that follow the occupation: mean gross annual earnings of its ISCO-08 major group (Eurostat SES 2022 by NACE section for France, Germany, Spain and Italy; BLS OEWS for the United States), adjusted to the experience asked (earnings by age), to the contract (internship, apprenticeship, part-time) and kept above the minimum wage. `scripts/fetch_salaries.py` caches the earnings in `DATAS/salaries/`.
- `OccupationRecord.isco_code` / `isco_group`; `seniority` ('junior', 'mid', 'senior') in `OccupationPosting` and `JobPosting`.
- Contracts that follow the occupation (France, Germany, Spain, Italy): the national contract mix of the postings is adapted to the occupation's ISCO-08 major group with the Eurostat Labour Force Survey 2025 (shares of temporary employees, part-time and self-employed workers relative to the national share, capped at x3; the permanent contract takes the rest, at least 10%). `scripts/fetch_salaries.py` also caches those figures (`DATAS/salaries/eurostat_lfs.json`).
- French postings: "CDD saisonnier" contracts, offered with the occupation's share of seasonal recruitment projects in the BMO 2026 survey, exposed in every locale as `OccupationRecord.seasonal` (a lower bound: areas masked in the open data count as 0).

### Changed
- The experience asked and the default diploma of the occupation postings follow the ISCO skill level of the occupation instead of the executive status; French salaries come from Eurostat earnings instead of hand-made ranges.
- French interns and apprentices get 0 years of experience asked and a reduced salary.
- French postings are now about 40% CDI, 30% CDD saisonnier (as in the BMO hiring plans), 14% CDD and 8% Intérim, instead of 55% CDI and no seasonal contract.

---

## [0.2.0] - 2026-11-06

### Added
- Locale-aware occupations, beyond the office jobs of the Kaggle data (trades, industry, logistics, healthcare, hospitality, public service...):
  - French locales (`fr_FR`, `fr_CA`...): the 1,923 job sheets of the ROME 4.0 directory (France Travail, v62), with ~14,000 job titles, 35 activity sectors, know-how, knowledge and soft skills, in French.
  - Other locales: the 2,045 ESCO 1.0.9 occupations mapped to those sheets by the official ROME → ESCO crosswalk, with their English labels, description, skills and knowledge; sectors, domains and soft skills come from the linked ROME sheets.
  - New methods: `job_activity_sector`, `job_occupation`, `job_occupation_title`, `job_occupation_record` (by `code`, filter by `sector`), `job_occupation_skills`; properties `job_activity_sectors` and `job_occupation_codes`; `OccupationRecord` TypedDict; `JobsProvider.occupations_locale` to force a language.
  - `job_occupation_posting()` (`OccupationPosting` TypedDict): a full posting whose job title, skills and hiring company fit the occupation's sector. The 888 companies are matched to the 35 ROME sectors by rules on their sector label; when no company fits, the company name comes from the Faker locale.
  - French postings (`job_occupation_posting()` in French locales): job title as "masculine form (H/F)", diploma from the ROME sheet, contract type (CDI, CDD, intérim...), yearly gross salary in EUR by executive status, French benefits and job boards, a place in France. These conditions are hand-made and illustrative.
  - ROME attributes on every occupation: `qualifications` (French diplomas, moved out of `knowledge`), `executive`, `regulated`, `riasec`, `transitions`.
  - `job_occupation_title(gender="M"|"F")`: the masculine or feminine form of a French job title.
  - French benefits fit the job and contract: remote work and flexible hours for office or executive jobs, company car for executives, no bonus or profit-sharing for interns, no employee benefit for freelancers.
  - `job_occupation_posting()` picks the company in the occupation's own sector only (no longer in its secondary sectors, which gave odd matches); otherwise the company name comes from the Faker locale.
  - German, Spanish and Italian occupations (`de_*`, `es_*`, `it_*` locales): the same ESCO occupations with their labels, description, skills and knowledge in the language, ROME sectors, domains and soft skills translated by hand (`scripts/rome_labels.py`); `job_occupation_title(gender=...)` splits their "Busfahrer/Busfahrerin" titles, and postings read "Busfahrer (m/w/d)" (German) or "(m/f)" (Italian). Other conditions stay the Kaggle ones, in English.
  - Occupations are picked by demand (`weighted=True` by default in every `job_occupation*` method): estimated yearly recruitment projects in France, from the BMO 2026 survey (France Travail) and the DARES FAP 2021 → ROME table, exposed as `OccupationRecord.demand`. An estimate: ROME 4.0 sheets missing from the DARES table get the mean of their ROME group.
  - French postings: the company is made up by the Faker locale, with a NAF rév. 2 activity (INSEE) of the occupation's sector (`OccupationPosting.company_naf`, label in `company.industry`), instead of a Kaggle company. `xlrd` added to the `dev` extra.
  - `scripts/fetch_esco.py` (ESCO API → cache) and `scripts/build_occupations.py` (→ `faker_jobs/data/occupations_{de_DE,en_US,es_ES,fr_FR,it_IT}.json.gz`, gzipped JSON); `openpyxl` added to the `dev` extra.
- Multiple cities per country in location data: 216 → 457 locations total, covering major cities worldwide (e.g., France now has Paris, Marseille, Lyon, Toulouse, Nice, etc.; USA has 20 major cities).
- Improved error messages with fuzzy matching: when a user mistypes a parameter value (sector, company, job title, role, qualification, or country), the error message now suggests the closest matches.
- New read-only properties: `job_companies` (list of all company names) and `job_roles` (list of all role names).
- New helper scripts: `scripts/build_report.py` and `scripts/build_sample.py`.

### Changed
- **Breaking:** `job_posting()` is built on a ROME / ESCO occupation by default (`source="occupations"`): every trade, in the language of the Faker locale, picked by demand, with French conditions in French locales. The same keys as before, plus `source` and `occupation` (the `OccupationRecord`, None for Kaggle postings). `source="kaggle"` gives the previous postings; `job_title` and `role` require it, and `code` / activity `sector` select the occupation otherwise.
- `faker_locations.csv` enriched with multiple cities per country instead of just capitals.
- Error handling in `_pick_company`, `_resolve_title`, `_find_role`, `job_qualification_name`, and `job_location` now provides helpful suggestions for common typos.
- Tests updated to handle multiple locations per country.

---

## [0.1.0] - 2026-11-04

### Added
- `JobsProvider`, a Faker provider built from the Job Description Dataset (Kaggle, ~1.6M postings): 147 job titles, 376 roles, 888 companies, 216 locations, 25 benefits.
- Job titles and roles (`job_title`, `job_role`, `job_role_record`, `job_description`, `job_skills`, `job_responsibilities`), picked in proportion to their number of postings (`weighted=False` for a uniform pick).
- Requirements and conditions: `job_qualification`, `job_qualification_name`, `job_experience`, `job_experience_range`, `job_salary_range`, `job_salary_bounds`, `job_work_type`, `job_benefits`, `job_portal`.
- Companies and locations: `job_company`, `job_company_profile` (filter by sector), `job_company_size`, `job_location` (filter by country).
- Full postings: `job_id`, `job_posting_date`, `job_posting`, with a localized contact person and phone number.
- `TypedDict`s for the returned dicts (`RoleRecord`, `LocationRecord`, `CompanyProfile`, `JobPosting`) and `py.typed`.
- `scripts/build_job_stats.py` (role popularity, benefits, numeric ranges from the full postings file) and `scripts/build_data.py` (packaged JSON).
- Demo (`python -m faker_jobs`) and 33 tests.
- GitHub Actions CI: ruff + mypy, tests on Python 3.11 to 3.14 and with the oldest supported Faker (20.0.0), build with a check that the wheel ships `jobs_data.json`.

### Notes
- The source data files (`DATAS/`: CSV files, raw archive, geocoding cache) are not published in the repository; the package only needs the generated `faker_jobs/data/jobs_data.json`. `tests/test_build_data.py` is skipped when `DATAS/` is absent (27 tests run in CI, 33 locally).
