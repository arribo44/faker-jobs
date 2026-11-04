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
"""
import datetime as _datetime
import itertools
import json
import os
from typing import Any, TypedDict

from faker.providers import BaseProvider

__version__ = "0.1.0"

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "jobs_data.json")
_data_cache: dict[str, Any] | None = None


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
        "locations_by_country": {loc["country"].lower(): loc for loc in raw["locations"]},
        "company_by_name": {company["company"].lower(): company for company in raw["companies"]},
        "companies_by_sector": by_sector,
        "sector_by_name": {sector.lower(): sector for sector in by_sector},
    }


def _check_count(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


class JobsProvider(BaseProvider):
    """Provider for generating job-market related data.

    Every method is prefixed with `job_` so as not to shadow Faker's own
    `job()` (a random job title from Faker's job provider) or `company()`.
    """

    @property
    def _data(self) -> dict[str, Any]:
        return _load_data()

    # -- lookup helpers ---------------------------------------------------------

    def _resolve_title(self, job_title: str | None) -> str | None:
        if job_title is None:
            return None
        title = self._data["title_by_name"].get(str(job_title).strip().lower())
        if title is None:
            raise ValueError(f"Unknown job title: {job_title!r}")
        return title

    def _find_role(self, role: str) -> dict[str, Any]:
        found = self._data["role_by_name"].get(str(role).strip().lower())
        if found is None:
            raise ValueError(f"Unknown role: {role!r}")
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
        raise ValueError(f"Unknown qualification: {code!r}")

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
        the one of the given `country` (one city per country)."""
        if country is None:
            location = self.random_element(self._data["locations"])
        else:
            location = self._data["locations_by_country"].get(str(country).strip().lower())
            if location is None:
                raise ValueError(f"Unknown country: {country!r}")
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

    def _pick_company(self, company: str | None = None, sector: str | None = None) -> dict[str, Any]:
        if company is not None:
            found = self._data["company_by_name"].get(str(company).strip().lower())
            if found is None:
                raise ValueError(f"Unknown company: {company!r}")
            return found
        if sector is None:
            return self.random_element(self._data["companies"])
        name = self._data["sector_by_name"].get(str(sector).strip().lower())
        if name is None:
            raise ValueError(f"Unknown sector: {sector!r}")
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
