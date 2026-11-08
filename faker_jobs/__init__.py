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
are those of France, Germany, Spain, Italy or, for every other locale, the
United States.

Job locations are the ~29,500 cities of 15,000 inhabitants or more of
GeoNames in 216 countries, picked in proportion to their population, with
their local names in France, Germany, Spain and Italy. Companies come from
the "Job Description Dataset" (Kaggle): 888 companies with their profile,
used as is in English locales; German, Spanish, French and Italian locales
make their companies up. Contact names and phone numbers always come from
the Faker locale.
"""
import difflib
import gzip
import datetime as _datetime
import itertools
import json
import os
from collections.abc import Mapping
from typing import Any, TypedDict

from faker.providers import BaseProvider

__version__ = "0.5.0"

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_DATA_PATH = os.path.join(_DATA_DIR, "jobs_data.json")
_data_cache: dict[str, Any] | None = None
_CITIES_PATH = os.path.join(_DATA_DIR, "cities.json.gz")
_cities_cache: dict[str, Any] | None = None

# Locales with their own occupation data, and the one used for every other locale.
OCCUPATION_LOCALES = ("de_DE", "en_US", "es_ES", "fr_FR", "it_IT")
DEFAULT_OCCUPATION_LOCALE = "en_US"
_occupation_cache: dict[str, dict[str, Any]] = {}
# Posting conditions of every occupation locale (contracts, diplomas, salaries...).
_CONDITIONS_PATH = os.path.join(_DATA_DIR, "conditions.json")
_conditions_cache: dict[str, Any] | None = None


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

    Fields missing from the source data (e.g. no state outside the US, no
    CEO for some companies) are None."""

    company: str
    sector: str | None
    industry: str | None
    city: str | None
    state: str | None
    zip: str | None
    website: str | None
    ticker: str | None
    ceo: str | None


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
    job boards and benefits; those of the United States in the locales
    without conditions of their own (en_GB, nl_NL...). The job title reads
    "Conducteur de poids lourd (H/F)" in French, "Busfahrer (m/w/d)" in
    German, "autista di autobus (m/f)" in Italian (Spanish keeps both forms).
    `seniority` is 'junior', 'mid' or 'senior', from the experience asked.

    In French locales the company is made up by the Faker locale, in the
    occupation's sector: `company_naf` is its NAF rév. 2 activity code
    (e.g. '86.10Z'), whose label is the company's `industry`. Elsewhere it
    is made up the same way without NAF code in German, Spanish and Italian
    locales; in the other locales it is one of the Kaggle companies of the
    occupation's sector (`company_sector`), or, when none is in that sector,
    a name made up by the Faker locale with every other profile field None
    and `company_sector` None. `company_naf` is None outside French locales."""

    job_id: int
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
    7) or 'senior' (8 and more)."""

    occupation: OccupationRecord
    job_id: int
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


def _load_data() -> dict[str, Any]:
    global _data_cache
    if _data_cache is None:
        with open(_DATA_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        _data_cache = _build_index(raw)
    return _data_cache


def _load_cities() -> dict[str, Any]:
    """{lowercase country: {"country": name, "cities": rows, "cum_weights":
    cumulative populations, or None for a uniform pick}}; a row is [English
    name, latitude, longitude, population, local name (France, Germany,
    Spain, Italy only)]."""
    global _cities_cache
    if _cities_cache is None:
        with gzip.open(_CITIES_PATH, "rt", encoding="utf-8") as f:
            raw = json.load(f)
        _cities_cache = {
            country.lower(): {
                "country": country,
                "cities": entry["cities"],
                "cum_weights": None if any(row[3] is None for row in entry["cities"])
                else list(itertools.accumulate(row[3] for row in entry["cities"])),
            }
            for country, entry in raw["countries"].items()
        }
    return _cities_cache


def _build_index(raw: dict[str, Any]) -> dict[str, Any]:
    """Lookups on the Kaggle companies."""
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for company in raw["companies"]:
        if company["sector"]:
            by_sector.setdefault(company["sector"], []).append(company)

    return {
        **raw,
        "company_by_name": {company["company"].lower(): company for company in raw["companies"]},
        "companies_by_sector": by_sector,
        "sector_by_name": {sector.lower(): sector for sector in by_sector},
    }


def _load_conditions() -> dict[str, Any]:
    global _conditions_cache
    if _conditions_cache is None:
        with open(_CONDITIONS_PATH, encoding="utf-8") as f:
            _conditions_cache = json.load(f)
    return _conditions_cache


def _load_occupations(locale: str) -> dict[str, Any]:
    if locale not in _occupation_cache:
        with gzip.open(os.path.join(_DATA_DIR, f"occupations_{locale}.json.gz"), "rt", encoding="utf-8") as f:
            raw = json.load(f)
        raw["conditions"] = _load_conditions()[locale]
        _occupation_cache[locale] = _build_occupation_index(raw)
    return _occupation_cache[locale]


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
        # Kaggle companies by sector (used in English only: see _local_companies).
        "companies_by_sector": raw.get("companies_by_sector", {}),
        "conditions": raw["conditions"],
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
    Italian; else English."""
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

    return str(salary_format["template"].format(min=amount(low), max=amount(high)))


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
    def _data(self) -> dict[str, Any]:
        return _load_data()

    @property
    def _occupations(self) -> dict[str, Any]:
        locale = self.occupations_locale
        if locale is None:
            locale = _occupation_locale(_generator_locale(self.generator))
        elif locale not in OCCUPATION_LOCALES:
            raise ValueError(f"occupations_locale must be one of {OCCUPATION_LOCALES}, got {locale!r}")
        return _load_occupations(locale)

    def _local_conditions(self) -> dict[str, Any]:
        """The posting conditions of the occupation data: French, German,
        Spanish, Italian, or those of the United States for every locale
        using the English data (en_US, en_GB, nl_NL...)."""
        conditions: dict[str, Any] = self._occupations["conditions"]
        return conditions

    def _local_companies(self) -> bool:
        """True where companies are made up by the Faker locale (German,
        Spanish, French and Italian data); False where they come from the
        Kaggle companies (English data)."""
        return bool(self._occupations["meta"]["language"] != "en")

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
        """list: every country a job can be located in (216), sorted, with
        the English names of `job_location(country=...)` ('France', 'USA'...)."""
        return sorted(entry["country"] for entry in _load_cities().values())

    def job_location(self, country: str | None = None) -> LocationRecord:
        """Return a random job location (city, country and coordinates), in
        the locale's country by default (the United States for locales
        without conditions of their own), or in the given `country` (see
        `job_countries`).

        Cities are those of 15,000 inhabitants or more (GeoNames), picked in
        proportion to their population: Paris comes up more often than
        Annecy. Their names are in English ('Munich'), except in the
        locale's own country for German, Spanish, French and Italian
        locales ('München', 'Deutschland')."""
        return self._local_location(self._local_conditions(), country)

    def _local_location(self, conditions: dict[str, Any], country: str | None) -> LocationRecord:
        """A location, in the locale's country by default (its local name is
        accepted too), with the local names of the country and its cities."""
        local_country = (conditions.get("place_names") or {}).get("country", conditions["country"])
        if country is None or str(country).strip().lower() == local_country.lower():
            country = conditions["country"]
        local = country == conditions["country"]
        return self._city(country, local_country if local else None)

    def _city(self, country: str, local_country: str | None = None) -> LocationRecord:
        """A city of `country`, picked by population; with `local_country`,
        the local names of the city and the country."""
        entry = _load_cities().get(str(country).strip().lower())
        if entry is None:
            similar = _suggest_similar(country, self.job_countries)
            msg = f"Unknown country: {country!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            raise ValueError(msg)
        rng = self.generator.random
        if entry["cum_weights"] is None:
            row = rng.choice(entry["cities"])
        else:
            row = rng.choices(entry["cities"], cum_weights=entry["cum_weights"])[0]
        local = local_country is not None and len(row) > 4
        return {
            "city": row[4] if local else row[0],
            "country": local_country if local_country is not None else entry["country"],
            "latitude": row[1],
            "longitude": row[2],
        }

    # -- companies --------------------------------------------------------------

    @property
    def job_sectors(self) -> list[str]:
        """list: every company sector, sorted: those of the Kaggle companies
        (e.g. 'Financial Services') in English locales, the activity sectors
        (see `job_activity_sectors`) where companies are made up."""
        if self._local_companies():
            return self.job_activity_sectors
        return sorted(self._data["companies_by_sector"])

    @property
    def job_companies(self) -> list[str]:
        """list: every company name of the Kaggle data (e.g. '3M'), sorted.
        German, Spanish, French and Italian locales make their company names
        up (see `job_company`)."""
        return sorted([c["company"] for c in self._data["companies"]])

    def _pick_company(self, company: str | None = None, sector: str | None = None) -> dict[str, Any]:
        if company is not None:
            found = self._data["company_by_name"].get(str(company).strip().lower())
            if found is None:
                similar = _suggest_similar(company, self._data["company_by_name"].keys())
                msg = f"Unknown company: {company!r}"
                if similar:
                    msg += f". Did you mean: {', '.join(similar)}?"
                raise ValueError(msg)
            return found
        if sector is None:
            return self.random_element(self._data["companies"])
        name = self._data["sector_by_name"].get(str(sector).strip().lower())
        if name is None:
            similar = _suggest_similar(sector, self._data["companies_by_sector"].keys())
            sectors = sorted(self._data["companies_by_sector"].keys())
            msg = f"Unknown sector: {sector!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            else:
                msg += f". Available sectors: {', '.join(sectors[:5])}..."
            raise ValueError(msg)
        return self.random_element(self._data["companies_by_sector"][name])

    def job_company(self, sector: str | None = None) -> str:
        """Return a random hiring company name, optionally restricted to a
        sector (see `job_sectors`), as `job_company_profile`.

        Not named `company` so as not to shadow Faker's own `company()`."""
        return self.job_company_profile(sector=sector)["company"]

    def job_company_profile(self, company: str | None = None, sector: str | None = None) -> CompanyProfile:
        """Return the profile of a hiring company.

        English locales: a Kaggle company (the given one, or a random one,
        optionally of a sector): sector, industry, headquarters
        city/state/zip, website, ticker and CEO.

        German, Spanish, French and Italian locales: a company made up by
        the Faker locale (or named `company`), in an activity sector
        (`sector`, else a random one), with a city of the country and a CEO;
        in French locales, a NAF activity of the sector as `industry`. No
        state, zip, website or ticker."""
        if self._local_companies():
            conditions = self._local_conditions()
            name = self._resolve_activity_sector(sector) if sector is not None else self.job_activity_sector()
            return self._local_company(name, conditions, self.job_location(), company)
        return self._kaggle_company_profile(company, sector)

    def _kaggle_company_profile(self, company: str | None = None, sector: str | None = None) -> CompanyProfile:
        found = self._pick_company(company=company, sector=sector)
        return {
            "company": found["company"],
            "sector": found["sector"],
            "industry": found["industry"],
            "city": found["city"],
            "state": found["state"],
            "zip": found["zip"],
            "website": found["website"],
            "ticker": found["ticker"],
            "ceo": found["ceo"],
        }

    def job_company_size(self) -> int:
        """Return a random company size (number of employees)."""
        return self.random_int(*self._data["ranges"]["company_size"])

    # -- occupations (ROME 4.0 / ESCO, locale-aware) -----------------------------

    @property
    def job_activity_sectors(self) -> list[str]:
        """list: every activity sector of the occupations (35, e.g.
        'Healthcare', or 'Santé' in French locales), sorted.

        Not the same list as `job_sectors`, the sectors of the companies."""
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

    def _occupation_company(self, sector: str) -> tuple[CompanyProfile, str | None]:
        """A company of `sector` and that sector, else a company name from the
        Faker locale and None. Only the given sector: the secondary sectors of
        an occupation would give odd matches (a nuclear decontamination
        worker at an oil company)."""
        companies = self._occupations["companies_by_sector"].get(sector)
        if companies:
            return self._kaggle_company_profile(company=self.random_element(companies)), sector
        return {
            "company": self.generator.company(),
            "sector": None, "industry": None, "city": None, "state": None,
            "zip": None, "website": None, "ticker": None, "ceo": None,
        }, None

    def job_occupation_posting(
        self,
        code: str | None = None,
        sector: str | None = None,
        country: str | None = None,
        skills: int = 5,
        weighted: bool = True,
    ) -> OccupationPosting:
        """Return a full random job posting built on an occupation (see
        `OccupationPosting`), in the language of the Faker locale.

        - `code` / `sector` choose the occupation (see `job_occupation_record`).
        - The hiring company is in the occupation's sector (the requested
          one, else its main one): made up by the Faker locale in German,
          Spanish, French and Italian locales (with a NAF activity of that
          sector in French ones); else a Kaggle company of that sector, or a
          name made up by the Faker locale when none is in it.
        - `skills`: how many of the occupation's skills to list (default 5).
        - `country` sets the job location (default: the locale's country,
          the United States for locales without conditions of their own).
        - `weighted` picks the occupation by demand (see `job_occupation`).

        Local conditions (French, German, Spanish and Italian locales; US
        conditions for every other one):
        benefits, job boards and default diplomas are hand-made and
        illustrative (scripts/posting_conditions.py); the contract comes
        from a national mix adapted to the occupation's ISCO major group
        (Eurostat LFS shares of temporary, part-time and self-employed
        workers; not for the United States), with a "CDD saisonnier" at the
        occupation's `seasonal` share in French locales; the experience
        asked follows the occupation's skill level (ISCO major group), and
        the salary comes from official mean earnings: Eurostat SES 2022 by
        ISCO major group and NACE section (France, Germany, Spain, Italy),
        BLS OEWS by SOC major group (United States), adjusted to the
        experience asked (earnings by age), to the contract (internships,
        apprenticeships, part-time) and kept above the minimum wage. ROME
        diplomas come first in French locales.
        """
        _check_count("skills", skills)
        occupation = self.job_occupation_record(code=code, sector=sector, weighted=weighted)
        return self._occupation_posting(occupation, country, skills)

    def _occupation_posting(self, occupation: OccupationRecord, country: str | None, skills: int) -> OccupationPosting:
        conditions = self._local_conditions()
        company_naf: str | None = None
        company_sector: str | None
        terms = self._local_terms(occupation, conditions, country)
        if terms["naf"] is not None:
            company = self._local_company(occupation["sector"], conditions, terms["location"], naf=terms["naf"])
            company_sector, company_naf = occupation["sector"], terms["naf"][0]
        elif self._local_companies():
            # German, Spanish, Italian: a company of the locale, not an American Kaggle one.
            company = self._local_company(occupation["sector"], conditions, terms["location"])
            company_sector = occupation["sector"]
        else:
            company, company_sector = self._occupation_company(occupation["sector"])
        job_title = occupation["job_title"]
        style = self._occupations["gender"]
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
            "salary_range": terms["salary_range"],
            "salary_min": terms["salary_min"],
            "salary_max": terms["salary_max"],
            "salary_currency": terms["salary_currency"],
            "work_type": terms["work_type"],
            "benefits": terms["benefits"],
            "location": terms["location"],
            "company": company,
            "company_sector": company_sector,
            "company_naf": company_naf,
            "company_size": self.job_company_size(),
            "seniority": _seniority(terms["experience_min"]),
            "job_portal": terms["job_portal"],
            "job_posting_date": self.job_posting_date(),
            "contact_person": self.generator.name(),
            "contact": self.generator.phone_number(),
        }

    def _local_company(
        self, sector: str, conditions: dict[str, Any], location: LocationRecord, name: str | None = None,
        naf: list[str] | None = None,
    ) -> CompanyProfile:
        """A company made up by the Faker locale (or named `name`) in
        `sector`, in the city of the posting; in French locales with a NAF
        rév. 2 activity of the sector (`naf`, else a random one) as industry."""
        if naf is None and "naf_by_sector" in conditions:
            naf = self.random_element(conditions["naf_by_sector"][sector])
        return {
            "company": name if name is not None else self.generator.company(),
            "sector": sector, "industry": naf[1] if naf else None, "city": location["city"], "state": None,
            "zip": None, "website": None, "ticker": None, "ceo": self.generator.name(),
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
        step = 1000 if center >= 100_000 else 500
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
        level, a salary from the earnings of its ISCO group, local benefits
        and job boards; in French locales, the NAF activity of the company."""
        level = conditions["skill_levels"][occupation["isco_group"]]
        contracts = conditions["contracts"]
        contract = self._local_contract(occupation, conditions)
        spec = contracts[contract]
        experience_min, experience_max = self._local_experience(level, spec["max_experience"], conditions)
        naf = None
        if "naf_by_sector" in conditions:
            naf = self.random_element(conditions["naf_by_sector"][occupation["sector"]])
            section = naf[2]
        else:
            section = conditions["section_by_sector"].get(occupation["sector"])
        salary_min, salary_max = self._local_salary(
            occupation["isco_group"], section, (experience_min, experience_max), spec, conditions)
        portals = conditions["job_portals"]
        if occupation["qualifications"]:
            qualification = self.random_element(occupation["qualifications"])
        else:
            qualification = self._default_qualification(conditions, level, occupation["sector"])
        return {
            "qualification": qualification,
            "experience": _local_experience_text(conditions, experience_min, experience_max),
            "experience_min": experience_min,
            "experience_max": experience_max,
            "salary_range": _local_salary_text(conditions, salary_min, salary_max),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": conditions["currency"],
            "work_type": contract,
            "benefits": self._local_benefits(occupation, conditions, contract),
            "location": self._local_location(conditions, country),
            "job_portal": self.random_element(
                portals["all"] + (portals.get("executive", []) if occupation["executive"] else [])),
            "naf": naf,
        }

    # -- postings ---------------------------------------------------------------

    def job_id(self) -> int:
        """Return a random job posting id (a 15 or 16-digit number, as in the source data)."""
        return self.random_int(10**14, 10**16 - 1)

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
        return self._occupation_job_posting(self._occupation_posting(occupation, country, 5))

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
        language of the occupation data (French, English, German, Spanish or
        Italian), so render a posting with a provider of the locale that made
        it. `markdown=True` gives Markdown headings, bold and bullets; else
        plain text with upper-case headings.

        The wording is hand-made, with a few phrasings per section picked at
        random (reproducible with `Faker.seed()`); every fact comes from the
        posting."""
        from faker_jobs.posting_text import render_posting

        if posting is None:
            posting = self.job_occupation_posting()
        return render_posting(posting, self._occupations["meta"]["language"], self.generator.random, markdown)

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
        }
