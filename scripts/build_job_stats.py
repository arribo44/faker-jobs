#!/usr/bin/env python3
"""
Aggregate the (large, unversioned) job postings file into the small
statistics files versioned in DATAS/ (build_data.py only keeps the company
size range of posting_ranges.csv; the others feed the reports):

- DATAS/role_popularity.csv: number of postings per (Job Title, Role) -
  drives popularity-weighted role picking (UX/UI designers are posted far
  more often than archivists).
- DATAS/faker_benefits.csv: number of postings offering each individual
  benefit (the source packs 5 benefits per posting in a single string).
- DATAS/posting_ranges.csv: observed min/max of the numeric fields
  (experience, salary range bounds, company size, posting date).

The raw file is DATAS/job_descriptions2.csv (~1.6M postings, see
transform_job_descriptions.py), only needed to regenerate these statistics:

    python scripts/build_job_stats.py [path/to/job_descriptions2.csv]
"""
import csv
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(ROOT, "DATAS")
DEFAULT_INPUT = os.path.join(DATAS_DIR, "job_descriptions2.csv")

EXPERIENCE_RE = re.compile(r"(\d+) to (\d+) Years")
SALARY_RE = re.compile(r"\$(\d+)K-\$(\d+)K")


def collect(path):
    roles = Counter()
    benefits = Counter()
    ranges = {}

    def observe(field, value):
        low, high = ranges.get(field, (value, value))
        ranges[field] = (min(low, value), max(high, value))

    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            roles[(row["Job Title"], row["Role"])] += 1
            # "{'Health Insurance, Retirement Plans, ...'}"
            for benefit in row["Benefits"].strip("{}'").split(", "):
                benefits[benefit] += 1
            experience = EXPERIENCE_RE.fullmatch(row["Experience"])
            observe("experience_min", int(experience[1]))
            observe("experience_max", int(experience[2]))
            salary = SALARY_RE.fullmatch(row["Salary Range"])
            observe("salary_min_k", int(salary[1]))
            observe("salary_max_k", int(salary[2]))
            observe("company_size", int(row["Company Size"]))
            observe("posting_date", row["Job Posting Date"])
    return roles, benefits, ranges


def main(path):
    roles, benefits, ranges = collect(path)

    out = os.path.join(DATAS_DIR, "role_popularity.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["Job Title", "Role", "posting_count"])
        for (title, role), count in sorted(roles.items()):
            writer.writerow([title, role, count])
    print(f"Wrote {out} ({len(roles)} roles, {sum(roles.values())} postings)")

    out = os.path.join(DATAS_DIR, "faker_benefits.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["Benefit", "posting_count"])
        for benefit, count in sorted(benefits.items()):
            writer.writerow([benefit, count])
    print(f"Wrote {out} ({len(benefits)} benefits)")

    out = os.path.join(DATAS_DIR, "posting_ranges.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["field", "min", "max"])
        for field, (low, high) in ranges.items():
            writer.writerow([field, low, high])
    print(f"Wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        sys.exit(__doc__)
    main(sys.argv[1] if len(sys.argv) == 2 else DEFAULT_INPUT)
