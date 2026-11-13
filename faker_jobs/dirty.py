"""
Dirty datasets: defects of real-world job data added to a share of the rows
of a `JobDataset` (`job_dataset(dirty=0.1)`, `make_dataset(dirty=...)`,
`python -m faker_jobs export --dirty 0.1`), to test cleaning, validation
and deduplication pipelines.

Each defect is listed in `JobDataset.defects` (see `DefectRow`): the table,
the id of the row, the field, the kind of defect and the original value, the
ground truth of a cleaning. Kinds:

- postings: 'typo' (a letter swapped, dropped or doubled in the job title
  or the city), 'case' (job title in upper or lower case), 'whitespace'
  (spaces around or inside the job title), 'missing' (a value left empty:
  salaries, city, qualification, contact, experience), 'monthly_salary'
  (a monthly amount in a yearly field), 'swapped_salary' (minimum above
  maximum), 'date_format' (another date format: '13/11/2026', '11/13/2026',
  '13.11.2026', '2026/11/13', '13 Nov 2026'), 'duplicate' (the posting
  again under another id, not flagged by `repost_of`, maybe with a
  whitespace or case change and a day or two later);
- companies: 'name_variant' (the company again under another id and a
  variant of its name, upper case, legal form or typo, with part of its
  postings), 'missing' (website, founding year or city left empty).

A row gets one defect; `rate` is the share of rows of each table with one
(duplicates counted). Reproducible with the dataset's random generator.
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, TypedDict, cast

if TYPE_CHECKING:
    from faker_jobs.dataset import JobDataset

POSTING_DEFECTS = {"typo": 3, "case": 1, "whitespace": 1, "missing": 3, "monthly_salary": 1, "swapped_salary": 1,
                   "date_format": 2, "duplicate": 2}
COMPANY_DEFECTS = {"name_variant": 2, "missing": 1}
POSTING_MISSING = (("salary_min", "salary_max"), ("city",), ("qualification",), ("contact_person", "contact_email",
                   "contact"), ("experience_min", "experience_max"), ("benefits",))
COMPANY_MISSING = ("website", "founded", "city")
DATE_FORMATS = ("%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y", "%Y/%m/%d", "%d %b %Y")
LEGAL_FORMS = ("SA", "SAS", "GmbH", "Ltd", "Inc.", "S.L.", "S.p.A.", "B.V.", "Sp. z o.o.", "Lda")
MONTHS_A_YEAR = 12


class DefectRow(TypedDict):
    """A defect of a dirty dataset: `table` ('postings' or 'companies'), `id`
    (job_id or company_id of the dirty row), `field` (None for a duplicate
    row), `kind` and `original` (the clean value, as text; for a duplicate,
    the id of the row it copies)."""

    table: str
    id: str
    field: str | None
    kind: str
    original: str | None


DEFECT_FIELDS = tuple(DefectRow.__annotations__)


def _text(value: Any) -> str | None:
    return None if value is None else str(value)


def _typo(text: str, rng: random.Random) -> str:
    """`text` with two letters swapped, one dropped or one doubled."""
    letters = [i for i, char in enumerate(text) if char.isalpha()]
    if len(letters) < 3:
        return text + text[-1:] if text else text
    i = rng.choice(letters[:-1])
    kind = rng.choice(("swap", "drop", "double"))
    if kind == "swap" and text[i] != text[i + 1]:
        return text[:i] + text[i + 1] + text[i] + text[i + 2:]
    if kind == "drop":
        return text[:i] + text[i + 1:]
    return text[:i] + text[i] + text[i:]


def _spaces(text: str, rng: random.Random) -> str:
    words = text.split(" ")
    if len(words) > 1 and rng.random() < 0.5:
        i = rng.randrange(1, len(words))
        return " ".join(words[:i]) + "  " + " ".join(words[i:])
    return rng.choice((" ", "  ", "\t")) + text + rng.choice(("", " ", "  "))


def _case(text: str, rng: random.Random) -> str:
    return text.upper() if rng.random() < 0.6 else text.lower()


class _Dirtier:
    def __init__(self, data: JobDataset, rng: random.Random) -> None:
        self.data, self.rng = data, rng
        self.defects: list[DefectRow] = []
        self.ids = {str(row["job_id"]) for row in data.postings}

    def note(self, table: str, row_id: Any, field: str | None, kind: str, original: Any) -> None:
        self.defects.append({"table": table, "id": str(row_id), "field": field, "kind": kind,
                             "original": _text(original)})

    def new_job_id(self, job_id: int | str) -> int | str:
        """A job id not used yet, in the shape of `job_id`."""
        for _ in range(1000):
            if isinstance(job_id, int):
                candidate: int | str = self.rng.randint(10**14, 10**16 - 1)
            else:
                candidate = "".join(self.rng.choice("0123456789") if char.isdigit() else char for char in job_id)
                if candidate == job_id:
                    candidate = f"{job_id}-{self.rng.randint(2, 99)}"
            if str(candidate) not in self.ids:
                self.ids.add(str(candidate))
                return candidate
        raise ValueError(f"no free job id like {job_id!r}")

    def posting(self, row: dict[str, Any], kind: str) -> bool:
        """Add a defect of `kind` to a posting; False when it does not apply."""
        rng, job_id = self.rng, row["job_id"]
        if kind in ("typo", "case", "whitespace"):
            field = "city" if kind == "typo" and row["city"] and rng.random() < 0.3 else "job_title"
            change = {"typo": _typo, "case": _case, "whitespace": _spaces}[kind]
            value = change(row[field], rng)
            if value == row[field]:
                return False
            self.note("postings", job_id, field, kind, row[field])
            row[field] = value
        elif kind == "missing":
            fields = rng.choice([group for group in POSTING_MISSING if row[group[0]] not in (None, "")] or [()])
            if not fields:
                return False
            for field in fields:
                self.note("postings", job_id, field, kind, row[field])
                row[field] = None if field.startswith(("salary", "experience")) else ""
        elif kind in ("monthly_salary", "swapped_salary"):
            if row["salary_min"] is None or row["salary_max"] is None:
                return False
            for field in ("salary_min", "salary_max"):
                self.note("postings", job_id, field, kind, row[field])
            if kind == "monthly_salary":
                row["salary_min"] = int(round(row["salary_min"] / MONTHS_A_YEAR, -1))
                row["salary_max"] = int(round(row["salary_max"] / MONTHS_A_YEAR, -1))
            elif row["salary_min"] == row["salary_max"]:
                return False
            else:
                row["salary_min"], row["salary_max"] = row["salary_max"], row["salary_min"]
        elif kind == "date_format":
            from faker_jobs.dataset import _parse_date

            try:
                posted = _parse_date(row["posted_date"])
            except ValueError:
                return False
            self.note("postings", job_id, "posted_date", kind, row["posted_date"])
            row["posted_date"] = posted.strftime(rng.choice(DATE_FORMATS))
        return True

    def duplicate(self, row: dict[str, Any]) -> dict[str, Any]:
        """A copy of a posting under another id, maybe slightly changed."""
        from faker_jobs.dataset import _parse_date

        copy = {**row, "job_id": self.new_job_id(row["job_id"]), "repost_of": None}
        if self.rng.random() < 0.5:
            copy["job_title"] = (_spaces if self.rng.random() < 0.5 else _case)(copy["job_title"], self.rng)
        try:
            posted = _parse_date(row["posted_date"])
            import datetime as _datetime

            copy["posted_date"] = (posted + _datetime.timedelta(days=self.rng.randint(0, 2))).isoformat()
        except ValueError:
            pass
        self.note("postings", copy["job_id"], None, "duplicate", row["job_id"])
        return copy

    def company_variant(self, company: dict[str, Any], postings: list[dict[str, Any]]) -> dict[str, Any] | None:
        """The company again under a new id and a variant of its name, with part of its postings."""
        own = [row for row in postings if row["company_id"] == company["company_id"]]
        if len(own) < 2:
            return None
        name = company["name"]
        variant = self.rng.choice((name.upper(), _typo(name, self.rng), f"{name} {self.rng.choice(LEGAL_FORMS)}",
                                   name.replace(" ", "  ", 1)))
        if variant == name:
            variant = name.upper() if name.upper() != name else name + "."
        prefix = company["company_id"].rsplit("C", 1)[0]
        new_id = f"{prefix}C{len(self.data.companies) + 1:05d}"
        copy = {**company, "company_id": new_id, "name": variant}
        moved = self.rng.sample(own, max(1, len(own) // 3))
        for row in moved:
            row["company_id"] = new_id
        self.note("companies", new_id, "name", "name_variant", name)
        self.note("companies", new_id, "company_id", "name_variant", company["company_id"])
        return copy

    def run(self, rate: float) -> None:
        rng = self.rng
        postings = cast(list[dict[str, Any]], self.data.postings)
        companies = cast(list[dict[str, Any]], self.data.companies)
        kinds, weights = list(COMPANY_DEFECTS), list(COMPANY_DEFECTS.values())
        for company in rng.sample(companies, round(len(companies) * rate)):
            kind = rng.choices(kinds, weights)[0]
            variant = self.company_variant(company, postings) if kind == "name_variant" else None
            if variant is not None:
                companies.append(variant)
                continue
            fields = [field for field in COMPANY_MISSING if company[field] is not None]
            if fields:
                field = rng.choice(fields)
                self.note("companies", company["company_id"], field, "missing", company[field])
                company[field] = None
        kinds, weights = list(POSTING_DEFECTS), list(POSTING_DEFECTS.values())
        duplicates = []
        for row in rng.sample(postings, round(len(postings) * rate)):
            kind = rng.choices(kinds, weights)[0]
            if kind == "duplicate":
                duplicates.append((row, self.duplicate(row)))
                continue
            for _ in range(3):  # another kind when this one does not apply to the row
                if self.posting(row, kind):
                    break
                kind = rng.choices(kinds[:-1], weights[:-1])[0]
        for row, copy in duplicates:  # right after the posting they copy, or a little further
            index = postings.index(row) + 1 + rng.randint(0, 5)
            postings.insert(min(index, len(postings)), copy)


def add_defects(data: JobDataset, rate: float, rng: random.Random) -> JobDataset:
    """`data` with defects in a share `rate` of its rows (in place), listed in `data.defects`."""
    if not 0 <= rate <= 1:
        raise ValueError(f"dirty must be in [0, 1], got {rate!r}")
    if rate:
        dirtier = _Dirtier(data, rng)
        dirtier.run(rate)
        data.defects.extend(dirtier.defects)
    return data
