"""
Job datasets: a pool of employers and the postings they publish over a
period, as two tables linked by `company_id` (`JobsProvider.job_dataset()`,
`make_dataset()` for several locales, `python -m faker_jobs export`).

- Employers: `companies` hiring companies of the locale's country (more
  when the postings need a sector that none of them is in: a pool smaller
  than the 35 sectors grows as needed), picked
  as those of the postings (`JobsProvider.job_occupation_posting`): real
  companies (People Data Labs) or made up by the Faker locale, by size
  class from the official shares of jobs; spread between the activity
  sectors in proportion to the demand for their occupations. A company
  keeps its name, city, size and activity in all its postings; companies
  of up to 500 employees hire in their city, larger ones anywhere in the
  country.
- Postings: an occupation picked by demand, then an employer of its
  sector, favouring those whose activity employs the occupation (French
  census, see `job_occupation_posting`), with the conditions of the
  locale's country. Postings by size class therefore follow the official
  shares of jobs, and an employer publishes several of them.
- Lifecycle: a publication date in [`start_date`, `end_date`] (seasonal
  contracts from March to September), a duration on line (log-normal,
  median POSTING_DAYS days), and its status on `end_date`: 'open' (still on
  line, no closing date), else 'filled' (FILLED_SHARE of them) or
  'expired'. A share `repost_rate` of the postings are published again on
  another job board a few days later (`repost_of`: the first one's
  `job_id`), as job boards do: a test case for deduplication.

Reproducible with `Faker.seed()` (or the `seed` of `make_dataset`).
"""
from __future__ import annotations

import csv
import datetime as _datetime
import json
import math
import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict

if TYPE_CHECKING:
    from faker_jobs import JobsProvider

# Median number of days a posting stays on line, and the spread of the durations.
POSTING_DAYS = 30
POSTING_DAYS_SIGMA = 0.6
MIN_POSTING_DAYS = 3
# Share of the closed postings that were filled (the others expired).
FILLED_SHARE = 0.7
# Months of the postings of seasonal contracts (spring and summer, harvests).
SEASONAL_MONTHS = range(3, 10)
# A republication comes this many days after the first one, at most.
MAX_REPOST_DELAY = 14
# Companies of up to this many employees hire in their own city.
SINGLE_SITE_EMPLOYEES = 500


class CompanyRow(TypedDict):
    """A row of `JobDataset.companies`. `real`: a People Data Labs company
    (website, founding year), else made up by the Faker locale."""

    company_id: str
    locale: str
    name: str
    sector: str
    industry: str | None
    activity_code: str | None
    employees: int
    city: str | None
    country: str
    website: str | None
    founded: int | None
    real: bool


class PostingRow(TypedDict):
    """A row of `JobDataset.postings`, flat (lists joined with '; ')."""

    job_id: int
    company_id: str
    locale: str
    job_title: str
    occupation_code: str
    occupation: str
    isco_code: str | None
    isco_group: str
    sector: str
    seniority: str
    work_type: str
    experience_min: int
    experience_max: int
    qualification: str
    salary_min: int
    salary_max: int
    salary_currency: str
    city: str
    country: str
    latitude: float
    longitude: float
    job_portal: str
    posted_date: str
    closed_date: str | None
    status: str
    repost_of: int | None
    skills: str
    benefits: str
    contact_person: str
    contact: str


COMPANY_FIELDS = tuple(CompanyRow.__annotations__)
POSTING_FIELDS = tuple(PostingRow.__annotations__)


@dataclass
class JobDataset:
    """Employers and their postings: `companies` and `postings` are lists of
    rows (see `CompanyRow`, `PostingRow`), linked by `company_id`."""

    companies: list[CompanyRow] = field(default_factory=list)
    postings: list[PostingRow] = field(default_factory=list)

    @classmethod
    def concat(cls, datasets: Iterable[JobDataset]) -> JobDataset:
        """One dataset of several (e.g. of several locales)."""
        result = cls()
        for dataset in datasets:
            result.companies.extend(dataset.companies)
            result.postings.extend(dataset.postings)
        return result

    def to_csv(self, directory: str) -> list[str]:
        """Write companies.csv and postings.csv (UTF-8, header row) in
        `directory` (created if needed); return their paths."""
        return self._write(directory, "csv")

    def to_jsonl(self, directory: str) -> list[str]:
        """Write companies.jsonl and postings.jsonl (one JSON object a line)
        in `directory` (created if needed); return their paths."""
        return self._write(directory, "jsonl")

    def to_dataframes(self) -> tuple[Any, Any]:
        """(companies, postings) as pandas DataFrames (needs pandas)."""
        try:
            import pandas as pd  # type: ignore[import-untyped, import-not-found, unused-ignore]
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise ImportError("to_dataframes() needs pandas: pip install pandas") from error
        return (pd.DataFrame(self.companies, columns=list(COMPANY_FIELDS)),
                pd.DataFrame(self.postings, columns=list(POSTING_FIELDS)))

    def _write(self, directory: str, kind: str) -> list[str]:
        os.makedirs(directory, exist_ok=True)
        paths = []
        tables: tuple[tuple[str, tuple[str, ...], list[Any]], ...] = (
            ("companies", COMPANY_FIELDS, self.companies), ("postings", POSTING_FIELDS, self.postings))
        for name, fields, rows in tables:
            path = os.path.join(directory, f"{name}.{kind}")
            with open(path, "w", encoding="utf-8", newline="") as f:
                if kind == "csv":
                    writer = csv.DictWriter(f, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    for row in rows:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
            paths.append(path)
        return paths


def _parse_date(value: _datetime.date | str) -> _datetime.date:
    """A date of `value`: a date, an ISO date ('2025-01-31'), or anything
    Faker's `date_between()` takes ('-2y', 'today')."""
    from faker.providers.date_time import Provider as DateTimeProvider

    if isinstance(value, _datetime.datetime):
        return value.date()
    if isinstance(value, _datetime.date):
        return value
    try:
        return _datetime.date.fromisoformat(str(value))
    except ValueError:
        return DateTimeProvider._parse_date(value)


def _shares(total: int, weights: Mapping[str, float]) -> dict[str, int]:
    """`total` split in proportion to `weights` (largest remainders), at least
    1 to each key with a weight when `total` allows it."""
    keys = [key for key, weight in weights.items() if weight > 0]
    if not keys or total <= 0:
        return {key: 0 for key in weights}
    whole = sum(weights[key] for key in keys)
    exact = {key: total * weights[key] / whole for key in keys}
    counts = {key: math.floor(value) for key, value in exact.items()}
    if total >= len(keys):
        for key in keys:
            counts[key] = max(counts[key], 1)
    left = total - sum(counts.values())
    by_remainder = sorted(keys, key=lambda key: exact[key] - math.floor(exact[key]), reverse=True)
    for key in by_remainder[:max(left, 0)]:
        counts[key] += 1
    while sum(counts.values()) > total:  # the minimum of 1 overshot: take from the largest
        counts[max(counts, key=lambda key: counts[key])] -= 1
    return {key: counts.get(key, 0) for key in weights}


class _Builder:
    """The employers and postings of one provider (one locale)."""

    def __init__(self, provider: JobsProvider, locale: str, prefix: str, start: _datetime.date,
                 end: _datetime.date) -> None:
        self.provider, self.locale, self.prefix = provider, locale, prefix
        self.start, self.end = start, end
        self.rng = provider.generator.random
        self.conditions = provider._local_conditions()
        self.country_name = (self.conditions.get("place_names") or {}).get("country", self.conditions["country"])
        # {sector: [(company_id, (profile, employees, site, activity), activity index)]}
        self.pool: dict[str, list[tuple[str, Any, int | None]]] = {}
        self.companies: list[CompanyRow] = []
        self.seen: set[tuple[str, str | None]] = set()

    def sector_demand(self) -> dict[str, float]:
        """{activity sector: demand of the occupations whose main sector it is}."""
        demand = {sector: 0.0 for sector in self.provider._occupations["sectors"]}
        for occupation in self.provider._occupations["occupations"]:
            demand[occupation["sectors"][0]] += occupation["weight"]
        return demand

    def add_company(self, sector: str) -> tuple[str, Any, int | None]:
        """A new employer of `sector`: a real company only once in the pool,
        and, for those of up to SINGLE_SITE_EMPLOYEES, one whose city is a
        city of `job_location` where possible (all its jobs are there)."""
        provider, conditions = self.provider, self.conditions
        for _attempt in range(10):
            location = provider._local_location(conditions, None)
            profile, employees, site, naf = provider._hiring_company(sector, conditions, location)
            key = (profile["company"], profile["website"])
            if profile["website"] is not None and key in self.seen:
                continue
            if employees > SINGLE_SITE_EMPLOYEES or site["city"] == profile["city"]:
                break
        self.seen.add(key)
        company_id = f"{self.prefix}C{len(self.companies) + 1:05d}"
        index = None
        if naf is not None and "naf_by_sector" in conditions:
            index = next((i for i, item in enumerate(conditions["naf_by_sector"][sector]) if item[0] == naf[0]), None)
        # A city of all its jobs, unless its own is not one of job_location (then any city).
        city_wide = site if employees <= SINGLE_SITE_EMPLOYEES and site["city"] == profile["city"] else None
        self.companies.append({
            "company_id": company_id, "locale": self.locale, "name": profile["company"], "sector": sector,
            "industry": profile["industry"], "activity_code": provider._activity_code(naf, conditions),
            "employees": employees, "city": profile["city"], "country": self.country_name,
            "website": profile["website"], "founded": profile["founded"], "real": profile["ceo"] is None,
        })
        entry = (company_id, (profile, employees, city_wide, naf), index)
        self.pool.setdefault(sector, []).append(entry)
        return entry

    def build_pool(self, companies: int) -> None:
        for sector, count in _shares(companies, self.sector_demand()).items():
            for _ in range(count):
                self.add_company(sector)

    def employer(self, sector: str, isco: str | None) -> tuple[str, Any, int | None]:
        """An employer of `sector` for an occupation (ISCO unit group `isco`):
        weighted by the employees of the occupation in its activity."""
        candidates = self.pool.get(sector) or [self.add_company(sector)]
        fit = dict(map(tuple, self.provider._occupations["naf_by_isco"].get(isco, {}).get(sector, ())))
        weights = [fit.get(index, 0) if index is not None else 0 for _, _, index in candidates]
        if not any(weights):
            return self.rng.choice(candidates)
        return self.rng.choices(candidates, weights=weights)[0]

    def posted_date(self, seasonal: bool) -> _datetime.date:
        span = (self.end - self.start).days
        for _attempt in range(50):
            date = self.start + _datetime.timedelta(days=self.rng.randint(0, max(span, 0)))
            if not seasonal or date.month in SEASONAL_MONTHS:
                return date
        return date

    def lifecycle(self, posted: _datetime.date) -> tuple[str | None, str]:
        """(closing date or None, status) of a posting on `self.end`."""
        days = max(MIN_POSTING_DAYS, round(math.exp(self.rng.gauss(math.log(POSTING_DAYS), POSTING_DAYS_SIGMA))))
        closed = posted + _datetime.timedelta(days=days)
        if closed > self.end:
            return None, "open"
        return closed.isoformat(), "filled" if self.rng.random() < FILLED_SHARE else "expired"

    def posting(self) -> PostingRow:
        provider = self.provider
        found = provider._pick_occupation()
        occupation = provider._occupation_record(found, None)
        company_id, employer, _index = self.employer(occupation["sector"], occupation["isco_code"])
        posting = provider._occupation_posting(occupation, None, 5, employer)
        contract = self.conditions["contracts"][posting["work_type"]]
        posted = self.posted_date(contract["kind"] == "seasonal")
        closed, status = self.lifecycle(posted)
        location = posting["location"]
        return {
            "job_id": posting["job_id"], "company_id": company_id, "locale": self.locale,
            "job_title": posting["job_title"], "occupation_code": occupation["code"],
            "occupation": occupation["title"], "isco_code": occupation["isco_code"],
            "isco_group": occupation["isco_group"], "sector": occupation["sector"], "seniority": posting["seniority"],
            "work_type": posting["work_type"], "experience_min": posting["experience_min"],
            "experience_max": posting["experience_max"], "qualification": posting["qualification"],
            "salary_min": posting["salary_min"], "salary_max": posting["salary_max"],
            "salary_currency": posting["salary_currency"], "city": location["city"], "country": location["country"],
            "latitude": location["latitude"], "longitude": location["longitude"],
            "job_portal": posting["job_portal"], "posted_date": posted.isoformat(), "closed_date": closed,
            "status": status, "repost_of": None, "skills": "; ".join(posting["skills"]),
            "benefits": "; ".join(posting["benefits"]), "contact_person": posting["contact_person"],
            "contact": posting["contact"],
        }

    def repost(self, row: PostingRow) -> PostingRow:
        """The same posting published again on another job board a few days later."""
        portals = [portal for portal in self.conditions["job_portals"]["all"] if portal != row["job_portal"]]
        posted = min(_datetime.date.fromisoformat(row["posted_date"])
                     + _datetime.timedelta(days=self.rng.randint(1, MAX_REPOST_DELAY)), self.end)
        closed, status = self.lifecycle(posted)
        return {**row, "job_id": self.provider.job_id(), "job_portal": self.rng.choice(portals or [row["job_portal"]]),
                "posted_date": posted.isoformat(), "closed_date": closed, "status": status,
                "repost_of": row["job_id"]}


def build_dataset(
    provider: JobsProvider, postings: int, companies: int | None = None,
    start_date: _datetime.date | str = "-2y", end_date: _datetime.date | str = "today",
    repost_rate: float = 0.08, prefix: str = "",
) -> JobDataset:
    """The dataset of `JobsProvider.job_dataset()` (see the module docstring);
    `prefix` starts the company ids (one per locale in `make_dataset`)."""
    from faker_jobs import _generator_locale

    for name, value in (("postings", postings), ("companies", companies)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    if not 0 <= repost_rate < 1:
        raise ValueError(f"repost_rate must be in [0, 1), got {repost_rate!r}")
    start, end = _parse_date(start_date), _parse_date(end_date)
    if start > end:
        raise ValueError(f"start_date {start} is after end_date {end}")
    builder = _Builder(provider, _generator_locale(provider.generator) or "", prefix, start, end)
    if companies is None:
        companies = max(1, postings // 10)
    builder.build_pool(companies if postings else 0)
    rows: list[PostingRow] = []
    while len(rows) < postings:
        row = builder.posting()
        rows.append(row)
        if len(rows) < postings and builder.rng.random() < repost_rate:
            rows.append(builder.repost(row))
    return JobDataset(builder.companies, rows)


def make_dataset(
    locales: str | Mapping[str, float] = "en_US", postings: int = 1000, companies: int | None = None,
    start_date: _datetime.date | str = "-2y", end_date: _datetime.date | str = "today",
    repost_rate: float = 0.08, seed: int | None = None,
) -> JobDataset:
    """A dataset of one locale ('fr_FR') or of several, with the share of the
    postings of each ({'fr_FR': 0.6, 'de_DE': 0.4}): each locale's postings
    in its country and language, and as many of the companies; company ids
    start with the locale when there are several ('fr_FR-C00001'). `seed`
    makes it reproducible."""
    from faker import Faker

    from faker_jobs import JobsProvider

    weights = {locales: 1.0} if isinstance(locales, str) else dict(locales)
    if not weights or any(weight < 0 for weight in weights.values()):
        raise ValueError(f"locales must be a locale or {{locale: share}}, got {locales!r}")
    posting_counts = _shares(postings, weights)
    company_counts = _shares(companies, weights) if companies is not None else None
    datasets = []
    for i, locale in enumerate(weights):
        fake = Faker(locale)
        if seed is not None:
            fake.seed_instance(seed + i)
        provider = JobsProvider(fake)
        datasets.append(build_dataset(
            provider, posting_counts[locale], company_counts[locale] if company_counts else None, start_date,
            end_date, repost_rate, prefix=f"{locale}-" if len(weights) > 1 else ""))
    return JobDataset.concat(datasets)
