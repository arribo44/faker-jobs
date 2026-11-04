#!/usr/bin/env python3
"""
Draw a representative sample of the (large, unversioned) job postings file,
for exploration and for scripts/build_report.py:

- DATAS/job_sample.csv: SAMPLE_SIZE postings drawn uniformly at random
  without replacement (reservoir sampling, fixed seed: re-running gives the
  same sample), in the same format as the source (';', every field quoted)
  and in source order.
- DATAS/job_full_counts.json: value counts of the analysed fields over the
  WHOLE file, so the report can check how close the sample is to it.

    python scripts/build_sample.py [path/to/job_descriptions2.csv] [sample_size]
"""
import csv
import json
import os
import random
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(ROOT, "DATAS")
DEFAULT_INPUT = os.path.join(DATAS_DIR, "job_descriptions2.csv")
SAMPLE_PATH = os.path.join(DATAS_DIR, "job_sample.csv")
COUNTS_PATH = os.path.join(DATAS_DIR, "job_full_counts.json")

SAMPLE_SIZE = 20000
SEED = 20261104

EXPERIENCE_RE = re.compile(r"(\d+) to (\d+) Years")
SALARY_RE = re.compile(r"\$(\d+)K-\$(\d+)K")

# Width of the company-size bins (number of employees).
COMPANY_SIZE_BIN = 10000


def derived_fields(row):
    """The analysed fields of a posting, as (field, value) pairs. Shared with
    build_report.py so the sample and the full file are counted the same way."""
    experience = EXPERIENCE_RE.fullmatch(row["Experience"])
    salary = SALARY_RE.fullmatch(row["Salary Range"])
    fields = [
        ("country", row["Country"]),
        ("city", f"{row['location']} ({row['Country']})"),
        ("job_portal", row["Job Portal"]),
        ("work_type", row["Work Type"]),
        ("experience", row["Experience"]),
        ("experience_min", int(experience[1])),
        ("experience_max", int(experience[2])),
        ("qualification", row["Qualifications"]),
        ("preference", row["Preference"]),
        ("job_title", row["Job Title"]),
        ("role", row["Role"]),
        ("company", row["Company"]),
        ("salary_min_k", int(salary[1])),
        ("salary_max_k", int(salary[2])),
        ("company_size_bin", int(row["Company Size"]) // COMPANY_SIZE_BIN * COMPANY_SIZE_BIN),
        ("posting_month", row["Job Posting Date"][:7]),
    ]
    # "{'Health Insurance, Retirement Plans, ...'}"
    fields += [("benefit", benefit) for benefit in row["Benefits"].strip("{}'").split(", ")]
    return fields


def main(path, sample_size):
    rng = random.Random(SEED)
    counts = {}
    reservoir = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames
        for index, row in enumerate(reader):
            for field, value in derived_fields(row):
                counts.setdefault(field, Counter())[value] += 1
            if index < sample_size:
                reservoir.append((index, row))
            else:
                slot = rng.randrange(index + 1)
                if slot < sample_size:
                    reservoir[slot] = (index, row)
    total = index + 1

    reservoir.sort(key=lambda pair: pair[0])
    with open(SAMPLE_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(row for _, row in reservoir)
    print(f"Wrote {SAMPLE_PATH} ({len(reservoir)} of {total} postings, seed {SEED})")

    with open(COUNTS_PATH, "w", encoding="utf-8") as f:
        # JSON keys are strings: numeric values are written as such and
        # converted back by build_report.py.
        json.dump({"total": total, "counts": {field: dict(counter) for field, counter in counts.items()}},
                  f, ensure_ascii=False)
    print(f"Wrote {COUNTS_PATH}")


if __name__ == "__main__":
    if len(sys.argv) > 3:
        sys.exit(__doc__)
    main(sys.argv[1] if len(sys.argv) >= 2 else DEFAULT_INPUT,
         int(sys.argv[2]) if len(sys.argv) == 3 else SAMPLE_SIZE)
