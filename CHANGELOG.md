# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Locale-aware occupations, beyond the office jobs of the Kaggle data (trades, industry, logistics, healthcare, hospitality, public service...):
  - French locales (`fr_FR`, `fr_CA`...): the 1,923 job sheets of the ROME 4.0 directory (France Travail, v62), with ~14,000 job titles, 35 activity sectors, know-how, knowledge and soft skills, in French.
  - Other locales: the 2,045 ESCO 1.0.9 occupations mapped to those sheets by the official ROME → ESCO crosswalk, with their English labels, description, skills and knowledge; sectors, domains and soft skills come from the linked ROME sheets.
  - New methods: `job_activity_sector`, `job_occupation`, `job_occupation_title`, `job_occupation_record` (by `code`, filter by `sector`), `job_occupation_skills`; properties `job_activity_sectors` and `job_occupation_codes`; `OccupationRecord` TypedDict; `JobsProvider.occupations_locale` to force a language.
  - `job_occupation_posting()` (`OccupationPosting` TypedDict): a full posting whose job title, skills and hiring company fit the occupation's sector. The 888 companies are matched to the 35 ROME sectors by rules on their sector label; when no company fits, the company name comes from the Faker locale.
  - `scripts/fetch_esco.py` (ESCO API → cache) and `scripts/build_occupations.py` (→ `faker_jobs/data/occupations_{en_US,fr_FR}.json`); `openpyxl` added to the `dev` extra.
- Multiple cities per country in location data: 216 → 457 locations total, covering major cities worldwide (e.g., France now has Paris, Marseille, Lyon, Toulouse, Nice, etc.; USA has 20 major cities).
- Improved error messages with fuzzy matching: when a user mistypes a parameter value (sector, company, job title, role, qualification, or country), the error message now suggests the closest matches.
- New read-only properties: `job_companies` (list of all company names) and `job_roles` (list of all role names).
- New helper scripts: `scripts/build_report.py` and `scripts/build_sample.py`.

### Changed
- `faker_locations.csv` enriched with multiple cities per country instead of just capitals.
- Error handling in `_pick_company`, `_resolve_title`, `_find_role`, `job_qualification_name`, and `job_location` now provides helpful suggestions for common typos.
- Tests updated to handle multiple locations per country.

---

## [0.1.0] - 2026-11-04

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
