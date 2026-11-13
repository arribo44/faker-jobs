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
- Salaries: those of the postings (`job_occupation_posting`) on `end_date`;
  earlier postings lowered by the country's yearly growth of the GDP per
  capita in local currency (World Bank, latest 5 years; about 5% in France,
  much more where inflation is high), rounded as the postings' salaries.
- Remote work: 'on_site', 'hybrid' or 'remote', as the postings (see
  `job_occupation_posting`).
- Contacts: each employer has its recruiters (1 up to 50 employees, 2 up
  to 500, 3 up to 5,000, else 4; names and phone numbers of the Faker
  locale), with an e-mail address at the company's domain (its website, or
  one made of its name); each posting names one of them.
- Job ids: numbers by default, else from `id_template` (see
  `JobsProvider.job_id`) with the publication date, the country and `{n}`,
  the posting's number from 1 (across the locales of `make_dataset`);
  unique in the dataset.

`candidates` adds a pool of candidates and their applications to the
postings (see faker_jobs/candidates.py).

`dirty` adds defects of real-world data to a share of the rows, listed in
`JobDataset.defects` (see faker_jobs/dirty.py).

Reproducible with `Faker.seed()` (or the `seed` of `make_dataset`).
"""
from __future__ import annotations

import csv
import datetime as _datetime
import json
import math
import os
import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypedDict

from faker_jobs.candidates import APPLICATION_FIELDS, CANDIDATE_FIELDS, Applications, ApplicationRow, CandidateRow
from faker_jobs.dirty import DEFECT_FIELDS, DefectRow, add_defects

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
# Draws of a templated job id before giving up on finding one not used yet.
ID_ATTEMPTS = 100
# Recruiters of an employer: (up to this many employees, recruiters); 4 above.
RECRUITERS = ((50, 1), (500, 2), (5000, 3))
MAX_RECRUITERS = 4
# Legal forms left out of the made-up domains ('Dupont SARL' -> dupont.fr).
LEGAL_FORMS = re.compile(r"\b(s\.?a\.?r\.?l|sas|sasu|sa|eurl|snc|gmbh|ag|kgaa|kg|ohg|ug|e\.?k|ltd|llc|inc|plc|co|corp|"
                         r"s\.?l|s\.?a|s\.?p\.?a|s\.?r\.?l|s\.?n\.?c|lda|bv|nv|vof|sp\.? z o\.?o|sp\.? ?[jkp]|s\.?c|"
                         r"and sons|et fils|e hijos|e figli|group|groupe)\b\.?", re.IGNORECASE)


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

    job_id: int | str
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
    remote: str
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
    repost_of: int | str | None
    skills: str
    benefits: str
    contact_person: str
    contact_email: str
    contact: str


COMPANY_FIELDS = tuple(CompanyRow.__annotations__)
POSTING_FIELDS = tuple(PostingRow.__annotations__)


@dataclass
class JobDataset:
    """Employers and their postings: `companies` and `postings` are lists of
    rows (see `CompanyRow`, `PostingRow`), linked by `company_id`; `defects`
    lists the defects of a dirty dataset (see `DefectRow`), empty otherwise;
    `candidates` and their `applications` to the postings (by `job_id` and
    `candidate_id`), empty without `candidates`."""

    companies: list[CompanyRow] = field(default_factory=list)
    postings: list[PostingRow] = field(default_factory=list)
    defects: list[DefectRow] = field(default_factory=list)
    candidates: list[CandidateRow] = field(default_factory=list)
    applications: list[ApplicationRow] = field(default_factory=list)

    @classmethod
    def concat(cls, datasets: Iterable[JobDataset]) -> JobDataset:
        """One dataset of several (e.g. of several locales)."""
        result = cls()
        for dataset in datasets:
            result.companies.extend(dataset.companies)
            result.postings.extend(dataset.postings)
            result.defects.extend(dataset.defects)
            result.candidates.extend(dataset.candidates)
            result.applications.extend(dataset.applications)
        return result

    def to_csv(self, directory: str) -> list[str]:
        """Write companies.csv and postings.csv (UTF-8, header row) in
        `directory` (created if needed), candidates.csv and
        applications.csv with candidates, defects.csv for a dirty dataset;
        return their paths."""
        return self._write(directory, "csv")

    def to_jsonl(self, directory: str) -> list[str]:
        """Write companies.jsonl and postings.jsonl (one JSON object a line)
        in `directory` (created if needed), candidates.jsonl and
        applications.jsonl with candidates, defects.jsonl for a dirty
        dataset; return their paths."""
        return self._write(directory, "jsonl")

    def to_dataframes(self) -> tuple[Any, Any]:
        """(companies, postings) as pandas DataFrames (needs pandas)."""
        try:
            import pandas as pd  # type: ignore[import-untyped, import-not-found, unused-ignore]
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise ImportError("to_dataframes() needs pandas: pip install pandas") from error
        return (pd.DataFrame(self.companies, columns=list(COMPANY_FIELDS)),
                pd.DataFrame(self.postings, columns=list(POSTING_FIELDS)))

    def to_dataframe(self, table: str) -> Any:
        """One table ('companies', 'postings', 'candidates', 'applications'
        or 'defects') as a pandas DataFrame (needs pandas)."""
        try:
            import pandas as pd  # type: ignore[import-untyped, import-not-found, unused-ignore]
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise ImportError("to_dataframe() needs pandas: pip install pandas") from error
        tables = {name: (fields, rows) for name, fields, rows in self._tables()}
        if table not in tables:
            raise ValueError(f"unknown table {table!r}: one of {', '.join(tables)}")
        fields, rows = tables[table]
        return pd.DataFrame(rows, columns=list(fields))

    def _tables(self) -> list[tuple[str, tuple[str, ...], list[Any]]]:
        return [("companies", COMPANY_FIELDS, self.companies), ("postings", POSTING_FIELDS, self.postings),
                ("candidates", CANDIDATE_FIELDS, self.candidates),
                ("applications", APPLICATION_FIELDS, self.applications), ("defects", DEFECT_FIELDS, self.defects)]

    def _write(self, directory: str, kind: str) -> list[str]:
        os.makedirs(directory, exist_ok=True)
        paths = []
        tables = [(name, fields, rows) for name, fields, rows in self._tables()
                  if rows or name in ("companies", "postings")]
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


# Letters that do not decompose into an ASCII letter and an accent.
_LETTERS = str.maketrans({"ł": "l", "Ł": "L", "ß": "ss", "æ": "ae", "Æ": "AE", "ø": "o", "Ø": "O", "đ": "d",
                          "Đ": "D", "œ": "oe", "Œ": "OE", "ı": "i", "þ": "th", "ð": "d"})


def _ascii(text: str) -> str:
    """`text` in lowercase ASCII letters and digits ('Société Générale' -> 'societegenerale')."""
    plain = unicodedata.normalize("NFKD", text.translate(_LETTERS)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", plain.lower())


def _domain(website: str | None, name: str, tld: str) -> str:
    """The e-mail domain of a company: its website's, else one made of its name."""
    if website:
        domain = re.sub(r"^(https?://)?(www\.)?", "", website.strip().lower()).split("/")[0]
        if "." in domain:
            return domain
    words = [_ascii(word) for word in LEGAL_FORMS.sub(" ", name).replace("-", " ").split()]
    stem = "-".join(word for word in words if word)[:30].strip("-") or "entreprise"
    return f"{stem}.{tld}"


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


class _Ids:
    """The job ids of a dataset (of all its locales) and the number of the next posting."""

    def __init__(self) -> None:
        self.used: set[int | str] = set()
        self.next = 1


class _Builder:
    """The employers and postings of one provider (one locale)."""

    def __init__(self, provider: JobsProvider, locale: str, prefix: str, start: _datetime.date,
                 end: _datetime.date, id_template: str | None = None, ids: _Ids | None = None) -> None:
        self.provider, self.locale, self.prefix = provider, locale, prefix
        self.start, self.end = start, end
        self.id_template, self.ids = id_template, ids if ids is not None else _Ids()
        self.rng = provider.generator.random
        self.conditions = provider._local_conditions()
        self.country_name = (self.conditions.get("place_names") or {}).get("country", self.conditions["country"])
        from faker_jobs import _labour

        self.growth = _labour(self.conditions["country"])["wage_growth"]
        # {sector: [(company_id, (profile, employees, site, activity), activity index)]}
        self.pool: dict[str, list[tuple[str, Any, int | None]]] = {}
        self.companies: list[CompanyRow] = []
        self.seen: set[tuple[str, str | None]] = set()
        self.recruiter_pool: dict[str, list[tuple[str, str, str]]] = {}

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
        salary_min, salary_max = self.salaries(posting["salary_min"], posting["salary_max"], posted)
        contact_person, contact_email, contact = self.rng.choice(self.recruiters(company_id))
        return {
            "job_id": self.job_id(posting["job_id"], posted), "company_id": company_id, "locale": self.locale,
            "job_title": posting["job_title"], "occupation_code": occupation["code"],
            "occupation": occupation["title"], "isco_code": occupation["isco_code"],
            "isco_group": occupation["isco_group"], "sector": occupation["sector"], "seniority": posting["seniority"],
            "work_type": posting["work_type"], "remote": posting["remote"], "experience_min": posting["experience_min"],
            "experience_max": posting["experience_max"], "qualification": posting["qualification"],
            "salary_min": salary_min, "salary_max": salary_max,
            "salary_currency": posting["salary_currency"], "city": location["city"], "country": location["country"],
            "latitude": location["latitude"], "longitude": location["longitude"],
            "job_portal": posting["job_portal"], "posted_date": posted.isoformat(), "closed_date": closed,
            "status": status, "repost_of": None, "skills": "; ".join(posting["skills"]),
            "benefits": "; ".join(posting["benefits"]), "contact_person": contact_person,
            "contact_email": contact_email, "contact": contact,
        }

    def recruiters(self, company_id: str) -> list[tuple[str, str, str]]:
        """[(name, e-mail, phone)] of the recruiters of an employer, made on its first posting."""
        if company_id not in self.recruiter_pool:
            company = self.companies[int(company_id[len(self.prefix) + 1:]) - 1]
            count = next((n for limit, n in RECRUITERS if company["employees"] <= limit), MAX_RECRUITERS)
            generator = self.provider.generator
            domain = _domain(company["website"], company["name"], generator.tld())
            people = []
            for i in range(count):
                first, last = generator.first_name(), generator.last_name()
                local = ".".join(part for part in (_ascii(first), _ascii(last)) if part) or f"recrutement{i + 1}"
                people.append((f"{first} {last}", f"{local}@{domain}", self.provider._phone_number()))
            self.recruiter_pool[company_id] = people
        return self.recruiter_pool[company_id]

    def salaries(self, low: int, high: int, posted: _datetime.date) -> tuple[int, int]:
        """The salaries of a posting on `end_date`, brought back to its date by the country's growth."""
        years = (self.end - posted).days / 365.25
        if not years:
            return low, high
        factor = (1 + self.growth) ** -years
        scale = self.conditions.get("salary_scale", 1)
        step = (1000 if (low + high) / 2 >= 100_000 * scale else 500) * scale
        low, high = round(low * factor / step) * step, round(high * factor / step) * step
        return int(low), int(max(high, low + step))

    def job_id(self, default: int | str, posted: _datetime.date) -> int | str:
        """The job id of the next posting: `default`, or one from the template not used yet."""
        n, self.ids.next = self.ids.next, self.ids.next + 1
        if self.id_template is None:
            self.ids.used.add(default)
            return default
        for _ in range(ID_ATTEMPTS):
            job_id = self.provider.job_id(self.id_template, posted, self.conditions["country"], n)
            if job_id not in self.ids.used:
                self.ids.used.add(job_id)
                return job_id
        raise ValueError(f"job id template {self.id_template!r} gives too few distinct ids for the dataset "
                         "(add random characters #, ? or *, or {n})")

    def repost(self, row: PostingRow) -> PostingRow:
        """The same posting published again on another job board a few days later."""
        portals = [portal for portal in self.conditions["job_portals"]["all"] if portal != row["job_portal"]]
        posted = min(_datetime.date.fromisoformat(row["posted_date"])
                     + _datetime.timedelta(days=self.rng.randint(1, MAX_REPOST_DELAY)), self.end)
        closed, status = self.lifecycle(posted)
        job_id = self.job_id(self.provider.job_id(), posted)
        return {**row, "job_id": job_id, "job_portal": self.rng.choice(portals or [row["job_portal"]]),
                "posted_date": posted.isoformat(), "closed_date": closed, "status": status,
                "repost_of": row["job_id"]}


def build_dataset(
    provider: JobsProvider, postings: int, companies: int | None = None,
    start_date: _datetime.date | str = "-2y", end_date: _datetime.date | str = "today",
    repost_rate: float = 0.08, prefix: str = "", id_template: str | None = None, ids: _Ids | None = None,
    dirty: float = 0.0, candidates: int = 0, applications: float = 10.0,
) -> JobDataset:
    """The dataset of `JobsProvider.job_dataset()` (see the module docstring);
    `prefix` starts the company ids (one per locale in `make_dataset`), `ids`
    are the job ids already used (by the other locales of `make_dataset`)."""
    from faker_jobs import _generator_locale

    for name, value in (("postings", postings), ("companies", companies), ("candidates", candidates)):
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
    if not 0 <= dirty <= 1:
        raise ValueError(f"dirty must be in [0, 1], got {dirty!r}")
    if isinstance(applications, bool) or not isinstance(applications, (int, float)) or applications < 0:
        raise ValueError(f"applications must be a non-negative number, got {applications!r}")
    if not 0 <= repost_rate < 1:
        raise ValueError(f"repost_rate must be in [0, 1), got {repost_rate!r}")
    start, end = _parse_date(start_date), _parse_date(end_date)
    if start > end:
        raise ValueError(f"start_date {start} is after end_date {end}")
    if id_template is not None and (not isinstance(id_template, str) or not id_template):
        raise ValueError(f"id_template must be a non-empty string, got {id_template!r}")
    builder = _Builder(provider, _generator_locale(provider.generator) or "", prefix, start, end, id_template, ids)
    if companies is None:
        companies = max(1, postings // 10)
    builder.build_pool(companies if postings else 0)
    rows: list[PostingRow] = []
    while len(rows) < postings:
        row = builder.posting()
        rows.append(row)
        if len(rows) < postings and builder.rng.random() < repost_rate:
            rows.append(builder.repost(row))
    data = JobDataset(builder.companies, rows)
    if candidates:
        pool = Applications(provider, builder.conditions, builder.locale, prefix, end, applications)
        pool.build_pool(candidates)
        for row in rows:
            pool.add(dict(row))
        data.candidates, data.applications = pool.candidates, pool.applications
    return add_defects(data, dirty, builder.rng)


def make_dataset(
    locales: str | Mapping[str, float] = "en_US", postings: int = 1000, companies: int | None = None,
    start_date: _datetime.date | str = "-2y", end_date: _datetime.date | str = "today",
    repost_rate: float = 0.08, seed: int | None = None, id_template: str | None = None, dirty: float = 0.0,
    candidates: int = 0, applications: float = 10.0,
) -> JobDataset:
    """A dataset of one locale ('fr_FR') or of several, with the share of the
    postings of each ({'fr_FR': 0.6, 'de_DE': 0.4}): each locale's postings
    in its country and language, and as many of the companies; company ids
    start with the locale when there are several ('fr_FR-C00001'). `seed`
    makes it reproducible; `id_template` gives the job ids from a template
    (see `JobsProvider.job_id`), unique and numbered (`{n}`) across the locales;
    `dirty` the share of rows with a defect (see faker_jobs/dirty.py);
    `candidates` (split between the locales as the postings) apply to the
    postings of their locale, `applications` of them a posting on average
    (see faker_jobs/candidates.py)."""
    from faker import Faker

    from faker_jobs import JobsProvider

    weights = {locales: 1.0} if isinstance(locales, str) else dict(locales)
    if not weights or any(weight < 0 for weight in weights.values()):
        raise ValueError(f"locales must be a locale or {{locale: share}}, got {locales!r}")
    posting_counts = _shares(postings, weights)
    company_counts = _shares(companies, weights) if companies is not None else None
    candidate_counts = _shares(candidates, weights)
    datasets = []
    ids = _Ids()
    for i, locale in enumerate(weights):
        fake = Faker(locale)
        if seed is not None:
            fake.seed_instance(seed + i)
        provider = JobsProvider(fake)
        datasets.append(build_dataset(
            provider, posting_counts[locale], company_counts[locale] if company_counts else None, start_date,
            end_date, repost_rate, prefix=f"{locale}-" if len(weights) > 1 else "", id_template=id_template, ids=ids,
            dirty=dirty, candidates=candidate_counts[locale], applications=applications))
    return JobDataset.concat(datasets)
