"""
Candidates and their applications: `JobsProvider.job_candidate()`, and in
job datasets (`job_dataset(candidates=...)`) a pool of candidates applying
to the postings.

- A candidate has an occupation (picked by demand, as the postings), a
  title of it, years of experience for its skill level, a diploma, some of
  its skills (activities) and knowledge, the salary they ask (around the
  local earnings of the occupation at their experience) and when they are
  available; a name, a personal e-mail address and a phone number of the
  Faker locale, in a city of the country.
- Applications: each posting gets about `applications` of them (a mean;
  log-normal spread, one at least for a filled posting), from candidates of
  the same occupation mostly, else of the same ISCO unit group, of the
  same activity sector or any, preferring those of the posting's city.
  A filled posting whose applicants are all hired elsewhere gets one more
  applicant still free, while the pool has one.
  Each has a match score (0-100): skills in common with the posting (40),
  experience within the range asked (25), salary asked within the offer
  (20), same city or country (15).
- Statuses follow the posting's lifecycle: a filled posting hires one of
  its applicants (the better scores more likely; a candidate is hired once
  at most), the others are 'rejected' or 'withdrawn'; an expired posting
  rejects all; an open one has applications 'in_review', at 'interview'
  (good scores) or already 'rejected' or 'withdrawn'.
"""
from __future__ import annotations

import datetime as _datetime
import math
import re
import unicodedata
from typing import TYPE_CHECKING, Any, TypedDict, cast

if TYPE_CHECKING:
    from faker_jobs import JobsProvider, LocationRecord

# Availability of a candidate, with its share.
AVAILABILITY = {"immediate": 0.4, "1_month": 0.25, "3_months": 0.25, "6_months": 0.1}
# The salary asked: the occupation's local mean at the candidate's experience times this range.
SALARY_ASKED = (0.95, 1.2)
# Where the applicants of a posting come from: same occupation, ISCO unit group, sector, anywhere.
APPLICANT_SOURCES = (("code", 0.55), ("isco", 0.25), ("sector", 0.15), ("any", 0.05))
# Candidates looked at for one application slot: the first of the posting's city, else the first.
CITY_TRIES = 10
# Spread of the number of applications of a posting (log-normal sigma).
APPLICATIONS_SIGMA = 0.7
# Mean days between the publication and an application; an applicant withdraws with this share.
APPLY_DAYS = 7
WITHDRAWN_SHARE = 0.07
# Score weights.
SCORE_WEIGHTS = {"skills": 40, "experience": 25, "salary": 20, "location": 15}
# The hired applicant: weighted by exp(score / HIRE_SHARPNESS).
HIRE_SHARPNESS = 6
# Applications of open postings: at interview from this score, still in review this many days.
INTERVIEW_SCORE = 60
REVIEW_DAYS = 10


class CandidateRecord(TypedDict):
    """A candidate, as returned by `JobsProvider.job_candidate()`: their
    occupation (`occupation_code`, `occupation`, `job_title` they look for),
    `experience_years`, `qualification`, `skills` (activities and knowledge
    of the occupation), `desired_salary` (yearly, in `salary_currency`),
    `availability` ('immediate', '1_month', '3_months' or '6_months')."""

    name: str
    email: str
    phone: str
    city: str
    country: str
    occupation_code: str
    occupation: str
    job_title: str
    isco_code: str | None
    isco_group: str
    sector: str
    experience_years: int
    qualification: str
    skills: list[str]
    desired_salary: int
    salary_currency: str
    availability: str


class CandidateRow(TypedDict):
    """A row of `JobDataset.candidates`: a `CandidateRecord`, flat (skills joined with '; ')."""

    candidate_id: str
    locale: str
    name: str
    email: str
    phone: str
    city: str
    country: str
    occupation_code: str
    occupation: str
    job_title: str
    isco_code: str | None
    isco_group: str
    sector: str
    experience_years: int
    qualification: str
    skills: str
    desired_salary: int
    salary_currency: str
    availability: str


class ApplicationRow(TypedDict):
    """A row of `JobDataset.applications`: a candidate's application to a
    posting, its `match_score` (0-100), `status` ('in_review', 'interview',
    'hired', 'rejected' or 'withdrawn') and the date of that status."""

    application_id: str
    job_id: int | str
    candidate_id: str
    applied_date: str
    match_score: int
    status: str
    status_date: str


CANDIDATE_FIELDS = tuple(CandidateRow.__annotations__)
APPLICATION_FIELDS = tuple(ApplicationRow.__annotations__)


def _email_name(first: str, last: str) -> str:
    def ascii_(text: str) -> str:
        plain = unicodedata.normalize("NFKD", text.replace("ł", "l").replace("Ł", "L").replace("ß", "ss"))
        return re.sub(r"[^a-z0-9]", "", plain.encode("ascii", "ignore").decode().lower())

    return ".".join(part for part in (ascii_(first), ascii_(last)) if part)


def make_candidate(
    provider: JobsProvider, conditions: dict[str, Any], occupation: dict[str, Any], location: LocationRecord,
) -> CandidateRecord:
    """A candidate of `occupation` living in `location`, with the local `conditions`."""
    generator, rng = provider.generator, provider.generator.random
    level = conditions["skill_levels"][occupation["isco_group"]]
    low, high = provider._local_experience(level, None, conditions)
    experience = rng.randint(low, high + 3)
    if occupation["qualifications"] and conditions.get("rome_diplomas", True):
        qualification = rng.choice(occupation["qualifications"])
    else:
        qualification = provider._default_qualification(conditions, level, occupation["sector"])
    skills = rng.sample(occupation["skills"], min(len(occupation["skills"]), rng.randint(5, 8)))
    skills += rng.sample(occupation["knowledge"], min(len(occupation["knowledge"]), 3))
    contracts = conditions["contracts"]
    permanent = next((spec for spec in contracts.values() if spec["kind"] == "permanent"),
                     next(iter(contracts.values())))
    section = conditions.get("section_by_sector", {}).get(occupation["sector"])
    salary_low, salary_high = provider._local_salary(occupation["isco_group"], section, (experience, experience),
                                                     permanent, conditions)
    scale = conditions.get("salary_scale", 1)
    asked = (salary_low + salary_high) / 2 * rng.uniform(*SALARY_ASKED)
    step = (1000 if asked >= 100_000 * scale else 500) * scale
    first, last = generator.first_name(), generator.last_name()
    local = _email_name(first, last) or f"candidat{rng.randint(1, 9999)}"
    if rng.random() < 0.4:
        local += str(rng.randint(1, 99))
    return {
        "name": f"{first} {last}",
        "email": f"{local}@{generator.free_email_domain()}",
        "phone": provider._phone_number(),
        "city": location["city"],
        "country": location["country"],
        "occupation_code": occupation["code"],
        "occupation": occupation["title"],
        "job_title": occupation["job_title"],
        "isco_code": occupation["isco_code"],
        "isco_group": occupation["isco_group"],
        "sector": occupation["sector"],
        "experience_years": experience,
        "qualification": qualification,
        "skills": skills,
        "desired_salary": int(round(asked / step) * step),
        "salary_currency": conditions["currency"],
        "availability": rng.choices(list(AVAILABILITY), weights=list(AVAILABILITY.values()))[0],
    }


def match_score(candidate: CandidateRow, posting: dict[str, Any], skills: set[str]) -> int:
    """0-100: skills in common, experience in the range asked, salary within the offer, place."""
    posting_skills = {skill for skill in str(posting["skills"]).split("; ") if skill}
    common = len(posting_skills & skills) / len(posting_skills) if posting_skills else 0
    years, low, high = candidate["experience_years"], posting["experience_min"], posting["experience_max"]
    gap = low - years if years < low else years - high - 5 if years > high + 5 else 0
    experience = math.exp(-max(gap, 0) / 2)
    offer = posting["salary_max"]
    asked = candidate["desired_salary"]
    salary = 1.0 if asked <= offer else max(0.0, 1 - (asked / offer - 1) * 4)
    location = 1.0 if candidate["city"] == posting["city"] else 0.5 if candidate["country"] == posting["country"] else 0
    weights = SCORE_WEIGHTS
    score = (weights["skills"] * common + weights["experience"] * experience + weights["salary"] * salary
             + weights["location"] * location)
    return int(round(score))


class Applications:
    """The candidates of a dataset (one locale) and their applications."""

    def __init__(self, provider: JobsProvider, conditions: dict[str, Any], locale: str, prefix: str,
                 end: _datetime.date, mean: float) -> None:
        self.provider, self.conditions, self.locale, self.prefix = provider, conditions, locale, prefix
        self.end, self.mean = end, mean
        self.rng = provider.generator.random
        self.candidates: list[CandidateRow] = []
        self.applications: list[ApplicationRow] = []
        self.skills: list[set[str]] = []
        self.buckets: dict[tuple[str, Any], list[int]] = {}
        self.hired: set[int] = set()

    def build_pool(self, count: int) -> None:
        provider = self.provider
        for i in range(count):
            occupation = provider._occupation_record(provider._pick_occupation(), None)
            location = provider._local_location(self.conditions, None)
            record = make_candidate(provider, self.conditions, dict(occupation), location)
            flat: dict[str, Any] = {"candidate_id": f"{self.prefix}P{i + 1:06d}", "locale": self.locale, **record,
                                    "skills": "; ".join(record["skills"])}
            self.candidates.append(cast(CandidateRow, {key: flat[key] for key in CANDIDATE_FIELDS}))
            self.skills.append(set(record["skills"]))
            for key in (("code", record["occupation_code"]), ("isco", record["isco_code"]),
                        ("sector", record["sector"]), ("any", None)):
                self.buckets.setdefault(key, []).append(i)

    def applicants(self, posting: dict[str, Any], count: int) -> list[int]:
        """`count` candidates (indexes) for a posting, at most the pool."""
        rng, chosen = self.rng, list[int]()
        keys = {"code": posting["occupation_code"], "isco": posting["isco_code"], "sector": posting["sector"],
                "any": None}
        sources, weights = [name for name, _ in APPLICANT_SOURCES], [share for _, share in APPLICANT_SOURCES]
        for _ in range(count * 3):
            if len(chosen) == count:
                break
            # From the source drawn, else the next wider one with candidates not chosen yet.
            start = sources.index(rng.choices(sources, weights)[0])
            for source in sources[start:]:
                bucket = [i for i in self.buckets.get((source, keys[source]), ()) if i not in chosen] \
                    if source != "any" else self.buckets[("any", None)]
                if bucket:
                    break
            tries = [rng.choice(bucket) for _ in range(CITY_TRIES)]
            index = next((i for i in tries if self.candidates[i]["city"] == posting["city"]), tries[0])
            if index not in chosen:
                chosen.append(index)
        return chosen

    def add(self, posting: dict[str, Any]) -> None:
        """The applications of a posting (a `PostingRow`), with their statuses."""
        rng = self.rng
        count = round(self.mean * math.exp(rng.gauss(0, APPLICATIONS_SIGMA) - APPLICATIONS_SIGMA ** 2 / 2))
        if posting["status"] == "filled":
            count = max(count, 1)
        if not count:
            return
        posted = _datetime.date.fromisoformat(posting["posted_date"])
        last = _datetime.date.fromisoformat(posting["closed_date"]) if posting["closed_date"] else self.end
        entries = []
        for index in self.applicants(posting, count):
            days = min(round(rng.expovariate(1 / APPLY_DAYS)), max((last - posted).days - 1, 0))
            applied = posted + _datetime.timedelta(days=days)
            entries.append((index, applied, match_score(self.candidates[index], posting, self.skills[index])))
        hired = None
        if posting["status"] == "filled":
            free = [entry for entry in entries if entry[0] not in self.hired]
            if not free:  # every applicant is hired elsewhere: one more who is not, if any is left
                chosen = {index for index, _, _ in entries}
                left = [i for i in self.buckets[("any", None)] if i not in self.hired and i not in chosen]
                if left:
                    index = rng.choice(left)
                    applied = posted + _datetime.timedelta(days=rng.randint(0, max((last - posted).days - 1, 0)))
                    entries.append((index, applied, match_score(self.candidates[index], posting, self.skills[index])))
            free = [entry for entry in entries if entry[0] not in self.hired] or entries
            hired = rng.choices(free, weights=[math.exp(score / HIRE_SHARPNESS) for _, _, score in free])[0][0]
            self.hired.add(hired)
        for index, applied, score in entries:
            status, date = self.status(posting["status"], index == hired, score, applied, last)
            self.applications.append({
                "application_id": f"{self.prefix}A{len(self.applications) + 1:07d}", "job_id": posting["job_id"],
                "candidate_id": self.candidates[index]["candidate_id"], "applied_date": applied.isoformat(),
                "match_score": score, "status": status, "status_date": date.isoformat(),
            })

    def status(self, posting_status: str, hired: bool, score: int, applied: _datetime.date,
               last: _datetime.date) -> tuple[str, _datetime.date]:
        """(status, its date) of an application to a posting closed or still open on `last`."""
        rng = self.rng
        if hired:
            return "hired", last
        if rng.random() < WITHDRAWN_SHARE and last > applied:
            return "withdrawn", applied + _datetime.timedelta(days=rng.randint(1, (last - applied).days))
        if posting_status != "open":
            return "rejected", last
        waited = (last - applied).days
        if waited <= REVIEW_DAYS:
            return "in_review", applied
        if score >= INTERVIEW_SCORE and rng.random() < 0.6:
            return "interview", applied + _datetime.timedelta(days=rng.randint(REVIEW_DAYS // 2, waited))
        return "rejected", applied + _datetime.timedelta(days=rng.randint(REVIEW_DAYS // 2, waited))
