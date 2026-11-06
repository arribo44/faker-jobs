"""
Faker Jobs Provider

A custom Faker provider for simulating job postings: job titles and roles
(with their description, skills and responsibilities), qualifications,
experience and salary ranges, work types, benefits, job portals, hiring
companies with their profile, locations, contacts and full job postings.

The data comes from the "Job Description Dataset" (Kaggle, ~1.6M synthetic
postings): 147 job titles, 376 roles, 888 companies, 216 locations (one city
per country, geocoded). Roles are picked in proportion to how often they are
posted in that dataset. Contact names and phone numbers come from the Faker
locale, so they are localized; everything else is in English.

The `job_occupation*` and `job_activity_sector*` methods use a second,
locale-aware source: the 1,923 job sheets of the French ROME 4.0 directory
(France Travail) for French locales, and the ~2,000 ESCO occupations mapped
to them (European Commission) for every other locale. Each occupation comes
with its job titles, activity sectors, skills, knowledge and soft skills.
"""
import difflib
import datetime as _datetime
import itertools
import json
import os
from typing import Any, TypedDict

from faker.providers import BaseProvider

__version__ = "0.1.0"

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_DATA_PATH = os.path.join(_DATA_DIR, "jobs_data.json")
_data_cache: dict[str, Any] | None = None

# Locales with their own occupation data; every other locale uses the first.
OCCUPATION_LOCALES = ("en_US", "fr_FR")
_occupation_cache: dict[str, dict[str, Any]] = {}


def _suggest_similar(value: str, options: list[str], n: int = 3) -> list[str]:
    """Suggest similar values using fuzzy matching."""
    return difflib.get_close_matches(
        value.lower(),
        [o.lower() for o in options],
        n=n,
        cutoff=0.6
    )


class RoleRecord(TypedDict):
    """A role, as returned by `JobsProvider.job_role_record()`."""

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
    the others an ESCO occupation (`code` is its ESCO concept id).
    `job_title` is one of its job titles, picked at random; `sector` is the
    requested sector, or else its main one. `description` is None for ROME
    sheets (the source has none).

    From ROME (for an ESCO occupation, from the ROME sheet holding most of
    its job titles): `executive` (a "cadre" job), `regulated` (a regulated
    profession), `riasec` (Holland codes, major first, e.g. ['R', 'C']) and
    `transitions` (any of 'ecological', 'digital', 'demographic': jobs
    ROME flags as part of that transition). `qualifications` are the French
    diplomas listed by the ROME sheet (CAP, Bac pro, BTS, Master...); empty
    for ESCO occupations."""

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


class OccupationPosting(TypedDict):
    """A job posting built on an occupation, as returned by
    `JobsProvider.job_occupation_posting()`.

    `job_title`, `skills` and the company follow the occupation and its
    sector. In French locales the conditions are French (contract type in
    `work_type`, yearly gross salary in EUR, French diplomas, a place in
    France, French job boards) and the job title reads "Conducteur de
    poids lourd (H/F)"; in other locales they are drawn as in `JobPosting`
    (salaries in USD, from the Kaggle data). `company_sector` is the
    activity sector the company was picked from, or None when no packaged
    company is in the occupation's sectors: the company is then a name made
    up by the Faker locale, with every other profile field None."""

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
    company_size: int
    job_portal: str
    job_posting_date: _datetime.date
    contact_person: str
    contact: str


class JobPosting(TypedDict):
    """A full job posting, as returned by `JobsProvider.job_posting()`.

    Salaries are yearly amounts in `salary_currency` (USD, as in the source
    data); `salary_range` is their compact text form ("$59K-$104K")."""

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


def _build_index(raw: dict[str, Any]) -> dict[str, Any]:
    roles = raw["roles"]
    by_title: dict[str, list[dict[str, Any]]] = {}
    for role in roles:
        by_title.setdefault(role["job_title"], []).append(role)

    def cum_weights(rows: list[dict[str, Any]]) -> list[int]:
        # Popularity weight = number of postings for the role in the source data.
        return list(itertools.accumulate(row["posting_count"] for row in rows))

    title_weights = [sum(role["posting_count"] for role in by_title[title]) for title in raw["job_titles"]]
    by_sector: dict[str, list[dict[str, Any]]] = {}
    for company in raw["companies"]:
        if company["sector"]:
            by_sector.setdefault(company["sector"], []).append(company)

    return {
        **raw,
        "role_by_name": {role["role"].lower(): role for role in roles},
        "title_by_name": {title.lower(): title for title in raw["job_titles"]},
        "roles_by_title": by_title,
        # Cumulative weights, parallel to the lists above, for O(log n)
        # weighted picks with random.choices(cum_weights=...).
        "cum_weights": cum_weights(roles),
        "cum_weights_by_title": {title: cum_weights(rows) for title, rows in by_title.items()},
        "title_cum_weights": list(itertools.accumulate(title_weights)),
        "locations_by_country": {
            country.lower(): list(locations)
            for country, locations in itertools.groupby(
                sorted(raw["locations"], key=lambda x: x["country"]), key=lambda x: x["country"]
            )
        },
        "company_by_name": {company["company"].lower(): company for company in raw["companies"]},
        "companies_by_sector": by_sector,
        "sector_by_name": {sector.lower(): sector for sector in by_sector},
    }


def _load_occupations(locale: str) -> dict[str, Any]:
    if locale not in _occupation_cache:
        with open(os.path.join(_DATA_DIR, f"occupations_{locale}.json"), encoding="utf-8") as f:
            raw = json.load(f)
        _occupation_cache[locale] = _build_occupation_index(raw)
    return _occupation_cache[locale]


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
    return {
        "meta": raw["meta"],
        "sectors": sorted(raw["sectors"]),
        "occupations": occupations,
        "occupation_by_code": {occupation["code"].lower(): occupation for occupation in occupations},
        "occupations_by_sector": by_sector,
        "sector_by_name": {sector.lower(): sector for sector in raw["sectors"]},
        "companies_by_sector": raw["companies_by_sector"],
        "conditions": raw.get("conditions"),
        "gendered_titles": raw["meta"]["language"] == "fr",
    }


def _gender_form(title: str, gender: str) -> str:
    """The masculine ('M') or feminine ('F') form of a French ROME job title
    written with both, e.g. "Conducteur / Conductrice d'engins agricoles"
    -> "Conducteur d'engins agricoles" / "Conductrice d'engins agricoles".

    The words before " / " are the masculine form; they match as many words
    after it, which are the feminine one; the rest is common to both. Words
    before the first gendered one are common too ("Garde forestier /
    Forestière"). Titles in another shape (no or several " / ") are
    returned unchanged."""
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
    """The occupation data used for a Faker locale: French for 'fr', 'fr_FR', 'fr_CA'..., else English."""
    if locale and locale.replace("-", "_").split("_")[0].lower() == "fr":
        return "fr_FR"
    return OCCUPATION_LOCALES[0]


def _check_count(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


class JobsProvider(BaseProvider):
    """Provider for generating job-market related data.

    Every method is prefixed with `job_` so as not to shadow Faker's own
    `job()` (a random job title from Faker's job provider) or `company()`.
    """

    #: Force the occupation data ('en_US' or 'fr_FR') whatever the Faker
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

    # -- lookup helpers ---------------------------------------------------------

    def _resolve_title(self, job_title: str | None) -> str | None:
        if job_title is None:
            return None
        title = self._data["title_by_name"].get(str(job_title).strip().lower())
        if title is None:
            similar = _suggest_similar(job_title, self._data["title_by_name"].keys())
            msg = f"Unknown job title: {job_title!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            raise ValueError(msg)
        return title

    def _find_role(self, role: str) -> dict[str, Any]:
        found = self._data["role_by_name"].get(str(role).strip().lower())
        if found is None:
            similar = _suggest_similar(role, self._data["role_by_name"].keys())
            msg = f"Unknown role: {role!r}"
            if similar:
                msg += f". Did you mean: {', '.join(similar)}?"
            raise ValueError(msg)
        return found

    def _pick_role(
        self, job_title: str | None = None, role: str | None = None, weighted: bool = True
    ) -> dict[str, Any]:
        title = self._resolve_title(job_title)
        if role is not None:
            found = self._find_role(role)
            if title is not None and found["job_title"] != title:
                raise ValueError(f"Role {role!r} does not belong to job title {job_title!r}")
            return found
        if title is None:
            rows, cum_weights = self._data["roles"], self._data["cum_weights"]
        else:
            rows, cum_weights = self._data["roles_by_title"][title], self._data["cum_weights_by_title"][title]
        if weighted:
            return self.generator.random.choices(rows, cum_weights=cum_weights)[0]
        return self.generator.random.choice(rows)

    # -- job titles / roles -----------------------------------------------------

    @property
    def job_titles(self) -> list[str]:
        """list: every job title (e.g. 'Software Engineer'), sorted."""
        return self._data["job_titles"]

    def job_title(self, weighted: bool = True) -> str:
        """Return a random job title (e.g. 'Software Engineer'), a family of
        roles. By default titles are picked in proportion to how often they
        are posted in the source data; `weighted=False` picks uniformly.

        Not to be confused with Faker's own `job()`, unrelated to this provider."""
        if weighted:
            return self.generator.random.choices(self.job_titles, cum_weights=self._data["title_cum_weights"])[0]
        return self.generator.random.choice(self.job_titles)

    def job_role(self, job_title: str | None = None, weighted: bool = True) -> str:
        """Return a random role (e.g. 'Frontend Web Developer'), optionally
        restricted to a job title (e.g. 'Web Developer'). `weighted` works
        as in `job_title`."""
        return self._pick_role(job_title=job_title, weighted=weighted)["role"]

    def job_role_record(
        self, job_title: str | None = None, role: str | None = None, weighted: bool = True
    ) -> RoleRecord:
        """Return a dict describing a random role (or the given `role`): its
        job title, description, skills and responsibilities."""
        found = self._pick_role(job_title=job_title, role=role, weighted=weighted)
        return {
            "job_title": found["job_title"],
            "role": found["role"],
            "description": found["description"],
            "skills": found["skills"],
            "responsibilities": found["responsibilities"],
        }

    def job_description(self, role: str | None = None) -> str:
        """Return the description of the given role, or of a random one."""
        return self._pick_role(role=role)["description"]

    def job_skills(self, role: str | None = None) -> str:
        """Return the skills of the given role, or of a random one."""
        return self._pick_role(role=role)["skills"]

    def job_responsibilities(self, role: str | None = None) -> str:
        """Return the responsibilities of the given role, or of a random one."""
        return self._pick_role(role=role)["responsibilities"]

    # -- qualifications / experience / salary -----------------------------------

    def job_qualification(self, full_name: bool = False) -> str:
        """Return a random qualification code (e.g. 'MBA'), or its full
        name ('Master of Business Administration') if `full_name` is true."""
        code = self.random_element(list(self._data["qualifications"]))
        return self._data["qualifications"][code] if full_name else code

    def job_qualification_name(self, code: str) -> str:
        """Return the full name of a qualification code (e.g. 'MBA')."""
        for known, name in self._data["qualifications"].items():
            if known.lower() == str(code).strip().lower():
                return name
        similar = _suggest_similar(code, self._data["qualifications"].keys())
        msg = f"Unknown qualification: {code!r}"
        if similar:
            msg += f". Did you mean: {', '.join(similar)}?"
        raise ValueError(msg)

    def job_experience_range(self) -> tuple[int, int]:
        """Return a random (min, max) years-of-experience range, e.g. (2, 12)."""
        ranges = self._data["ranges"]
        low = self.random_int(*ranges["experience_min"])
        high = self.random_int(*ranges["experience_max"])
        return low, high

    def job_experience(self) -> str:
        """Return a random experience requirement, e.g. '2 to 12 Years'."""
        return "{} to {} Years".format(*self.job_experience_range())

    def job_salary_bounds(self) -> tuple[int, int]:
        """Return a random (min, max) yearly salary range in USD, e.g. (59000, 104000)."""
        ranges = self._data["ranges"]
        low = self.random_int(*ranges["salary_min_k"])
        high = self.random_int(*ranges["salary_max_k"])
        return low * 1000, high * 1000

    def job_salary_range(self) -> str:
        """Return a random yearly salary range, e.g. '$59K-$104K'."""
        return self._format_salary(*self.job_salary_bounds())

    @staticmethod
    def _format_salary(low: int, high: int) -> str:
        return f"${low // 1000}K-${high // 1000}K"

    # -- work type / benefits / portals -----------------------------------------

    def job_work_type(self) -> str:
        """Return a random work type: 'Full-Time', 'Part-Time', 'Contract', 'Temporary' or 'Intern'."""
        return self.random_element(self._data["work_types"])

    def job_benefits(self, count: int | None = None, weighted: bool = True) -> list[str]:
        """Return `count` distinct benefits (default: 5, as in every source
        posting), e.g. ['Health Insurance', 'Parental Leave', ...].

        By default benefits are picked in proportion to how often they are
        offered in the source data; `weighted=False` picks uniformly."""
        if count is None:
            count = self._data["meta"]["benefits_per_posting"]
        _check_count("count", count)
        benefits = self._data["benefits"]
        if count > len(benefits):
            raise ValueError(f"count must be at most {len(benefits)}, got {count!r}")
        rng = self.generator.random
        if not weighted:
            return rng.sample(list(benefits), count)
        # Weighted sampling without replacement: draw, then drop the winner.
        remaining = dict(benefits)
        picked: list[str] = []
        for _ in range(count):
            benefit = rng.choices(list(remaining), weights=list(remaining.values()))[0]
            picked.append(benefit)
            del remaining[benefit]
        return picked

    def job_portal(self) -> str:
        """Return a random job portal or staffing agency (e.g. 'Indeed', 'Randstad')."""
        return self.random_element(self._data["job_portals"])

    # -- locations --------------------------------------------------------------

    @property
    def job_countries(self) -> list[str]:
        """list: every country a job can be located in."""
        return [location["country"] for location in self._data["locations"]]

    def job_location(self, country: str | None = None) -> LocationRecord:
        """Return a random job location (city, country and coordinates), or
        a random one from the given `country`."""
        if country is None:
            location = self.random_element(self._data["locations"])
        else:
            locations = self._data["locations_by_country"].get(str(country).strip().lower())
            if locations is None:
                countries = sorted({loc["country"] for loc in self._data["locations"]})
                similar = _suggest_similar(country, countries)
                msg = f"Unknown country: {country!r}"
                if similar:
                    msg += f". Did you mean: {', '.join(similar)}?"
                raise ValueError(msg)
            location = self.random_element(locations)
        return {
            "city": location["city"],
            "country": location["country"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        }

    # -- companies --------------------------------------------------------------

    @property
    def job_sectors(self) -> list[str]:
        """list: every company sector (e.g. 'Financial Services'), sorted."""
        return sorted(self._data["companies_by_sector"])

    @property
    def job_companies(self) -> list[str]:
        """list: every company name (e.g. '3M'), sorted."""
        return sorted([c["company"] for c in self._data["companies"]])

    @property
    def job_roles(self) -> list[str]:
        """list: every role name (e.g. 'Frontend Web Developer'), sorted."""
        return sorted([r["role"] for r in self._data["roles"]])

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
        sector (see `job_sectors`).

        Not named `company` so as not to shadow Faker's own `company()`."""
        return self._pick_company(sector=sector)["company"]

    def job_company_profile(self, company: str | None = None, sector: str | None = None) -> CompanyProfile:
        """Return the profile of the given company, or of a random one
        (optionally restricted to a sector): sector, industry, headquarters
        city/state/zip, website, ticker and CEO."""
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

    def _pick_occupation(self, code: str | None = None, sector: str | None = None) -> dict[str, Any]:
        data = self._occupations
        if code is not None:
            found = data["occupation_by_code"].get(str(code).strip().lower())
            if found is None:
                raise ValueError(f"Unknown occupation code: {code!r} (see job_occupation_codes)")
            if sector is not None and self._resolve_activity_sector(sector) not in found["sectors"]:
                raise ValueError(f"Occupation {code!r} is not in activity sector {sector!r}")
            return found
        if sector is None:
            return self.random_element(data["occupations"])
        return self.random_element(data["occupations_by_sector"][self._resolve_activity_sector(sector)])

    def job_activity_sector(self) -> str:
        """Return a random activity sector (see `job_activity_sectors`)."""
        return self.random_element(self._occupations["sectors"])

    def job_occupation(self, sector: str | None = None) -> str:
        """Return the name of a random occupation (e.g. 'nurse responsible
        for general care', 'Infirmier / Infirmière de soins généraux' in
        French locales), optionally from an activity sector."""
        return self._pick_occupation(sector=sector)["title"]

    def job_occupation_title(self, sector: str | None = None, gender: str | None = None) -> str:
        """Return a random job title (one of the ~14,000 ROME or ESCO job
        titles), optionally from an activity sector.

        French titles name both forms ("Conducteur / Conductrice de bus"),
        as ROME does; `gender='M'` or `'F'` gives only the masculine or
        feminine one. English titles are not gendered: `gender` is ignored."""
        if gender not in (None, "M", "F"):
            raise ValueError(f"gender must be None, 'M' or 'F', got {gender!r}")
        title = self.random_element(self._pick_occupation(sector=sector)["titles"])
        if gender is not None and self._occupations["gendered_titles"]:
            return _gender_form(title, gender)
        return title

    def job_occupation_record(self, code: str | None = None, sector: str | None = None) -> OccupationRecord:
        """Return a dict describing the given occupation (by `code`) or a
        random one, optionally from an activity sector: its name, a job
        title, domain, sectors, description, skills, knowledge and soft skills."""
        found = self._pick_occupation(code=code, sector=sector)
        return {
            "code": found["code"],
            "title": found["title"],
            "job_title": self.random_element(found["titles"]),
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
        }

    def job_occupation_skills(
        self, code: str | None = None, count: int = 5, sector: str | None = None
    ) -> list[str]:
        """Return `count` distinct skills of the given occupation (by `code`)
        or of a random one (optionally from an activity sector), e.g.
        ['administer medication', ...]. Returns all of them when the
        occupation has fewer than `count`."""
        _check_count("count", count)
        skills = self._pick_occupation(code=code, sector=sector)["skills"]
        return self.generator.random.sample(skills, min(count, len(skills)))

    def _occupation_company(self, sectors: list[str]) -> tuple[CompanyProfile, str | None]:
        """A company from the first of `sectors` that has some, and that sector;
        else a company name from the Faker locale and None."""
        by_sector = self._occupations["companies_by_sector"]
        for sector in sectors:
            if by_sector.get(sector):
                return self.job_company_profile(company=self.random_element(by_sector[sector])), sector
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
          one, else its main one, else its other sectors), or made up by
          the Faker locale when no packaged company fits.
        - `skills`: how many of the occupation's skills to list (default 5).
        - `country` sets the job location (default: France in French
          locales, anywhere otherwise).
        - `weighted` applies to the Kaggle benefits (non-French locales).

        In French locales the conditions are French and illustrative
        (contract, yearly gross salary in EUR by executive status, a diploma
        from the ROME sheet, French benefits and job boards); otherwise they
        come from the Kaggle data, in English.
        """
        _check_count("skills", skills)
        occupation = self.job_occupation_record(code=code, sector=sector)
        company_sectors = [occupation["sector"]] + [s for s in occupation["sectors"] if s != occupation["sector"]]
        company, company_sector = self._occupation_company(company_sectors)
        conditions = self._occupations["conditions"]
        if conditions is None:
            job_title = occupation["job_title"]
            terms = self._kaggle_terms(country, weighted)
        else:
            job_title = _gender_form(occupation["job_title"], "M") + " (H/F)"
            terms = self._french_terms(occupation, conditions, country)
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
            "company_size": self.job_company_size(),
            "job_portal": terms["job_portal"],
            "job_posting_date": self.job_posting_date(),
            "contact_person": self.generator.name(),
            "contact": self.generator.phone_number(),
        }

    def _kaggle_terms(self, country: str | None, weighted: bool) -> dict[str, Any]:
        """Posting conditions from the Kaggle data (as in `job_posting`)."""
        experience_min, experience_max = self.job_experience_range()
        salary_min, salary_max = self.job_salary_bounds()
        return {
            "qualification": self.job_qualification(),
            "experience": f"{experience_min} to {experience_max} Years",
            "experience_min": experience_min,
            "experience_max": experience_max,
            "salary_range": self._format_salary(salary_min, salary_max),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": self._data["meta"]["salary_currency"],
            "work_type": self.job_work_type(),
            "benefits": self.job_benefits(weighted=weighted),
            "location": self.job_location(country=country),
            "job_portal": self.job_portal(),
        }

    def _french_terms(
        self, occupation: OccupationRecord, conditions: dict[str, Any], country: str | None
    ) -> dict[str, Any]:
        """Illustrative French posting conditions (see CONDITIONS_FR in scripts/build_occupations.py)."""
        rng = self.generator.random
        level = "executive" if occupation["executive"] else "other"

        def bounds(spec: dict[str, list[int]]) -> tuple[int, int]:
            low = self.random_int(*spec["low"])
            return low, low + self.random_int(*spec["gap"])

        experience_min, experience_max = bounds(conditions["experience"][level])
        salary_low_k, salary_high_k = bounds(conditions["salary_k"][level])
        contracts = conditions["contracts"]
        qualifications = occupation["qualifications"] or conditions["qualifications"][level]
        portals = conditions["job_portals"]
        return {
            "qualification": self.random_element(qualifications),
            "experience": ("Débutant accepté" if experience_min == 0
                           else f"{experience_min} à {experience_max} ans"),
            "experience_min": experience_min,
            "experience_max": experience_max,
            "salary_range": f"{salary_low_k * 1000:,} € - {salary_high_k * 1000:,} € brut/an".replace(",", " "),
            "salary_min": salary_low_k * 1000,
            "salary_max": salary_high_k * 1000,
            "salary_currency": conditions["currency"],
            "work_type": rng.choices(list(contracts), weights=list(contracts.values()))[0],
            "benefits": rng.sample(conditions["benefits"], conditions["benefits_per_posting"]),
            "location": self.job_location(country=conditions["country"] if country is None else country),
            "job_portal": self.random_element(portals["all"] + (portals["executive"] if level == "executive" else [])),
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
    ) -> JobPosting:
        """Return a full random job posting as a dict (see `JobPosting`).

        - `job_title` / `role` restrict the role (see `job_role_record`).
        - `country` sets the job location (see `job_location`).
        - `sector` restricts the hiring company (see `job_company_profile`).
        - `weighted` (default True) picks popular roles and benefits more
          often; False makes both uniform.

        The contact person and phone number come from the Faker locale.
        """
        found = self._pick_role(job_title=job_title, role=role, weighted=weighted)
        experience_min, experience_max = self.job_experience_range()
        salary_min, salary_max = self.job_salary_bounds()
        return {
            "job_id": self.job_id(),
            "job_title": found["job_title"],
            "role": found["role"],
            "description": found["description"],
            "skills": found["skills"],
            "responsibilities": found["responsibilities"],
            "qualification": self.job_qualification(),
            "experience": f"{experience_min} to {experience_max} Years",
            "experience_min": experience_min,
            "experience_max": experience_max,
            "salary_range": self._format_salary(salary_min, salary_max),
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": self._data["meta"]["salary_currency"],
            "work_type": self.job_work_type(),
            "benefits": self.job_benefits(weighted=weighted),
            "location": self.job_location(country=country),
            "company": self.job_company_profile(sector=sector),
            "company_size": self.job_company_size(),
            "job_portal": self.job_portal(),
            "job_posting_date": self.job_posting_date(),
            "contact_person": self.generator.name(),
            "contact": self.generator.phone_number(),
        }
