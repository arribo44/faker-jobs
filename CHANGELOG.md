# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- `job_dataset(postings=1000, companies=None, start_date="-2y", end_date="today", repost_rate=0.08)`: a dataset of employers and the postings they publish over a period, as two flat tables linked by `company_id` (`JobDataset.companies`, `.postings`; rows typed `CompanyRow`, `PostingRow`), with `to_csv()`, `to_jsonl()` and `to_dataframes()` (pandas). A stable pool of employers (real or made up, by size class from the official shares of jobs, spread between the sectors by demand) keeps its name, city, size and activity in all its postings; postings pick an employer of the occupation's sector, favouring the activities that employ it. Lifecycle: publication date in the period (seasonal contracts from March to September), closing date (log-normal, median 30 days), status `open` / `filled` / `expired` on `end_date`, and republications on another job board (`repost_of`). New module `faker_jobs/dataset.py`.
- `make_dataset(locales, ...)`: a dataset of one locale or of several with their share of the postings ({"fr_FR": 0.6, "de_DE": 0.4}), company ids prefixed by the locale, `seed` for a reproducible output.
- `python -m faker_jobs export DIR [--locale fr_FR[:SHARE]]... [--postings N] [--companies N] [--start-date] [--end-date] [--repost-rate] [--format csv|jsonl] [--seed]`; `python -m faker_jobs` alone still prints the demo.

### Changed
- `python -m faker_jobs` prints the demo in English (`en_US`) only, instead of English, French then German (the terminal showed only the German one); `--locale fr_FR` (repeatable) picks other locales.

### Added
- Portuguese, Dutch and Polish occupations: the 2,045 ESCO occupations mapped to ROME in those languages (`occupations_pt_PT.json.gz`, `occupations_nl_NL.json.gz`, `occupations_pl_PL.json.gz`), with the 35 activity sectors, 14 domains and 16 soft skills translated by hand (`scripts/rome_labels.py`), NACE Rev. 2 activities (labels from EU Vocabularies, weighted by the employment of Portugal, the Netherlands and Poland) and the full text of the postings in the three languages (`job_posting_text()`). Every locale of these languages uses them: `pt_PT`, `pt_BR`, `nl_NL`, `nl_BE`, `pl_PL`, instead of the English occupations.
- Posting conditions of Portugal (`pt_PT`: Contrato sem termo, Subsídio de alimentação, Net-Empregos...), the Netherlands (`nl_NL`: Vast contract, 13e maand, Nationale Vacaturebank..., "(m/v/x)"), Poland (`pl_PL`: Umowa o pracę, Kontrakt B2B, PPK, Pracuj.pl..., "(k/m)", PLN), with their Eurostat SES 2022 earnings and LFS contract mix; of Brazil (`pt_BR`: CLT, PJ, Vale-refeição, Catho, Gupy..., BRL from the ILOSTAT earnings of Brazil) and Dutch-speaking Belgium (`nl_BE`: Studentenjob, Maaltijdcheques, VDAB..., the Belgian earnings). Local city names in these countries ('Lisboa', 'Den Haag', 'Warszawa', 'Antwerpen'), real companies of Portugal, the Netherlands, Poland and Brazil (People Data Labs), with the Eurostat size shares of the first three.
- Neutral conditions in Portuguese, Dutch and Polish for the other countries (`pt_PT` with `country="Angola"`: AOA salaries).
- Country names in the language of the occupations: a French posting in Algeria reads "Algérie", an Italian one in Germany "Germania", a Polish one "Niemcy" (Wikidata labels, CC0, of the item with the ISO code; the Netherlands and China by their usual item). `job_location(country=...)`, `job_posting(country=...)` also take these names ("Allemagne", "Pays-Bas"). Kept in `cities.json.gz` (`names` of each country, where they differ from the English one); cached in `DATAS/wikidata/country_names.json` (`build_cities.py --fetch-country-names`). Cities keep their English name outside the countries of the locale's language.
- Jobs in the regions of the language in the countries of several: `fr_CA` in Quebec and New Brunswick, `fr_BE` in Wallonia and Brussels, `nl_BE` in Flanders and Brussels, `fr_CH` in the French-speaking cantons (with Fribourg and Valais), `de_CH` in the German-speaking ones, `it_CH` in Ticino (`regions` of `COUNTRY_CONDITIONS`, GeoNames admin1 codes; `cities.json.gz` gives the region of each city of Belgium, Switzerland and Canada). Companies of up to 500 employees hire in their headquarters only when it is in these regions.
- `fetch_esco.py` takes `pt`, `nl` and `pl`; `fetch_activities.py` fetches the NACE labels in them; a country locale's earnings can be those of countries.json (`{"economy": country}`, Brazil).

### Changed
- **Breaking**: the `pt_*`, `nl_*` and `pl_*` locales return their occupations, sectors and conditions in their language (they were in English since 0.11.0, with neutral conditions).
- The age ratios of the US salaries stay the mean of France, Germany, Spain and Italy (`AGE_RATIO_COUNTRIES`).

---

## [0.11.0] - 2026-11-13

### Added
- Postings in every country: 232 of the 244 countries of `job_countries` have an economy in the new `faker_jobs/data/countries.json` (~200 KB): currency (ISO code, GeoNames; EUR for Bulgaria), mean yearly earnings by ISCO-08 major group and minimum wage. Sources, best first: the conditions of the country's locales; Eurostat SES 2022 for the 25 other European countries it covers (Portugal, Poland, the Netherlands, Sweden...); ILOSTAT average monthly earnings of employees by ISCO major group (~100 countries: India, Brazil, Argentina, South Africa...), latest year, brought to 2025 with the World Bank GDP per capita in local currency (series in median, net, real or daily terms left out; structures where professionals earn less than elementary occupations replaced by the median one); else the GDP per capita times the median ratio of earnings to it, with the median structure (Japan, China, Algeria...: ~70). Micro-states and territories take the economy of their neighbour or country (Liechtenstein: Switzerland, Monaco: France, Réunion: France, Jersey: United Kingdom...); Taiwan has hand-entered figures (DGBAS). Minimum wages: ILOSTAT, brought to the same year. `fetch_salaries.py` caches `DATAS/salaries/ilostat.json` and `worldbank_gdp.json`, and the SES earnings of every country it covers.
- Neutral posting conditions in each language (`GENERIC_CONDITIONS` in `scripts/posting_conditions.py`): contracts, benefits and diplomas found in most countries, international job boards (LinkedIn, Indeed, Glassdoor, Jooble, Careerjet), the currency code in the salary ("JPY 3,100,000 - 4,250,000 a year", "620 000 - 820 000 DZD brut/an").

### Changed
- **Breaking**: the locales of countries without conditions of their own post in their country, with its currency and salaries, in the language of the occupations: `ja_JP` in Japan in JPY, `en_IN` in India in INR, `pt_BR` in Brazil, `nl_NL` in the Netherlands (in English); `es_AR` in Argentina and `fr_DZ` in Algeria, in Spanish and French. They used the conditions and the country of the United States (or Spain, France). `es_CA` (Faker's Spanish of Catalonia) stays in Spain; `en` keeps the United States.
- **Breaking**: `country=` of `job_posting()`, `job_occupation_posting()` and `job_location()` sets the conditions too: those of a locale of the language in that country (`fr_FR` with `country="Belgium"`: the Belgian ones, "Belgique"), else neutral ones with the country's economy (`fr_FR` with `country="Brazil"`: BRL salaries, not EUR). The locale's conditions are kept with `occupations_locale` set and in countries without figures.
- Countries without real companies take the company size shares of the country of the language (no more error for a locale's country without companies).
- Locales without phone numbers in Faker (`en_PH`, `fil_PH`, `tl_PH`) get a generic one as contact instead of an error.

### Fixed
- `job_location(country="Palau")` raised an error: its only city has a population of 0 (now a uniform pick).
- Tests: locales missing from older Faker versions (`de_LU`, `fr_DZ` before Faker 21) are skipped (the CI with Faker 20 failed since 0.10.0; the library itself was not affected).

---

## [0.10.0] - 2026-11-13

### Added
- Posting conditions of their own for 15 country locales, over those of their language: `fr_BE`, `fr_CH`, `fr_CA` (and `fr_QC`), `de_AT`, `de_CH`, `de_LU`, `it_CH`, `es_MX`, `es_CL`, `es_CO`, `en_GB`, `en_IE`, `en_CA`, `en_AU`, `en_NZ`. Each has its currency (CHF, CAD, MXN, CLP, COP, GBP, AUD, NZD...), contracts (Job étudiant, Lehre, Honorarios, Casual...), default diplomas (CESS, CFC, DEC, EFZ, GCSEs, NCEA...), benefits, job boards (Le Forem, jobs.ch, Jobboom, karriere.at, OCC Mundial, SEEK...), salary wording and gender mark of the titles ("(H/F/X)" in Belgium, none in Canada). Jobs are located in the country by default, with the local names of its cities ('Anvers', 'Genf', 'Ginevra', 'Montréal', 'Wien'), and hired by real companies of the country. Hand-made and illustrative, as the other conditions (`scripts/posting_conditions.py`, `COUNTRY_CONDITIONS`); `conditions.json` holds for these locales only what differs from their language's (`base`).
- Salaries of these countries: Eurostat SES 2022 earnings and LFS contract mix of Belgium, Switzerland (in CHF), Austria, Luxembourg and Ireland, as for the base countries; for Canada, Mexico, Chile, Colombia, the United Kingdom, Australia and New Zealand, which have no such survey, the earnings of the country of their language (France, Spain, United States) times the ratio of the OECD average annual wages of the two countries in national currency, the same year. Minimum wage: the OECD statutory one (none in Austria and Switzerland). Amounts are rounded to 500 / 1,000 units, 10 times more in MXN, 1,000 times in CLP and COP. `fetch_salaries.py` also caches `DATAS/salaries/oecd_wages.json`.
- Real hiring companies of Belgium, Switzerland, Austria, Luxembourg, Ireland, Canada, Mexico, Chile, Colombia, Australia and New Zealand (People Data Labs, ~23,000 companies in all, `companies.json.gz` ~540 KB), with official size shares where they exist: Eurostat SBS for the five European countries, OECD SDBS for Canada (1-9, 10-49, 50-249, 250+) and New Zealand (1-9, 10+). Mexico, Chile, Colombia and Australia keep the LinkedIn shares, which list few small companies (4-8% of the postings in companies of up to 10 employees).

### Changed
- **Breaking**: `en_GB` has British conditions (GBP, Permanent / Fixed-term contract / Apprenticeship..., Reed, Totaljobs...) instead of those of the United States. Locales without conditions of their own keep those of their language's country (`es_AR`: Spain) or of the United States (`en_IN`, `nl_NL`, `ja_JP`...).
- Belgian, Swiss and Canadian postings ask for local diplomas instead of the French ones listed by ROME sheets, and their companies get the NACE class of their NAF activity (`company_naf` '86.10' instead of '86.10Z').
- `cities.json.gz`: the local names of a city are a {language: name} dict, only where they differ from the English name, for the countries of the locales (Switzerland in French, German and Italian; Belgium, Luxembourg and Canada prefer the name in the language: 'Anvers', not 'Antwerpen'). `build_cities.py --download` only fetches the missing files.
- `build_companies.py`: each country draws its companies with its own random generator, so that adding a country leaves the others unchanged; rows whose LinkedIn locality is in another country are left out (Luxoft in Moscow for Switzerland). The sample of the six former countries is drawn anew once (same size shares). Wikidata queries are retried, then split, when the service times out, and the cache is saved after each batch.
- `build_occupations.py`: an ISCO group missing from a country's Labour Force Survey (armed forces in Luxembourg) keeps the national contract mix.

---

## [0.9.0] - 2026-11-12

### Changed
- French mining (B) and water supply, sewerage and waste (E), whose employment by enterprise size is confidential, take the size split of the European Union (Eurostat SBS, EU27_2020), brought to the French employment of the section, instead of the LinkedIn shares: the "Environnement" sector hires in companies of up to 200 employees in 45% of the postings instead of 13%.
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
