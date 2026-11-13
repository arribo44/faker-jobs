"""
Faker Jobs Provider

A custom Faker provider for simulating job postings: job titles and
occupations (with their description, skills and responsibilities),
qualifications, experience and salary ranges, contract types, benefits, job
boards, hiring companies with their profile, locations, contacts and full
job postings.

Jobs come from occupation directories, in the locale's language: the 1,923
job sheets of the French ROME 4.0 directory (France Travail) for French
locales, and the ~2,000 ESCO occupations mapped to them (European
Commission), in German, Spanish or Italian for those locales and in English
for every other one. Each occupation comes with its job titles, activity
sectors, skills, knowledge and soft skills. The posting conditions
(contracts, diplomas, salaries from official earnings, benefits, job boards)
are those of the locale's country: France, Germany, Spain, Italy, the
United States, and Belgium, Switzerland, Canada, Austria, Luxembourg,
Mexico, Chile, Colombia, the United Kingdom, Ireland, Australia, New
Zealand for their locales (fr_BE, de_CH, es_MX, en_GB...); in every other
country (232 in all), neutral conditions in the language with the
country's currency and salaries (ILOSTAT, World Bank): ja_JP posts in
Japan in JPY, and `country=` takes the conditions of the country of the job.

Job locations are the ~29,700 cities of 15,000 inhabitants or more of
GeoNames in 244 countries, picked in proportion to their population, with
their local names in the countries of the locales. Hiring companies come
from the People Data Labs company dataset (LinkedIn pages, CC BY 4.0): real
companies of these 17 countries, by activity sector and size class, picked by the
share of jobs of each size class; the smallest ones (1 to 10 employees) are
made up by the Faker locale. Contact names and phone numbers always come
from the Faker locale.
"""
import difflib
import gzip
import datetime as _datetime
import itertools
import json
import math
import os
import string
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypedDict, overload

from faker.providers import BaseProvider

from faker_jobs.candidates import CandidateRecord as CandidateRecord
from faker_jobs.candidates import make_candidate

if TYPE_CHECKING:
    from faker_jobs.dataset import JobDataset

__version__ = "0.12.0"

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_CITIES_PATH = os.path.join(_DATA_DIR, "cities.json.gz")
_cities_cache: dict[str, Any] | None = None
_country_aliases: dict[str, str] = {}

# Locales with their own occupation data, and the one used for every other locale.
OCCUPATION_LOCALES = ("ar_SA", "cs_CZ", "de_DE", "el_GR", "en_US", "es_ES", "fr_FR", "it_IT", "nl_NL", "pl_PL", "pt_PT",
                      "ro_RO", "sv_SE")
DEFAULT_OCCUPATION_LOCALE = "en_US"
_occupation_cache: dict[str, dict[str, Any]] = {}
# Posting conditions of every occupation locale (contracts, diplomas, salaries...).
_CONDITIONS_PATH = os.path.join(_DATA_DIR, "conditions.json")
_conditions_cache: dict[str, Any] | None = None
# Hiring companies (People Data Labs) by country, activity sector and size class.
_COMPANIES_PATH = os.path.join(_DATA_DIR, "companies.json.gz")
_companies_cache: dict[str, Any] | None = None
# Faker locales that stand for another one with posting conditions (fr_QC is
# Faker's former name of fr_CA, es_CA its Spanish of Catalonia).
_LOCALE_ALIASES = {"fr_QC": "fr_CA", "es_CA": "es_ES"}
_country_conditions_cache: dict[str, dict[str, Any]] = {}
# Economy of every country (currency, salaries, minimum wage) and neutral
# conditions of each language, for the countries without conditions of their own.
_COUNTRIES_PATH = os.path.join(_DATA_DIR, "countries.json")
_countries_cache: dict[str, Any] | None = None
_generic_conditions_cache: dict[tuple[str, str], dict[str, Any]] = {}
# Companies up to this size class (201-500 employees) hire in their headquarters city.
_SINGLE_SITE_MAX_CLASS = 3
# Companies sampled per sector and size class: in a class of fewer companies,
# some are made up, so that no company gets more than 1/10 of its class.
_COMPANIES_PER_CLASS = 10


def _suggest_similar(value: str, options: list[str], n: int = 3) -> list[str]:
    """Suggest similar values using fuzzy matching."""
    return difflib.get_close_matches(
        value.lower(),
        [o.lower() for o in options],
        n=n,
        cutoff=0.6
    )


class RoleRecord(TypedDict):
    """An occupation in a flat shape, as returned by `JobsProvider.job_role_record()`:
    `role` is the occupation's name, `job_title` one of its titles."""

    job_title: str
    role: str
    description: str
    skills: str
    responsibilities: str


class LocationRecord(TypedDict):
    """A job location, as returned by `JobsProvider.job_location()`."""

    city: str
    country: str
    latitude: float
    longitude: float


class CompanyProfile(TypedDict):
    """A hiring company, as returned by `JobsProvider.job_company_profile()`.

    Fields missing from the source data are None: no state outside the US,
    no zip or ticker, no CEO for People Data Labs companies (a made-up CEO
    for made-up companies), no founding year for made-up companies."""

    company: str
    sector: str | None
    industry: str | None
    city: str | None
    state: str | None
    zip: str | None
    website: str | None
    ticker: str | None
    ceo: str | None
    founded: int | None


class OccupationRecord(TypedDict):
    """An occupation, as returned by `JobsProvider.job_occupation_record()`.

    In French locales it is a ROME 4.0 job sheet (`code` like 'M1805'), in
    the others an ESCO occupation (`code` is its ESCO concept id, the same
    in English, German, Spanish and Italian).
    `job_title` is one of its job titles, picked at random; `sector` is the
    requested sector, or else its main one. `description` is None for ROME
    sheets (the source has none).

    From ROME (for an ESCO occupation, from the ROME sheet holding most of
    its job titles): `executive` (a "cadre" job), `regulated` (a regulated
    profession), `riasec` (Holland codes, major first, e.g. ['R', 'C']) and
    `transitions` (any of 'ecological', 'digital', 'demographic': jobs
    ROME flags as part of that transition). `qualifications` are the French
    diplomas listed by the ROME sheet (CAP, Bac pro, BTS, Master...); empty
    for ESCO occupations.

    `isco_code` is the ISCO-08 unit group of the occupation (e.g. '2221',
    from ESCO; for a ROME sheet, that of most of its ESCO occupations, None
    when it has none) and `isco_group` its major group ('1' managers to
    '9' elementary occupations, '0' armed forces), which sets the skill
    level and the salary of the postings.

    `demand` estimates the yearly recruitment projects in France (France
    Travail's BMO 2026 survey, by job family, shared between the ROME sheets
    of the family by the DARES FAP 2021 → ROME table; ROME 4.0 sheets
    missing from that table get the mean of their ROME group). French
    figures in every locale: a rough popularity weight, not a statistic.
    `seasonal` is the share of those projects that are seasonal (0 to 1,
    same source; areas the open data masks count as 0, so it is a lower
    bound). It sets the share of "CDD saisonnier" postings in French locales."""

    code: str
    title: str
    job_title: str
    domain: str
    sector: str
    sectors: list[str]
    description: str | None
    skills: list[str]
    knowledge: list[str]
    soft_skills: list[str]
    qualifications: list[str]
    executive: bool
    regulated: bool
    riasec: list[str]
    transitions: list[str]
    isco_code: str | None
    isco_group: str
    demand: int
    seasonal: float


class OccupationPosting(TypedDict):
    """A job posting built on an occupation, as returned by
    `JobsProvider.job_occupation_posting()`.

    `job_title`, `skills` and the company follow the occupation and its
    sector. The conditions are local: contract type in `work_type` (CDI,
    Unbefristet, Indefinido, Tempo indeterminato, Full-time...), a yearly
    gross salary in the local currency from official earnings (see
    `job_occupation_posting`), local diplomas, a place in the country, local
    job boards and benefits: those of the country of the job (see
    `JobsProvider.job_occupation_posting`), neutral ones in the language
    with the country's currency and salaries where it has no conditions of
    its own in that language (Japan, India...). The job title reads
    "Conducteur de poids lourd (H/F)" in French ("(H/F/X)" in Belgium, both
    forms in Canada), "Busfahrer (m/w/d)" in German, "autista di autobus
    (m/f)" in Italian (Spanish keeps both forms).
    `seniority` is 'junior', 'mid' or 'senior', from the experience asked.
    `remote` is 'on_site', 'hybrid' or 'remote' (full remote work), see
    `job_occupation_posting`.

    The company is in the occupation's sector (`company_sector`) and in the
    country of the job (see `job_occupation_posting`); `company_size` is its
    number of employees. `company_naf` is the activity code of the company,
    in the sector and among those that employ the occupation: a NAF rév. 2
    sub-class in France (e.g. '86.10Z'), a NACE Rev. 2 class in the other
    countries of the locales but English ones (e.g. '86.10', also the class
    of WZ 2008, CNAE-2009 and ATECO 2007), whose label is the company's
    `industry`; it is None in English locales."""

    job_id: int | str
    job_title: str
    occupation: OccupationRecord
    skills: list[str]
    qualification: str
    experience: str
    experience_min: int
    experience_max: int
    salary_range: str
    salary_min: int
    salary_max: int
    salary_currency: str
    work_type: str
    benefits: list[str]
    location: LocationRecord
    company: CompanyProfile
    company_sector: str | None
    company_naf: str | None
    company_size: int
    seniority: str
    job_portal: str
    job_posting_date: _datetime.date
    contact_person: str
    contact: str
    remote: str


class JobPosting(TypedDict):
    """A full job posting, as returned by `JobsProvider.job_posting()`.

    It is `job_occupation_posting()` in the shape of `job_role_record()`:
    a ROME / ESCO occupation (whose record is in `occupation`), in the
    language of the Faker locale. `role` is the occupation's name,
    `responsibilities` its skills (activities), `skills` its knowledge and
    soft skills, `description` its ESCO description (or, for ROME sheets,
    which have none, its main activities). Salaries are yearly amounts in
    `salary_currency`; `salary_range` is their text in the local wording.

    `seniority` is 'junior' (under 3 years of experience asked), 'mid' (3 to
    7) or 'senior' (8 and more). `remote` is 'on_site', 'hybrid' or 'remote'."""

    occupation: OccupationRecord
    job_id: int | str
    job_title: str
    role: str
    description: str
    skills: str
    responsibilities: str
    qualification: str
    experience: str
    experience_min: int
    experience_max: int
    salary_range: str
    salary_min: int
    salary_max: int
    salary_currency: str
    work_type: str
    benefits: list[str]
    location: LocationRecord
    company: CompanyProfile
    company_size: int
    seniority: str
    job_portal: str
    job_posting_date: _datetime.date
    contact_person: str
    contact: str
    remote: str


def _load_cities() -> dict[str, Any]:
    """{lowercase country: {"country": name, "cities": rows, "cum_weights":
    cumulative populations, or None for a uniform pick}}; a row is [English
    name, latitude, longitude, population] and, in the countries of the
    locales with conditions of their own, {language: local name} where it
    differs from the English name ({'de': 'München'})."""
    global _cities_cache
    if _cities_cache is None:
        with gzip.open(_CITIES_PATH, "rt", encoding="utf-8") as f:
            raw = json.load(f)
        _cities_cache = {
            country.lower(): {
                "country": country,
                "code": entry["code"],
                # {language: name} in the languages of the occupations ('Allemagne'), where not the English one.
                "names": entry.get("names", {}),
                # GeoNames admin1 code of each city (Belgium, Switzerland, Canada), else None.
                "regions": entry.get("regions"),
                "cities": entry["cities"],
                # Uniform without populations (or with none but 0: Palau).
                "cum_weights": None if any(row[3] is None for row in entry["cities"])
                or not any(row[3] for row in entry["cities"])
                else list(itertools.accumulate(row[3] for row in entry["cities"])),
            }
            for country, entry in raw["countries"].items()
        }
        # ISO codes ('US', 'FR') and the short names of version 0.6 ('USA', 'UK', 'UAE').
        _country_aliases.update({entry["code"].lower(): country.lower() for country, entry in raw["countries"].items()})
        _country_aliases.update({"usa": "united states", "uk": "united kingdom", "uae": "united arab emirates"})
        # Names in the languages of the occupations ('Allemagne', 'Niemcy'); a name of two
        # countries ('Saint-Martin' in French) stays that of the first.
        for country, entry in raw["countries"].items():
            for name in entry.get("names", {}).values():
                if name.lower() not in _cities_cache:
                    _country_aliases.setdefault(name.lower(), country.lower())
    return _cities_cache


_regional_cache: dict[tuple[str, tuple[str, ...]], tuple[list[Any], list[int] | None]] = {}


def _regional_cities(entry: dict[str, Any], regions: tuple[str, ...]) -> tuple[list[Any], list[int] | None]:
    """(cities, cumulative populations or None) of a country in `regions` (GeoNames admin1 codes)."""
    key = (entry["country"], regions)
    if key not in _regional_cache:
        rows = [row for row, region in zip(entry["cities"], entry["regions"], strict=True) if region in regions]
        weights = None if any(row[3] is None for row in rows) or not any(row[3] for row in rows) \
            else list(itertools.accumulate(row[3] for row in rows))
        _regional_cache[key] = (rows, weights)
    return _regional_cache[key]


def _in_regions(country: str, city: Any, regions: list[str] | None) -> bool:
    """Whether a company's headquarters (an index into the country's cities) is in
    `regions`: always without regions; never for a city that is not an index."""
    if not regions:
        return True
    entry = _load_cities()[country.lower()]
    return isinstance(city, int) and entry["regions"] is not None and entry["regions"][city] in regions


def _country_code(country: str | None) -> str:
    """The ISO 3166-1 alpha-2 code of a country (any name `job_location` takes), '' when unknown."""
    entry = _country_entry(country) if country else None
    return str(entry["code"]) if entry is not None else ""


JOB_ID_FIELDS = ("year", "month", "day", "date", "country", "locale", "n")
_JOB_ID_CHARACTERS = {"#": string.digits, "?": string.ascii_uppercase, "*": string.ascii_uppercase + string.digits}


def _format_job_id(
    random: Any, template: str, date: _datetime.date, country: str, locale: str, n: int | None,
) -> str:
    """A job id from `template` (see `JobsProvider.job_id`)."""
    if not isinstance(template, str) or not template:
        raise ValueError(f"template must be a non-empty string, got {template!r}")
    fields = {"year": date.year, "month": date.month, "day": date.day, "date": date,
              "country": country, "locale": locale, "n": n}
    try:
        names = {name for _, name, _, _ in string.Formatter().parse(template) if name is not None}
    except ValueError as error:
        raise ValueError(f"bad job id template {template!r}: {error}") from None
    unknown = names - set(fields)
    if unknown:
        raise ValueError(f"unknown field(s) {sorted(unknown)} in job id template {template!r}; "
                         f"known: {', '.join('{' + name + '}' for name in JOB_ID_FIELDS)}")
    if "n" in names and n is None:
        raise ValueError("{n} (the posting's number) is only known in job_dataset(), or with job_id(n=...)")
    try:
        text = template.format(**fields)
    except (ValueError, TypeError) as error:
        raise ValueError(f"bad job id template {template!r}: {error}") from None
    return "".join(random.choice(_JOB_ID_CHARACTERS[char]) if char in _JOB_ID_CHARACTERS else char
                   for char in text)


def _country_name(country: str, language: str) -> str:
    """The name of a country of `job_countries` in a language of the occupations
    ('Germany', 'fr' -> 'Allemagne'); the English one without."""
    entry = _country_entry(country)
    return str(entry["names"].get(language, entry["country"])) if entry is not None else country


def _country_entry(country: str) -> dict[str, Any] | None:
    """The cities of a country, by name, ISO code or alias (case-insensitive)."""
    cities = _load_cities()
    key = str(country).strip().lower()
    found: dict[str, Any] | None = cities.get(key) or cities.get(_country_aliases.get(key, ""))
    return found


def _load_conditions() -> dict[str, Any]:
    global _conditions_cache
    if _conditions_cache is None:
        with open(_CONDITIONS_PATH, encoding="utf-8") as f:
            _conditions_cache = json.load(f)
    return _conditions_cache


def _size_class(classes: list[list[int]], size: int) -> int:
    """Index of the size class of `size` employees (the last class has no upper bound)."""
    return next(i for i, (_, high) in enumerate(classes) if size <= high or i == len(classes) - 1)


def _load_companies() -> dict[str, Any]:
    """{"classes": [low, high] employees of each size class, "industries":
    LinkedIn industries, "countries": {country: {"cum_weights": {ROME sector
    code: cumulative job shares of the size classes}, "cum_weights_all": the
    same for every sector, "counts": {ROME sector code: number of companies
    of each size class in the dataset}, "by_class": {ROME sector code: company rows of
    each size class}}}}; a row is [name, website, founding year, city (index
    into the country's cities or name), state, employees, industry index]."""
    global _companies_cache
    if _companies_cache is None:
        with gzip.open(_COMPANIES_PATH, "rt", encoding="utf-8") as f:
            raw = json.load(f)
        classes = raw["meta"]["size_classes"]
        countries = {}
        for country, entry in raw["countries"].items():
            by_class: dict[str, list[list[list[Any]]]] = {}
            for code, rows in entry["companies"].items():
                grouped: list[list[list[Any]]] = [[] for _ in classes]
                for row in rows:
                    grouped[_size_class(classes, row[5])].append(row)
                by_class[code] = grouped
            countries[country] = {
                "cum_weights": {code: list(itertools.accumulate(w)) for code, w in entry["weights"].items()},
                "cum_weights_all": list(itertools.accumulate(entry["weights_all"])),
                "counts": entry["counts"],
                "by_class": by_class,
            }
        # {country: {lower-case name: (sector code, size class, row)}}, for job_company_profile(company=...).
        by_name: dict[str, dict[str, tuple[str, int, list[Any]]]] = {}
        for country, entry in countries.items():
            lookup = by_name.setdefault(country, {})
            for code, grouped in entry["by_class"].items():
                for size_class, rows in enumerate(grouped):
                    for row in rows:
                        lookup.setdefault(row[0].lower(), (code, size_class, row))
        _companies_cache = {"classes": classes, "industries": raw["industries"], "countries": countries,
                            "by_name": by_name}
    return _companies_cache


def _country_conditions(locale: str) -> dict[str, Any]:
    """The posting conditions of a country locale of conditions.json
    ('fr_BE', 'en_GB'...): its own keys over those of its occupation locale
    (`base`: the fields of study, activity sectors and activities...)."""
    if locale not in _country_conditions_cache:
        own = _load_conditions()[locale]
        _country_conditions_cache[locale] = {**_load_conditions()[own["base"]], **own}
    return _country_conditions_cache[locale]


def _conditions_locale(locale: str | None) -> str | None:
    """The country locale of conditions.json of a Faker locale ('fr_BE',
    'fr_QC' -> 'fr_CA'), None for the occupation locales and the locales
    without conditions of their own."""
    if not locale:
        return None
    key = locale.replace("-", "_")
    key = _LOCALE_ALIASES.get(key, key)
    entry = _load_conditions().get(key)
    return key if entry is not None and "base" in entry else None


def _load_countries() -> dict[str, Any]:
    global _countries_cache
    if _countries_cache is None:
        with open(_COUNTRIES_PATH, encoding="utf-8") as f:
            _countries_cache = json.load(f)
    return _countries_cache


# Remote work: the share of postings offering it is the country's share of
# employees working from home (Eurostat LFS, usually or sometimes) times a
# factor of the occupation's ISCO major group (hand-made, illustrative:
# about 2 for professionals and managers, under 0.2 for manual work; their
# mean over the EU employment is about 1); at most MAX_REMOTE_SHARE. Of
# those, FULL_REMOTE_SHARE times the share working from home "usually" are
# full remote, the others hybrid.
REMOTE_FACTORS = {"1": 2.0, "2": 2.2, "3": 1.5, "4": 1.35, "5": 0.2, "6": 0.1, "7": 0.13, "8": 0.1, "9": 0.1,
                  "0": 0.05}
MAX_REMOTE_SHARE = 0.9
FULL_REMOTE_SHARE = 0.5


def _labour(country: str) -> dict[str, Any]:
    """The telework shares [usually, sometimes] and yearly wage growth of a
    country (countries.json), the defaults (EU, median) where it has none."""
    data = _load_countries()
    economy = data["countries"].get(country, {})
    return {key: economy.get(key, data["meta"][key]) for key in ("telework", "wage_growth")}


def _locale_country(locale: str | None) -> str | None:
    """The country of a Faker locale's territory ('ja_JP' -> 'Japan'), None
    without one or for a territory without cities ('de_LI')."""
    if not locale:
        return None
    key = locale.replace("-", "_")
    key = _LOCALE_ALIASES.get(key, key)
    parts = key.split("_")
    if len(parts) < 2:
        return None
    entry = _country_entry(parts[1])
    return str(entry["country"]) if entry is not None else None


def _own_conditions(language: str, country: str) -> dict[str, Any] | None:
    """The conditions of a locale of `language` with conditions of its own in
    `country` ('fr' and 'Belgium' -> those of fr_BE), None without."""
    for locale, entry in _load_conditions().items():
        if locale.startswith(f"{language}_"):
            conditions = _country_conditions(locale) if "base" in entry else entry
            if conditions["country"] == country:
                return conditions
    return None


def _generic_conditions(base: dict[str, Any], language: str, country: str) -> dict[str, Any] | None:
    """Neutral conditions in `language` (countries.json) over those of its
    occupation locale (`base`), with the currency, salaries and minimum wage
    of `country`; None for a country without them."""
    key = (language, country)
    if key not in _generic_conditions_cache:
        data = _load_countries()
        economy, generic = data["countries"].get(country), data["generic"].get(language)
        if economy is None or generic is None:
            return None
        conditions = {key: value for key, value in base.items() if key not in ("place_names", "salary_scale")}
        conditions.update(generic)
        conditions.update({key: value for key, value in economy.items() if key != "salary"})
        conditions["salary"] = {"base": economy["salary"]["base"], "age_ratio": data["meta"]["age_ratio"]}
        conditions["country"] = country
        conditions["place_names"] = {"country": _country_name(country, language)}
        _generic_conditions_cache[key] = conditions
    return _generic_conditions_cache[key]


# Locales whose occupations are those of another one in their own spelling: {locale: (data, converter)}.
_OCCUPATION_VARIANTS = {"pt_BR": "pt_PT"}


def _load_occupations(locale: str, variant: str | None = None) -> dict[str, Any]:
    """The occupations of an occupation locale; with `variant` ('pt_BR'), in
    its spelling (Brazilian Portuguese from the European labels)."""
    key = variant or locale
    if key not in _occupation_cache:
        with gzip.open(os.path.join(_DATA_DIR, f"occupations_{locale}.json.gz"), "rt", encoding="utf-8") as f:
            raw = json.load(f)
        if variant == "pt_BR":
            from faker_jobs.pt_br import to_brazilian

            # Sector names stay: they are the keys of the conditions.
            sectors = set(raw["sectors"])
            raw["strings"] = [text if text in sectors else to_brazilian(text) for text in raw["strings"]]
            for record in raw["occupations"]:
                record["title"] = to_brazilian(record["title"])
                record["titles"] = list(dict.fromkeys(to_brazilian(title) for title in record["titles"]))
                record["description"] = to_brazilian(record["description"])
        raw["conditions"] = _load_conditions()[locale]
        _occupation_cache[key] = _build_occupation_index(raw)
    return _occupation_cache[key]


def _group_by_title(occupations: list[dict[str, Any]]) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    """{lowercase job title: (job title, occupations that have it)}."""
    grouped: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for occupation in occupations:
        for title in occupation["titles"]:
            grouped.setdefault(title.lower(), (title, []))[1].append(occupation)
    return grouped


def _build_occupation_index(raw: dict[str, Any]) -> dict[str, Any]:
    # Labels are stored once in `strings`; records refer to them by index.
    strings = raw["strings"]
    occupations = [
        {
            **record,
            "domain": strings[record["domain"]],
            **{field: [strings[i] for i in record[field]]
               for field in ("sectors", "skills", "knowledge", "soft_skills", "qualifications")},
        }
        for record in raw["occupations"]
    ]
    by_sector: dict[str, list[dict[str, Any]]] = {sector: [] for sector in raw["sectors"]}
    for occupation in occupations:
        for sector in occupation["sectors"]:
            by_sector[sector].append(occupation)

    def cum_weights(rows: list[dict[str, Any]]) -> list[int]:
        # Demand weight = estimated recruitment projects (BMO 2026).
        return list(itertools.accumulate(row["weight"] for row in rows))

    return {
        "meta": raw["meta"],
        "sectors": sorted(raw["sectors"]),
        "occupations": occupations,
        "occupation_by_code": {occupation["code"].lower(): occupation for occupation in occupations},
        # Localized generic methods: role = occupation name, job title = one of its titles.
        "occupation_by_title": {occupation["title"].lower(): occupation for occupation in occupations},
        "occupations_by_job_title": _group_by_title(occupations),
        "occupations_by_sector": by_sector,
        "cum_weights": cum_weights(occupations),
        "cum_weights_by_sector": {sector: cum_weights(rows) for sector, rows in by_sector.items()},
        "sector_by_name": {sector.lower(): sector for sector in raw["sectors"]},
        "conditions": raw["conditions"],
        # {ISCO unit group: {sector: [[index in conditions["naf_by_sector"][sector], weight], ...]}}:
        # the activities of the sector that employ the occupation (see `_pick_naf`).
        "naf_by_isco": raw.get("naf_by_isco", {}),
        # None (titles are not gendered) or {"titles": "rome" | "esco", "posting_suffix": str | None}.
        "gender": raw["meta"].get("gender"),
    }


def _gender_form(title: str, gender: str, style: str = "rome") -> str:
    """The masculine ('M') or feminine ('F') form of a French ROME job title
    written with both, e.g. "Conducteur / Conductrice d'engins agricoles"
    -> "Conducteur d'engins agricoles" / "Conductrice d'engins agricoles".

    The words before " / " are the masculine form; they match as many words
    after it, which are the feminine one; the rest is common to both. Words
    before the first gendered one are common too ("Garde forestier /
    Forestière"). Titles in another shape (no or several " / ") are
    returned unchanged.

    `style='esco'`: ESCO titles in German, Spanish or Italian write both
    full forms around one "/" ("Busfahrer/Busfahrerin")."""
    if style == "esco":
        parts = title.split("/")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            return title
        return parts[0 if gender == "M" else 1].strip()
    if title.count(" / ") != 1:
        return title
    left, right = title.split(" / ")
    if right.lower() in left.lower():
        # "Homme sage-femme / Sage-femme": the feminine form is part of the masculine one.
        return left if gender == "M" else right
    masculine, feminine = left.split(), right.split()
    # The first gendered word of the left side starts like the feminine form;
    # if none does ("Homme / Femme de pied"), the whole left side is gendered.
    start = next((i for i, word in enumerate(masculine) if word[:3].lower() == feminine[0][:3].lower()), 0)
    common, gendered = masculine[:start], masculine[start:]
    if len(feminine) < len(gendered):
        return title
    rest = feminine[len(gendered):]
    feminine = feminine[:len(gendered)]
    if common and gendered[0][0].islower():
        feminine[0] = feminine[0][0].lower() + feminine[0][1:]
    return " ".join(common + (gendered if gender == "M" else feminine) + rest)


def _generator_locale(generator: Any) -> str | None:
    """The locale of a Faker generator (or of the first locale of a Faker proxy)."""
    config = getattr(generator, "_Generator__config", None)
    if isinstance(config, dict) and config.get("locale"):
        return str(config["locale"])
    locales = getattr(generator, "locales", None)
    if locales:
        return str(locales[0])
    return None


def _occupation_locale(locale: str | None) -> str:
    """The occupation data used for a Faker locale, by language: French for
    'fr', 'fr_FR', 'fr_CA'..., German for 'de_DE', 'de_AT'..., Spanish,
    Italian, Portuguese ('pt_BR'), Dutch ('nl_BE'), Polish; else English."""
    language = locale.replace("-", "_").split("_")[0].lower() if locale else None
    return next((known for known in OCCUPATION_LOCALES if known.startswith(f"{language}_")),
                DEFAULT_OCCUPATION_LOCALE)


def _local_experience_text(conditions: dict[str, Any], low: int, high: int) -> str:
    """The experience asked in the local wording ('Débutant accepté', '1 à 3 ans'...)."""
    return conditions["experience_none"] if low == 0 else conditions["experience_range"].format(min=low, max=high)


def _local_salary_text(conditions: dict[str, Any], low: int, high: int) -> str:
    """The salary in the local wording ('31 000 € - 34 500 € brut/an'...)."""
    salary_format = conditions["salary_format"]

    def amount(value: int) -> str:
        return f"{value:,}".replace(",", salary_format["thousands"])

    return str(salary_format["template"].format(min=amount(low), max=amount(high), currency=conditions["currency"]))


class _RoleTexts(TypedDict):
    description: str
    skills: str
    responsibilities: str


def _role_texts(occupation: Mapping[str, Any], activities: list[str]) -> _RoleTexts:
    """Description, skills and responsibilities of an occupation, in the
    `RoleRecord` shape: the ESCO description (else the activities: ROME sheets
    have none), knowledge and soft skills, the given activities."""
    skills = list(occupation["knowledge"][:5]) + list(occupation["soft_skills"][:3])
    return {
        "description": occupation["description"] or "; ".join(activities),
        "skills": ", ".join(skills or activities),
        "responsibilities": "; ".join(activities),
    }


def _seniority(experience_min: int) -> str:
    """'junior' (under 3 years of experience asked), 'mid' (3 to 7) or 'senior' (8 and more)."""
    return "junior" if experience_min < 3 else "mid" if experience_min < 8 else "senior"


def _check_count(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


class JobsProvider(BaseProvider):
    """Provider for generating job-market related data.

    Every method is prefixed with `job_` so as not to shadow Faker's own
    `job()` (a random job title from Faker's job provider) or `company()`.
    """

    #: Force the occupation data (one of OCCUPATION_LOCALES) whatever the Faker
    #: locale, e.g. in a subclass. None (default) follows the Faker locale.
    occupations_locale: str | None = None

    @property
    def _occupations(self) -> dict[str, Any]:
        locale = self.occupations_locale
        if locale is None:
            own = (_generator_locale(self.generator) or "").replace("-", "_")
            locale = _occupation_locale(own)
            if _OCCUPATION_VARIANTS.get(own) == locale:  # pt_BR: the Portuguese occupations, Brazilian spelling
                return _load_occupations(locale, own)
        elif locale not in OCCUPATION_LOCALES:
            raise ValueError(f"occupations_locale must be one of {OCCUPATION_LOCALES}, got {locale!r}")
        return _load_occupations(locale)

    def _local_conditions(self) -> dict[str, Any]:
        """The posting conditions of the Faker locale's country: its own for
        the locales of conditions.json (fr_FR, fr_BE, de_AT, es_MX, en_GB...);
        for the other locales, neutral ones in the language of the
        occupations with the economy of the locale's territory (en_IN: India,
        ja_JP: Japan, in English; es_AR: Argentina, in Spanish); else those of
        the occupation data (the United States for 'en', 'de_LI'...)."""
        if self.occupations_locale is None:
            locale = _generator_locale(self.generator)
            key = _conditions_locale(locale)
            if key is not None:
                return _country_conditions(key)
            country = _locale_country(locale)
            if country is not None:
                found = self._conditions_in(country)
                if found is not None:
                    return found
        conditions: dict[str, Any] = self._occupations["conditions"]
        return conditions

    def _conditions_in(self, country: str) -> dict[str, Any] | None:
        """The conditions of a posting in `country` (name of `job_countries`) in
        the language of the occupations: those of a locale of the language in
        that country (fr_BE for 'Belgium' in French), else neutral ones with
        its economy (see `_generic_conditions`); None for a country without."""
        base: dict[str, Any] = self._occupations["conditions"]
        if base["country"] == country:
            return base
        return _own_conditions(self._language, country) or _generic_conditions(base, self._language, country)

    def _posting_conditions(self, country: str | None) -> dict[str, Any]:
        """The conditions of a posting in `country` (any name `job_location`
        takes, None: the locale's country): those of the locale, or of the
        country of the job (see `_conditions_in`); the locale's own with a
        forced `occupations_locale` or a country without economy data."""
        home = self._local_conditions()
        if country is None or self.occupations_locale is not None:
            return home
        local_country = (home.get("place_names") or {}).get("country", home["country"])
        if str(country).strip().lower() in (local_country.lower(), home["country"].lower()):
            return home
        entry = _country_entry(country)
        if entry is None:
            return home  # an unknown country: job_location raises
        return self._conditions_in(entry["country"]) or home

    @property
    def _language(self) -> str:
        """The language of the occupation data ('fr', 'en'...)."""
        return str(self._occupations["meta"]["language"])

    # -- job titles / roles -----------------------------------------------------

    @property
    def job_titles(self) -> list[str]:
        """list: every job title of the occupations, sorted ('Conducteur /
        Conductrice de bus' in French locales, 'bus driver' in English ones...)."""
        return sorted(title for title, _ in self._occupations["occupations_by_job_title"].values())

    def job_title(self, weighted: bool = True) -> str:
        """Return a random job title: a title of an occupation picked by
        demand (`weighted=False`: uniformly), in the locale's language (see
        `job_occupation_title`).

        Not to be confused with Faker's own `job()`, unrelated to this provider."""
        return self.job_occupation_title(weighted=weighted)

    @property
    def job_roles(self) -> list[str]:
        """list: every occupation name, sorted (see `job_occupation`)."""
        return sorted(occupation["title"] for occupation in self._occupations["occupations"])

    def job_role(self, job_title: str | None = None, weighted: bool = True) -> str:
        """Return the name of a random occupation (of one that has
        `job_title` among its titles), as `job_posting()` gives it.
        `weighted` works as in `job_title`."""
        return self._local_role(job_title, None, weighted)[0]["title"]

    def job_role_record(
        self, job_title: str | None = None, role: str | None = None, weighted: bool = True
    ) -> RoleRecord:
        """Return a random occupation (or the one named `role`, or one that
        has `job_title`), as in `job_posting()`: `role` is its name,
        `job_title` one of its titles, `description` its ESCO description
        (else its activities: ROME sheets have none), `skills` its knowledge
        and soft skills, `responsibilities` five of its activities."""
        occupation, title = self._local_role(job_title, role, weighted)
        activities = self.generator.random.sample(occupation["skills"], min(5, len(occupation["skills"])))
        return {"job_title": title, "role": occupation["title"], **_role_texts(occupation, activities)}

    def _local_role(
        self, job_title: str | None, role: str | None, weighted: bool
    ) -> tuple[dict[str, Any], str]:
        """(occupation, job title): the occupation named `role`, or one that
        has `job_title`, or one picked by demand."""
        data = self._occupations
        title = None
        if job_title is not None:
            entry = data["occupations_by_job_title"].get(str(job_title).strip().lower())
            if entry is None:
                similar = _suggest_similar(job_title, [t for t, _ in data["occupations_by_job_title"].values()])
                msg = f"Unknown job title: {job_title!r}"
                if similar:
                    msg += f". Did you mean: {', '.join(similar)}?"
                raise ValueError(msg)
            title, candidates = entry
        if role is not None:
            occupation = data["occupation_by_title"].get(str(role).strip().lower())
            if occupation is None:
                similar = _suggest_similar(role, [o["title"] for o in data["occupations"]])
                msg = f"Unknown role: {role!r}"
                if similar:
                    msg += f". Did you mean: {', '.join(similar)}?"
                raise ValueError(msg)
            if title is not None and occupation not in candidates:
                raise ValueError(f"Role {role!r} does not belong to job title {job_title!r}")
        elif title is not None:
            occupation = self.random_element(candidates)
        else:
            occupation = self._pick_occupation(weighted=weighted)
        return occupation, title if title is not None else self.random_element(occupation["titles"])

    def job_description(self, role: str | None = None) -> str:
        """Return the description of the given occupation, or of a random one."""
        return self.job_role_record(role=role)["description"]

    def job_skills(self, role: str | None = None) -> str:
        """Return the skills (knowledge and soft skills) of the given occupation, or of a random one."""
        return self.job_role_record(role=role)["skills"]

    def job_responsibilities(self, role: str | None = None) -> str:
        """Return five activities of the given occupation, or of a random one."""
        return self.job_role_record(role=role)["responsibilities"]

    # -- qualifications / experience / salary -----------------------------------

    def _default_qualification(self, conditions: dict[str, Any], level: str, sector: str) -> str:
        """A default local diploma of a skill level, in the field of study of
        `sector` when the diploma names one ("Bachelor im Bereich Logistik")."""
        template = self.random_element(conditions["qualifications"][level])
        return str(template).format(field=conditions["fields_of_study"][sector])

    def job_qualification(self) -> str:
        """Return a random local diploma ('Bac+2 (BTS, DUT)', 'Abgeschlossene
        Berufsausbildung im Bereich Logistik', "Bachelor's degree in Computer
        Science"...): one of a random skill level, in the field of study of a
        random activity sector when it names one."""
        conditions = self._local_conditions()
        level = self.random_element(sorted(conditions["qualifications"]))
        return self._default_qualification(conditions, level, self.job_activity_sector())

    def job_experience_range(self) -> tuple[int, int]:
        """Return a random (min, max) years-of-experience range, e.g. (1, 3):
        the range asked for a random skill level, as in the postings."""
        conditions = self._local_conditions()
        return self._local_experience(self.random_element(sorted(conditions["experience"])), None, conditions)

    def job_experience(self) -> str:
        """Return a random experience requirement in the local wording
        ('1 à 3 ans', 'Débutant accepté', '2-5 years of experience'...)."""
        return _local_experience_text(self._local_conditions(), *self.job_experience_range())

    def job_salary_bounds(self) -> tuple[int, int]:
        """Return a random (min, max) yearly gross salary in the local
        currency, e.g. (31000, 34500): from the earnings of a random
        occupation's ISCO major group (see `job_occupation_posting`), for a
        full-time employee."""
        conditions = self._local_conditions()
        occupation = self._pick_occupation()
        experience = self._local_experience(conditions["skill_levels"][occupation["isco_group"]], None, conditions)
        full_time = {"salary_factor": 1, "employee": True}
        return self._local_salary(occupation["isco_group"], None, experience, full_time, conditions)

    def job_salary_range(self) -> str:
        """Return a random yearly salary range in the local wording
        ('31 000 € - 34 500 € brut/an', '$52,000 - $61,500 a year'...)."""
        return _local_salary_text(self._local_conditions(), *self.job_salary_bounds())

    # -- work type / benefits / portals -----------------------------------------

    def job_work_type(self) -> str:
        """Return a random local contract type (CDI, CDD, Befristet,
        Full-time...), with the mix of a random occupation (see `job_occupation_posting`)."""
        return self._local_contract(self._pick_occupation(), self._local_conditions())

    def job_benefits(self, count: int | None = None) -> list[str]:
        """Return `count` distinct local benefits ('Tickets restaurant',
        'Health insurance'...), picked uniformly; default count as in the
        local postings."""
        conditions = self._local_conditions()
        names = list(conditions["benefits"])
        count = conditions["benefits_per_posting"] if count is None else count
        _check_count("count", count)
        if count > len(names):
            raise ValueError(f"count must be at most {len(names)}, got {count!r}")
        return self.generator.random.sample(names, count)

    def job_portal(self) -> str:
        """Return a random local job board (France Travail, StepStone, Indeed...)."""
        portals = self._local_conditions()["job_portals"]
        return self.random_element(portals["all"] + portals.get("executive", []))

    # -- locations --------------------------------------------------------------

    @property
    def job_countries(self) -> list[str]:
        """list: every country a job can be located in (244), sorted, with
        the English names of `job_location(country=...)` ('France', 'United States'...)."""
        return sorted(entry["country"] for entry in _load_cities().values())

    def job_location(self, country: str | None = None) -> LocationRecord:
        """Return a random job location (city, country and coordinates), in
        the locale's country by default (Belgium for fr_BE, the United
        Kingdom for en_GB, Japan for ja_JP..., the United States for 'en'),
        or in the given `country` (see `job_countries`).

        Cities are those of 15,000 inhabitants or more (GeoNames), picked in
        proportion to their population: Paris comes up more often than
        Annecy. Their names are in English ('Munich'), except in the
        locale's own country for the locales but English ones ('München',
        'Deutschland'; 'Genf', 'Schweiz' for de_CH; 'Warszawa'), and
        in another country with conditions in the language ('Belgique' for
        fr_FR)."""
        return self._local_location(self._posting_conditions(country), country)

    def _local_location(self, conditions: dict[str, Any], country: str | None) -> LocationRecord:
        """A location, in the locale's country by default (its local name is
        accepted too), with the local names of the country and its cities."""
        local_country = (conditions.get("place_names") or {}).get("country", conditions["country"])
        if country is None:
            country = self._home_country(conditions)
        elif str(country).strip().lower() == local_country.lower():
            country = conditions["country"]
        else:
            entry = _country_entry(country)
            country = entry["country"] if entry is not None else country  # 'US', 'USA' -> 'United States'
        local = country == conditions["country"]
        # In a country of several languages, the regions of the locale's (Quebec for fr_CA).
        return self._city(country, local_country if local else None, conditions.get("regions") if local else None)

    @staticmethod
    def _home_country(conditions: dict[str, Any]) -> str:
        """The locale's country (name of `job_countries`): that of its conditions."""
        return str(conditions["country"])

    def _city(
        self, country: str, local_country: str | None = None, regions: list[str] | None = None,
    ) -> LocationRecord:
        """A city of `country`, picked by population; with `local_country`,
        the local names of the city and the country; with `regions`, one of
        those regions (GeoNames admin1 codes) where the country has them."""
        entry = _country_entry(country)
        if entry is None:
            similar = _suggest_similar(country, self.job_countries)
            msg = f"Unknown country: {country!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            raise ValueError(msg)
        rng = self.generator.random
        cities, cum_weights = entry["cities"], entry["cum_weights"]
        if regions and entry["regions"]:
            cities, cum_weights = _regional_cities(entry, tuple(regions))
        if cum_weights is None:
            row = rng.choice(cities)
        else:
            row = rng.choices(cities, cum_weights=cum_weights)[0]
        return self._city_record(entry, row, local_country, self._language)

    @staticmethod
    def _city_record(
        entry: dict[str, Any], row: list[Any], local_country: str | None, language: str,
    ) -> LocationRecord:
        """A location record of a city row; with `local_country`, the city's name in `language`;
        the country's name in `language` ('Allemagne'), else `local_country`."""
        local = local_country is not None and len(row) > 4
        return {
            "city": row[4].get(language, row[0]) if local else row[0],
            "country": local_country if local_country is not None else entry["names"].get(language, entry["country"]),
            "latitude": row[1],
            "longitude": row[2],
        }

    # -- companies --------------------------------------------------------------

    @property
    def job_sectors(self) -> list[str]:
        """list: the sectors of the companies: the activity sectors of the
        occupations (see `job_activity_sectors`)."""
        return self.job_activity_sectors

    @property
    def job_companies(self) -> list[str]:
        """list: the names of the real companies of the locale's country
        (People Data Labs, e.g. 'IBM'), sorted. The company of a posting or
        profile may also be made up by the Faker locale (see
        `job_occupation_posting`)."""
        country = self._home_country(self._local_conditions())
        return sorted(row[0] for _, _, row in _load_companies()["by_name"].get(country, {}).values())

    def job_company(self, sector: str | None = None) -> str:
        """Return a random hiring company name, optionally of an activity
        sector (see `job_activity_sectors`), as `job_company_profile`.

        Not named `company` so as not to shadow Faker's own `company()`."""
        return self.job_company_profile(sector=sector)["company"]

    def job_company_profile(self, company: str | None = None, sector: str | None = None) -> CompanyProfile:
        """Return the profile of a hiring company of the locale's country.

        Without `company`: a company of an activity sector (`sector`, else a
        random one), picked as the hiring companies of
        `job_occupation_posting` (by size class, real or made up), in a city
        of the country. With `company`: that company of `job_companies`
        ('ibm' -> IBM, case-insensitive), else a company of that name made
        up by the Faker locale, with a city of the country and a CEO, in
        `sector` (else a random one). In the locales but English ones, an
        activity (NAF / NACE) of the sector as `industry`."""
        conditions = self._local_conditions()
        if company is not None:
            country = self._home_country(conditions)
            found = _load_companies()["by_name"].get(country, {}).get(str(company).strip().lower())
            if found is not None:
                code, size_class, row = found
                name = {code: name for name, code in conditions["sector_codes"].items()}[code]
                return self._real_company(row, name, country, conditions, None)[0]
        name = self._resolve_activity_sector(sector) if sector is not None else self.job_activity_sector()
        if company is not None:
            return self._local_company(name, conditions, self.job_location(), company)
        return self._hiring_company(name, conditions, self.job_location())[0]

    def job_company_size(self) -> int:
        """Return a random company size (number of employees): a size class
        (1-10, 11-50... 10001+ employees) picked by the share of jobs in the
        companies of each class in the locale's country (People Data Labs,
        every sector), then a number of employees in that class."""
        entry = self._companies_entry(self._home_country(self._local_conditions()))
        return self._class_size(self._pick_size_class(entry["cum_weights_all"]))

    def _companies_entry(self, country: str) -> dict[str, Any]:
        """The companies of a country (companies.json.gz), else those of the
        country of the occupation data, whose size shares stand for it."""
        countries = _load_companies()["countries"]
        entry: dict[str, Any] = countries.get(country) or countries[self._occupations["conditions"]["country"]]
        return entry

    def _pick_size_class(self, cum_weights: list[float]) -> int:
        return self.generator.random.choices(range(len(cum_weights)), cum_weights=cum_weights)[0]

    def _class_size(self, size_class: int) -> int:
        """A number of employees in a size class, log-uniform (as many companies of 11-20 as of 20-40)."""
        low, high = _load_companies()["classes"][size_class]
        return round(math.exp(self.generator.random.uniform(math.log(low), math.log(high))))

    def _company_country(self, conditions: dict[str, Any], location: LocationRecord) -> str | None:
        """The country of `location` (name of `job_countries`) when it has companies, else None."""
        local_country = (conditions.get("place_names") or {}).get("country", conditions["country"])
        if location["country"] == local_country:
            country = conditions["country"]
        else:  # another country, maybe by its name in the language ('Allemagne')
            entry = _country_entry(location["country"])
            country = entry["country"] if entry is not None else location["country"]
        return country if country in _load_companies()["countries"] else None

    def _pick_naf(
        self, sector: str, conditions: dict[str, Any], industry: str | None = None, isco: str | None = None,
    ) -> list[Any] | None:
        """An activity [code, label, NACE section, weight] of the activity
        sector: a NAF sub-class in French locales, a NACE class in German,
        Spanish and Italian ones, None in English ones. Only those that fit
        the company's LinkedIn `industry`, when some do; then, for an
        occupation (ISCO unit group `isco`), picked by its employees in each
        activity (French census), else by employment."""
        if "naf_by_sector" not in conditions:
            return None
        candidates = list(enumerate(conditions["naf_by_sector"][sector]))
        prefixes = conditions["naf_by_industry"].get(industry.lower()) if industry else None
        if prefixes:
            candidates = [(i, naf) for i, naf in candidates if naf[0].startswith(tuple(prefixes))] or candidates
        fit = dict(map(tuple, self._occupations["naf_by_isco"].get(isco, {}).get(sector, ())))
        weights = [fit.get(i, 0) for i, _ in candidates]
        if not any(weights):
            weights = [naf[3] for _, naf in candidates]
        found: list[Any] = self.generator.random.choices(candidates, weights=weights)[0][1]
        return found

    def _hiring_company(
        self, sector: str, conditions: dict[str, Any], location: LocationRecord, isco: str | None = None,
    ) -> tuple[CompanyProfile, int, LocationRecord, list[Any] | None]:
        """A company of the activity sector `sector` hiring in `location`,
        its number of employees, the job location and its activity (NAF /
        NACE, None in English locales) for an occupation of ISCO unit group
        `isco`.

        Its size class is picked by the share of jobs of each class in the
        sector and the country of the job (People Data Labs), then a real
        company of that sector and class, else (1-10 employees, a country
        without companies, or at random in a class of fewer than 10
        companies) a company made up by the Faker locale in the job's city.
        When the activities that employ the occupation are known (French,
        German, Spanish and Italian locales), the activity is picked first
        (see `_pick_naf`), then a real company whose LinkedIn industry has
        that activity (no farming cooperative for an aquaculture worker),
        else a made-up one. Companies of up to 500 employees hire in their
        headquarters city when it is one of the cities of `job_location`.
        The activity is the company's industry."""
        data = _load_companies()
        country = self._company_country(conditions, location)
        entry = self._companies_entry(country or self._home_country(conditions))
        code = conditions["sector_codes"][sector]
        size_class = self._pick_size_class(entry["cum_weights"].get(code, entry["cum_weights_all"]))
        rows = entry["by_class"][code][size_class] if country is not None and code in entry["by_class"] else []
        if rows and self.generator.random.random() * _COMPANIES_PER_CLASS >= entry["counts"][code][size_class]:
            rows = []  # a class of few companies: a made-up one in its place
        naf = None
        if "naf_by_sector" in conditions and sector in self._occupations["naf_by_isco"].get(isco, {}):
            naf = self._pick_naf(sector, conditions, isco=isco)
            assert naf is not None
            industries, by_industry = data["industries"], conditions["naf_by_industry"]
            rows = [row for row in rows if naf[0].startswith(tuple(by_industry.get(industries[row[6]].lower(), ())))]
        if country is None or not rows:
            if naf is None:
                naf = self._pick_naf(sector, conditions, isco=isco)
            company = self._local_company(sector, conditions, location, naf=naf)
            return company, self._class_size(size_class), location, naf
        row = self.random_element(rows)
        if naf is None:
            naf = self._pick_naf(sector, conditions, data["industries"][row[6]], isco)
        profile, size, headquarters = self._real_company(row, sector, country, conditions, naf)
        if headquarters is not None and size_class <= _SINGLE_SITE_MAX_CLASS and _in_regions(
                country, row[3], conditions.get("regions") if country == conditions["country"] else None):
            location = headquarters
        return profile, size, location, naf

    def _real_company(
        self, row: list[Any], sector: str, country: str, conditions: dict[str, Any], naf: list[str] | None,
    ) -> tuple[CompanyProfile, int, LocationRecord | None]:
        """The profile of a People Data Labs company (a row of companies.json.gz),
        its number of employees and its headquarters city (None if not one
        of the cities of `job_location`)."""
        data = _load_companies()
        name, website, founded, city, state, size, industry = row
        if naf is None:
            naf = self._pick_naf(sector, conditions, data["industries"][industry])
        headquarters = None
        if isinstance(city, int):
            local = country == conditions["country"]
            local_country = (conditions.get("place_names") or {}).get("country", conditions["country"])
            cities = _load_cities()[country.lower()]
            headquarters = self._city_record(cities, cities["cities"][city], local_country if local else None,
                                             self._language)
            city = headquarters["city"]
        if naf is not None:
            industry_name = naf[1]
        elif self._occupations["meta"]["language"] == "en":
            industry_name = data["industries"][industry]
        else:
            industry_name = None  # LinkedIn industries are in English
        return {
            "company": name, "sector": sector, "industry": industry_name, "city": city, "state": state,
            "zip": None, "website": website, "ticker": None, "ceo": None, "founded": founded,
        }, size, headquarters

    # -- occupations (ROME 4.0 / ESCO, locale-aware) -----------------------------

    @property
    def job_activity_sectors(self) -> list[str]:
        """list: every activity sector of the occupations (35, e.g.
        'Healthcare', or 'Santé' in French locales), sorted.

        `job_sectors` is the same list."""
        return list(self._occupations["sectors"])

    @property
    def job_occupation_codes(self) -> list[str]:
        """list: every occupation code (ROME codes like 'M1805' in French
        locales, ESCO concept ids otherwise), sorted."""
        return [occupation["code"] for occupation in self._occupations["occupations"]]

    def _resolve_activity_sector(self, sector: str) -> str:
        data = self._occupations
        name = data["sector_by_name"].get(str(sector).strip().lower())
        if name is None:
            similar = _suggest_similar(sector, data["sectors"])
            msg = f"Unknown activity sector: {sector!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            else:
                msg += f". Available sectors: {', '.join(data['sectors'][:5])}..."
            raise ValueError(msg)
        return name

    def _pick_occupation(
        self, code: str | None = None, sector: str | None = None, weighted: bool = True
    ) -> dict[str, Any]:
        data = self._occupations
        if code is not None:
            found = data["occupation_by_code"].get(str(code).strip().lower())
            if found is None:
                raise ValueError(f"Unknown occupation code: {code!r} (see job_occupation_codes)")
            if sector is not None and self._resolve_activity_sector(sector) not in found["sectors"]:
                raise ValueError(f"Occupation {code!r} is not in activity sector {sector!r}")
            return found
        if sector is None:
            rows, cum_weights = data["occupations"], data["cum_weights"]
        else:
            name = self._resolve_activity_sector(sector)
            rows, cum_weights = data["occupations_by_sector"][name], data["cum_weights_by_sector"][name]
        if weighted:
            return self.generator.random.choices(rows, cum_weights=cum_weights)[0]
        return self.generator.random.choice(rows)

    def job_activity_sector(self) -> str:
        """Return a random activity sector (see `job_activity_sectors`)."""
        return self.random_element(self._occupations["sectors"])

    def job_occupation(self, sector: str | None = None, weighted: bool = True) -> str:
        """Return the name of a random occupation (e.g. 'nurse responsible
        for general care', 'Infirmier / Infirmière de soins généraux' in
        French locales), optionally from an activity sector.

        By default occupations are picked in proportion to their demand in
        France (recruitment projects of the BMO 2026 survey, see
        `OccupationRecord.demand`), in every locale: cooks and care
        assistants come up more often than air traffic controllers.
        `weighted=False` picks uniformly. The same goes for the other
        `job_occupation*` methods."""
        return self._pick_occupation(sector=sector, weighted=weighted)["title"]

    def job_occupation_title(
        self, sector: str | None = None, gender: str | None = None, weighted: bool = True
    ) -> str:
        """Return a random job title (one of the ~14,000 ROME or ESCO job
        titles), optionally from an activity sector; `weighted` as in
        `job_occupation`.

        French titles name both forms ("Conducteur / Conductrice de bus"),
        as ROME does, and so do most German, Spanish and Italian ones
        ("Busfahrer/Busfahrerin"), as ESCO does; `gender='M'` or `'F'`
        gives only the masculine or feminine one. English titles are not
        gendered: `gender` is ignored."""
        if gender not in (None, "M", "F"):
            raise ValueError(f"gender must be None, 'M' or 'F', got {gender!r}")
        title = self.random_element(self._pick_occupation(sector=sector, weighted=weighted)["titles"])
        style = self._occupations["gender"]
        if gender is not None and style is not None:
            return _gender_form(title, gender, style["titles"])
        return title

    def job_occupation_record(
        self, code: str | None = None, sector: str | None = None, weighted: bool = True
    ) -> OccupationRecord:
        """Return a dict describing the given occupation (by `code`) or a
        random one, optionally from an activity sector (`weighted` as in
        `job_occupation`): its name, a job title, domain, sectors,
        description, skills, knowledge and soft skills."""
        return self._occupation_record(self._pick_occupation(code=code, sector=sector, weighted=weighted), sector)

    def _occupation_record(
        self, found: dict[str, Any], sector: str | None, job_title: str | None = None
    ) -> OccupationRecord:
        """The `OccupationRecord` of an occupation, with `job_title` (else a random one of its titles)."""
        return {
            "code": found["code"],
            "title": found["title"],
            "job_title": job_title if job_title is not None else self.random_element(found["titles"]),
            "domain": found["domain"],
            "sector": self._resolve_activity_sector(sector) if sector is not None else found["sectors"][0],
            "sectors": list(found["sectors"]),
            "description": found["description"],
            "skills": list(found["skills"]),
            "knowledge": list(found["knowledge"]),
            "soft_skills": list(found["soft_skills"]),
            "qualifications": list(found["qualifications"]),
            "executive": found["executive"],
            "regulated": found["regulated"],
            "riasec": list(found["riasec"]),
            "transitions": list(found["transitions"]),
            "isco_code": found["isco_code"],
            "isco_group": found["isco_group"],
            "demand": found["weight"],
            "seasonal": found["seasonal"],
        }

    def job_occupation_skills(
        self, code: str | None = None, count: int = 5, sector: str | None = None, weighted: bool = True
    ) -> list[str]:
        """Return `count` distinct skills of the given occupation (by `code`)
        or of a random one (optionally from an activity sector), e.g.
        ['administer medication', ...]. Returns all of them when the
        occupation has fewer than `count`."""
        _check_count("count", count)
        skills = self._pick_occupation(code=code, sector=sector, weighted=weighted)["skills"]
        return self.generator.random.sample(skills, min(count, len(skills)))

    def job_occupation_posting(
        self,
        code: str | None = None,
        sector: str | None = None,
        country: str | None = None,
        skills: int = 5,
        weighted: bool = True,
        id_template: str | None = None,
    ) -> OccupationPosting:
        """Return a full random job posting built on an occupation (see
        `OccupationPosting`), in the language of the Faker locale.

        - `code` / `sector` choose the occupation (see `job_occupation_record`).
        - The hiring company is in the occupation's sector (the requested
          one, else its main one) and the country of the job: its size class
          (1-10 ... 10001+ employees) is picked by the share of jobs of each
          class in that sector and country, then a real company of that
          class (People Data Labs: name, website, founding year,
          headquarters), or one made up by the Faker locale for 1-10
          employees or outside the countries of the locales with
          conditions of their own. Companies of up to 500 employees
          hire in their headquarters city when it is a city of
          `job_location`. Locales other than English add an
          activity of the sector that employs the occupation (NAF / NACE).
        - `skills`: how many of the occupation's skills to list (default 5).
        - `country` sets the job location (default: the locale's country,
          see `job_location`).
        - `weighted` picks the occupation by demand (see `job_occupation`).
        - `id_template` makes `job_id` a string from a template (see
          `job_id`), with the posting date and the country of the job.

        Local conditions, those of the country of the job (`country`, else
        the locale's: see `job_location`), in the language of the locale:
        a locale's own (fr_BE for a French posting in Belgium), else neutral
        ones (contracts, benefits, diplomas found in most countries,
        international job boards) with the country's currency, salaries and
        minimum wage (countries.json: Eurostat SES, ILOSTAT earnings by ISCO
        group or the GDP per capita), and the locale's conditions in the few
        countries without figures (North Korea...); with
        `occupations_locale` set, always the locale's.

        Benefits, job boards and default diplomas are hand-made and
        illustrative (scripts/posting_conditions.py); the contract comes
        from a national mix adapted to the occupation's ISCO major group
        (Eurostat LFS shares of temporary, part-time and self-employed
        workers; not for the United States and the countries with
        OECD-scaled earnings), with a "CDD saisonnier" at the
        occupation's `seasonal` share in France; the experience
        asked follows the occupation's skill level (ISCO major group), and
        the salary comes from official mean earnings: Eurostat SES 2022 by
        ISCO major group and NACE section (France, Germany, Spain, Italy,
        Belgium, Switzerland, Austria, Luxembourg, Ireland), BLS OEWS by SOC
        major group (United States), those of the country of the language
        times the ratio of the OECD average wages (Canada, Mexico, Chile,
        Colombia, United Kingdom, Australia, New Zealand), those of
        countries.json elsewhere (no section, no contract adaptation), adjusted to the
        experience asked (earnings by age), to the contract (internships,
        apprenticeships, part-time) and kept above the minimum wage. ROME
        diplomas come first in France.
        """
        _check_count("skills", skills)
        occupation = self.job_occupation_record(code=code, sector=sector, weighted=weighted)
        return self._templated_id(self._occupation_posting(occupation, country, skills), id_template)

    def _templated_id(self, posting: OccupationPosting, id_template: str | None) -> OccupationPosting:
        """The posting with its `job_id` from `id_template` (its date and country), if given."""
        if id_template is not None:
            posting["job_id"] = self.job_id(id_template, posting["job_posting_date"], posting["location"]["country"])
        return posting

    def _occupation_posting(
        self, occupation: OccupationRecord, country: str | None, skills: int,
        employer: tuple[CompanyProfile, int, LocationRecord | None, list[Any] | None] | None = None,
    ) -> OccupationPosting:
        """A posting of `occupation`; by a given `employer` (profile, number of
        employees, the city of all its jobs or None for any city of the country,
        activity) instead of a hiring company picked for it (job_dataset)."""
        conditions = self._posting_conditions(country)
        terms = self._local_terms(occupation, conditions, country)
        if employer is None:
            company, company_size, location, naf = self._hiring_company(
                occupation["sector"], conditions, terms["location"], occupation["isco_code"])
        else:
            company, company_size, site, naf = employer
            location = site if site is not None else terms["location"]
        # The salary follows the NACE section of the company's activity (NAF /
        # NACE), else that of the occupation's sector (English locales).
        section = naf[2] if naf is not None else conditions["section_by_sector"].get(occupation["sector"])
        salary_min, salary_max = self._local_salary(
            occupation["isco_group"], section, (terms["experience_min"], terms["experience_max"]),
            conditions["contracts"][terms["work_type"]], conditions)
        job_title = occupation["job_title"]
        style = self._occupations["gender"]
        if style is not None:
            # The country's own gender mark: "(H/F/X)" in Belgium, none in Canada.
            style = {**style, "posting_suffix": conditions.get("posting_suffix", style["posting_suffix"])}
        if style is not None and style["posting_suffix"]:
            # Masculine form and the mark for every gender: "Busfahrer (m/w/d)".
            # ESCO alternative labels have a single form, sometimes the
            # feminine one ("Inspizientin"): start from the preferred label.
            if style["titles"] == "esco":
                job_title = occupation["title"]
            job_title = f'{_gender_form(job_title, "M", style["titles"])} {style["posting_suffix"]}'

        return {
            "job_id": self.job_id(),
            "job_title": job_title,
            "occupation": occupation,
            "skills": self.generator.random.sample(occupation["skills"], min(skills, len(occupation["skills"]))),
            "qualification": terms["qualification"],
            "experience": terms["experience"],
            "experience_min": terms["experience_min"],
            "experience_max": terms["experience_max"],
            "salary_range": _local_salary_text(conditions, salary_min, salary_max),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": conditions["currency"],
            "work_type": terms["work_type"],
            "benefits": terms["benefits"],
            "location": location,
            "company": company,
            "company_sector": occupation["sector"],
            "company_naf": self._activity_code(naf, conditions),
            "company_size": company_size,
            "seniority": _seniority(terms["experience_min"]),
            "job_portal": terms["job_portal"],
            "job_posting_date": self.job_posting_date(),
            "contact_person": self.generator.name(),
            "contact": self._phone_number(),
            "remote": self._remote(occupation["isco_group"], conditions["country"]),
        }

    def _remote(self, isco_group: str | None, country: str) -> str:
        """'on_site', 'hybrid' or 'remote': the country's share of employees
        working from home (usually + sometimes; Eurostat, else the EU's) times
        the occupation group's factor, of which a part is full remote."""
        usually, sometimes = _labour(country)["telework"]
        share = min(MAX_REMOTE_SHARE, (usually + sometimes) * REMOTE_FACTORS.get(isco_group or "", 1.0))
        if self.generator.random.random() >= share:
            return "on_site"
        full = FULL_REMOTE_SHARE * usually / (usually + sometimes) if usually + sometimes else 0
        return "remote" if self.generator.random.random() < full else "hybrid"

    def _phone_number(self) -> str:
        """A phone number of the Faker locale; a generic one where it has none (en_PH, fil_PH...)."""
        if hasattr(self.generator, "phone_number"):
            return str(self.generator.phone_number())
        return str(self.generator.numerify("+## ### ### ####"))

    @staticmethod
    def _activity_code(naf: list[Any] | None, conditions: dict[str, Any]) -> str | None:
        """The activity code of a company: the NAF sub-class ('86.10Z'), its
        NACE class ('86.10') outside France (`activity_code` 'nace'), a
        NACE class in the other locales but English; None without."""
        if naf is None:
            return None
        code = str(naf[0])
        return code[:5] if conditions.get("activity_code") == "nace" else code

    def _local_company(
        self, sector: str, conditions: dict[str, Any], location: LocationRecord, name: str | None = None,
        naf: list[str] | None = None,
    ) -> CompanyProfile:
        """A company made up by the Faker locale (or named `name`) in
        `sector`, in the city of the posting; with an activity of the sector
        (`naf`, else one picked by employment; NAF / NACE, none in English locales) as industry."""
        if naf is None:
            naf = self._pick_naf(sector, conditions)
        return {
            "company": name if name is not None else self.generator.company(),
            "sector": sector, "industry": naf[1] if naf else None, "city": location["city"], "state": None,
            "zip": None, "website": None, "ticker": None, "ceo": self.generator.name(), "founded": None,
        }

    def _local_benefits(self, occupation: OccupationRecord, conditions: dict[str, Any], contract: str) -> list[str]:
        """Local benefits that fit the job and contract: remote work and
        flexible hours for office or executive jobs, a company car for
        executives, no bonus for interns, only those office benefits for
        freelancers..."""
        office = occupation["executive"] or occupation["domain"] in conditions["office_domains"]
        allowed = {"office": office, "executive": occupation["executive"], None: True}
        employee = conditions["contracts"][contract]["employee"]
        eligible = [name for name, rule in conditions["benefits"].items()
                    if allowed[rule["requires"]] and contract not in rule["not_for"]
                    and (employee or rule["requires"] == "office")]
        return self.generator.random.sample(eligible, min(conditions["benefits_per_posting"], len(eligible)))

    def _local_salary(
        self, group: str, section: str | None, experience: tuple[int, int], contract: dict[str, Any],
        conditions: dict[str, Any],
    ) -> tuple[int, int]:
        """Yearly gross salary bounds: the mean earnings of the occupation's
        ISCO major group in the company's NACE section (else in every
        section), times the ratio of the age band that matches the
        experience asked, times the contract's share of a full-time salary;
        spread around that value, rounded, and not below the minimum wage
        for a full-time employee."""
        rng = self.generator.random
        salary = conditions["salary"]
        means = salary["base"][group]
        base = means.get(section, means["*"]) if section else means["*"]
        middle = sum(experience) / 2
        band = "Y_LT30" if middle < 5 else "Y30-49" if middle < 20 else "Y_GE50"
        center = base * salary["age_ratio"][group][band] * contract["salary_factor"]
        low, high = center * rng.uniform(0.85, 0.95), center * rng.uniform(1.05, 1.2)
        # Rounded to 500 or 1,000 units (EUR, USD...), 10 times more in MXN, 1,000 times in CLP and COP.
        scale = conditions.get("salary_scale", 1)
        step = (1000 if center >= 100_000 * scale else 500) * scale
        low, high = round(low / step) * step, round(high / step) * step
        minimum = conditions["minimum_wage"]
        if minimum and contract["salary_factor"] == 1 and contract["employee"] and low < minimum:
            low = -(-minimum // step) * step   # rounded up, so never below the minimum wage
        return int(low), int(max(high, low + step))

    def _local_experience(
        self, level: str, cap: int | None, conditions: dict[str, Any]
    ) -> tuple[int, int]:
        """(min, max) years of experience asked for a skill level, capped by the contract."""
        bounds = conditions["experience"][level]
        experience_min = self.random_int(*bounds["low"])
        experience_max = experience_min + self.random_int(*bounds["gap"])
        if cap is not None:
            experience_min, experience_max = min(experience_min, cap), min(experience_max, cap)
        return experience_min, experience_max

    def _local_contract(self, occupation: Mapping[str, Any], conditions: dict[str, Any]) -> str:
        """A contract type from the mix of the occupation's ISCO major group
        (see contract_weights() in scripts/build_occupations.py); a seasonal
        contract, where the locale has one, with the occupation's seasonal share."""
        weights = dict(conditions["contract_weights"][occupation["isco_group"]])
        seasonal = [name for name, spec in conditions["contracts"].items() if spec["kind"] == "seasonal"]
        if seasonal:
            share = min(occupation["seasonal"], 0.99)
            others = sum(weight for name, weight in weights.items() if name not in seasonal)
            for name in seasonal:
                weights[name] = others * share / (1 - share) / len(seasonal)
        return self.generator.random.choices(list(weights), weights=list(weights.values()))[0]

    def _local_terms(
        self, occupation: OccupationRecord, conditions: dict[str, Any], country: str | None
    ) -> dict[str, Any]:
        """Local posting conditions (see scripts/posting_conditions.py): the
        contract, the experience and diploma for the occupation's skill
        level, local benefits and job boards, a place. The salary comes after
        the company (see `_occupation_posting`)."""
        level = conditions["skill_levels"][occupation["isco_group"]]
        contracts = conditions["contracts"]
        contract = self._local_contract(occupation, conditions)
        spec = contracts[contract]
        experience_min, experience_max = self._local_experience(level, spec["max_experience"], conditions)
        portals = conditions["job_portals"]
        # ROME sheets list French diplomas: not those of Belgium, Switzerland or Canada.
        if occupation["qualifications"] and conditions.get("rome_diplomas", True):
            qualification = self.random_element(occupation["qualifications"])
        else:
            qualification = self._default_qualification(conditions, level, occupation["sector"])
        return {
            "qualification": qualification,
            "experience": _local_experience_text(conditions, experience_min, experience_max),
            "experience_min": experience_min,
            "experience_max": experience_max,
            "work_type": contract,
            "benefits": self._local_benefits(occupation, conditions, contract),
            "location": self._local_location(conditions, country),
            "job_portal": self.random_element(
                portals["all"] + (portals.get("executive", []) if occupation["executive"] else [])),
        }

    # -- postings ---------------------------------------------------------------

    @overload
    def job_id(
        self, template: None = None, date: _datetime.date | None = None, country: str | None = None,
        n: int | None = None,
    ) -> int: ...

    @overload
    def job_id(
        self, template: str, date: _datetime.date | None = None, country: str | None = None,
        n: int | None = None,
    ) -> str: ...

    def job_id(
        self, template: str | None = None, date: _datetime.date | None = None, country: str | None = None,
        n: int | None = None,
    ) -> int | str:
        """Return a random job posting id: by default a 15 or 16-digit number
        (as in the source data); with a `template`, a string built from it:

        - `#` a random digit, `?` a random uppercase letter, `*` either;
        - `{year}`, `{month}`, `{day}`, `{date}` the posting date (`date`,
          default today), with Python format specs: `{month:02d}`,
          `{date:%y%m%d}`;
        - `{country}` the ISO code of the country of the job (`country`,
          default the locale's: 'FR'), `{locale}` the Faker locale;
        - `{n}` the posting's number (`n`; numbered from 1 in
          `job_dataset`), e.g. `{n:06d}`.

        'JOB-{year}-######' -> 'JOB-2026-048213', '{country}-{date:%y%m}-****'
        -> 'FR-2611-K7Q2', 'REQ{n:05d}' -> 'REQ00042'. The other characters
        are kept; `#`, `?` and `*` are always replaced. `job_posting(id_template=...)`,
        `job_occupation_posting()` and `job_dataset()` take a template too."""
        if template is None:
            return self.random_int(10**14, 10**16 - 1)
        if country is None:
            country = self._local_conditions()["country"]
        return _format_job_id(
            self.generator.random, template, date or _datetime.date.today(), _country_code(country),
            _generator_locale(self.generator) or "", n)

    def job_posting_date(
        self, start_date: _datetime.date | str = "-2y", end_date: _datetime.date | str = "today"
    ) -> _datetime.date:
        """Return a random posting date, by default within the last two
        years (the span of the source data). `start_date` / `end_date`
        accept anything Faker's `date_between()` does (dates, '-30d'...)."""
        return self.generator.date_between(start_date=start_date, end_date=end_date)

    def job_posting(
        self,
        job_title: str | None = None,
        role: str | None = None,
        country: str | None = None,
        sector: str | None = None,
        weighted: bool = True,
        code: str | None = None,
        id_template: str | None = None,
    ) -> JobPosting:
        """Return a full random job posting as a dict (see `JobPosting`),
        built on a ROME / ESCO occupation in the language of the Faker
        locale (see `job_occupation_posting`): every trade, picked by demand.

        - `code`, or `role` (an occupation name, see `job_roles`) and/or
          `job_title` (see `job_titles`), choose the occupation.
        - `sector` is an activity sector (see `job_activity_sectors`): the
          occupation's, and that of the hiring company.
        - `country` sets the job location (see `job_location`).
        - `weighted` (default True) picks popular occupations more often;
          False makes them uniform.
        - `id_template` makes `job_id` a string from a template (see `job_id`).

        The contact person and phone number come from the Faker locale.
        """
        if code is not None and (job_title is not None or role is not None):
            raise ValueError("pass either code, or job_title / role, not both")
        title = None
        if job_title is not None or role is not None:
            found, title = self._local_role(job_title, role, weighted)
            code = found["code"]
        found = self._pick_occupation(code=code, sector=sector, weighted=weighted)
        occupation = self._occupation_record(found, sector, title)
        posting = self._templated_id(self._occupation_posting(occupation, country, 5), id_template)
        return self._occupation_job_posting(posting)

    def job_candidate(
        self, code: str | None = None, sector: str | None = None, country: str | None = None,
        weighted: bool = True,
    ) -> CandidateRecord:
        """Return a random job seeker (see `CandidateRecord`): an occupation
        (by `code`, else picked by demand, optionally of an activity
        `sector`), the title they look for, years of experience for its
        skill level, a diploma, some of its skills and knowledge, the yearly
        salary they ask (around the local earnings of the occupation at that
        experience, in the currency of `country`, default the locale's), when
        they are available; a name, a personal e-mail address and a phone
        number of the Faker locale, in a city of `country`."""
        conditions = self._posting_conditions(country)
        found = self._pick_occupation(code=code, sector=sector, weighted=weighted)
        occupation = self._occupation_record(found, sector)
        return make_candidate(self, conditions, dict(occupation), self._local_location(conditions, country))

    def job_posting_text(
        self, posting: OccupationPosting | JobPosting | None = None, markdown: bool = False
    ) -> str:
        """Return the full text of a job posting, as published on a job
        board: headline, introduction of the company, the job (the ESCO
        description, or for ROME sheets their name and domain), the missions,
        the profile asked (diploma, experience, knowledge, soft skills), the
        conditions (contract, salary, place, benefits) and how to apply.

        `posting` is a dict from `job_occupation_posting()` or `job_posting()`
        (default: a new `job_occupation_posting()`). The text is in the
        language of the occupation data (French, English, German, Spanish,
        Italian, Portuguese, Dutch or Polish), so render a posting with a provider of the locale that made
        it. `markdown=True` gives Markdown headings, bold and bullets; else
        plain text with upper-case headings.

        The wording is hand-made, with a few phrasings per section picked at
        random (reproducible with `Faker.seed()`); every fact comes from the
        posting."""
        from faker_jobs.posting_text import render_posting

        if posting is None:
            posting = self.job_occupation_posting()
        text = render_posting(posting, self._occupations["meta"]["language"], self.generator.random, markdown)
        if self.occupations_locale is None and (_generator_locale(self.generator) or "").replace("-", "_") == "pt_BR":
            from faker_jobs.pt_br import to_brazilian

            text = "\n".join(to_brazilian(line) for line in text.split("\n"))
        return text

    def job_dataset(
        self,
        postings: int = 1000,
        companies: int | None = None,
        start_date: _datetime.date | str = "-2y",
        end_date: _datetime.date | str = "today",
        repost_rate: float = 0.08,
        id_template: str | None = None,
        dirty: float = 0.0,
        candidates: int = 0,
        applications: float = 10.0,
    ) -> "JobDataset":
        """Return a dataset of `postings` job postings published by a pool of
        `companies` employers (default: one per 10 postings; more when a
        sector has none of them) between
        `start_date` and `end_date` (anything `job_posting_date` takes), in
        the locale's country: `JobDataset.companies` and `.postings`, flat
        rows linked by `company_id`, with `to_csv()`, `to_jsonl()` and
        `to_dataframes()`.

        Employers keep their name, city, size and activity in all their
        postings; the postings have a lifecycle (closing date, status
        'open' / 'filled' / 'expired' on `end_date`) and a share
        `repost_rate` of them are published again on another job board
        (`repost_of`). `id_template` gives the job ids from a template (see
        `job_id`; `{n}` numbers the postings from 1), unique in the dataset.
        `dirty` (0 to 1) adds defects of real-world data (typos, missing
        values, monthly salaries, other date formats, unflagged duplicates,
        company name variants...) to that share of the rows, listed in
        `JobDataset.defects` (see faker_jobs/dirty.py). `candidates` adds a
        pool of that many job seekers (`JobDataset.candidates`) and their
        `applications` (about that many a posting; `JobDataset.applications`),
        with a match score and a status that follows the posting's (see
        faker_jobs/candidates.py).
        See faker_jobs/dataset.py; `make_dataset()` mixes several locales."""
        from faker_jobs.dataset import build_dataset

        return build_dataset(self, postings, companies, start_date, end_date, repost_rate, id_template=id_template,
                             dirty=dirty, candidates=candidates, applications=applications)

    @staticmethod
    def _occupation_job_posting(posting: OccupationPosting) -> JobPosting:
        """An occupation posting in the `JobPosting` shape."""
        occupation = posting["occupation"]
        return {
            "occupation": occupation,
            "job_id": posting["job_id"],
            "job_title": posting["job_title"],
            "role": occupation["title"],
            **_role_texts(occupation, posting["skills"]),
            "qualification": posting["qualification"],
            "experience": posting["experience"],
            "experience_min": posting["experience_min"],
            "experience_max": posting["experience_max"],
            "salary_range": posting["salary_range"],
            "salary_min": posting["salary_min"],
            "salary_max": posting["salary_max"],
            "salary_currency": posting["salary_currency"],
            "work_type": posting["work_type"],
            "benefits": posting["benefits"],
            "location": posting["location"],
            "company": posting["company"],
            "company_size": posting["company_size"],
            "seniority": posting["seniority"],
            "job_portal": posting["job_portal"],
            "job_posting_date": posting["job_posting_date"],
            "contact_person": posting["contact_person"],
            "contact": posting["contact"],
            "remote": posting["remote"],
        }
