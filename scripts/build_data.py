#!/usr/bin/env python3
"""
Build faker_jobs/data/jobs_data.json from the curated CSV files in DATAS/
(Job Description Dataset, Kaggle). Only its companies are kept: jobs come
from the ROME / ESCO occupations (see build_occupations.py), cities from
GeoNames (see build_cities.py, which reads the Kaggle country names of
faker_locations.csv).

- faker_firms.csv: companies and their profile (see scripts/transform_firms.py)
- posting_ranges.csv: the company size range measured on the full postings
  file (see build_job_stats.py)

Re-run this script whenever DATAS/ changes, then build_occupations.py (it
matches the companies to the activity sectors).
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(ROOT, "DATAS")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "jobs_data.json")

# Ranges of posting_ranges.csv kept in the package.
KEPT_RANGES = ("company_size",)


def read_csv(name):
    with open(os.path.join(DATAS_DIR, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_ranges():
    return {row["field"]: [int(row["min"]), int(row["max"])]
            for row in read_csv("posting_ranges.csv") if row["field"] in KEPT_RANGES}


def optional(value):
    """Empty CSV cells become null rather than ''."""
    value = value.strip()
    return value or None


def build_data():
    return {
        "meta": {
            "source": "Job Description Dataset (Kaggle, ~1.6M synthetic postings): companies",
        },
        "companies": [
            {
                "company": row["company"],
                "sector": optional(row["sector"]),
                "industry": optional(row["industry"]),
                "city": optional(row["city"]),
                "state": optional(row["state"]),
                "zip": optional(row["zip"]),
                "website": optional(row["website"]),
                "ticker": optional(row["ticker"]),
                "ceo": optional(row["ceo"]),
            }
            for row in read_csv("faker_firms.csv")
        ],
        "ranges": build_ranges(),
    }


def main():
    data = build_data()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write("\n")
    print(f"Wrote {OUTPUT_PATH}: {len(data['companies'])} companies")


if __name__ == "__main__":
    main()
