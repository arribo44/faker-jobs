#!/usr/bin/env python3
"""
Build faker_jobs/data/jobs_data.json from the curated CSV files in DATAS/:

- faker_job_descriptions.csv: job titles, roles, descriptions, skills and
  responsibilities (376 roles in 147 job titles)
- role_popularity.csv, faker_benefits.csv, posting_ranges.csv: statistics
  measured on the full postings file (see build_job_stats.py)
- faker_qualifications.csv, faker_contract.csv, faker_job_portal.csv
- faker_locations.csv: one city per country, geocoded (see geocode_locations.py)
- faker_firms.csv: companies and their profile (see transform_firms.py)

Re-run this script whenever DATAS/ changes.
"""
import csv
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(ROOT, "DATAS")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "jobs_data.json")

# Currency of the salary ranges in the source dataset ("$59K-$104K").
SALARY_CURRENCY = "USD"

# Number of benefits listed in every source posting.
BENEFITS_PER_POSTING = 5


def read_csv(name):
    with open(os.path.join(DATAS_DIR, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_column(name):
    """Values of a one-column CSV file (header excluded), blank lines skipped."""
    with open(os.path.join(DATAS_DIR, name), encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        return [row[0].strip() for row in reader if row and row[0].strip()]


def build_roles():
    popularity = {(row["Job Title"], row["Role"]): int(row["posting_count"])
                  for row in read_csv("role_popularity.csv")}
    roles = []
    for row in read_csv("faker_job_descriptions.csv"):
        key = (row["Job Title"], row["Role"])
        if key not in popularity:
            raise ValueError(f"No popularity for role {key!r}: re-run build_job_stats.py")
        roles.append({
            "job_title": row["Job Title"],
            "role": row["Role"],
            "description": row["Job Description"],
            "skills": row["skills"],
            "responsibilities": row["Responsibilities"],
            "posting_count": popularity[key],
        })
    names = [role["role"] for role in roles]
    if len(set(names)) != len(names):
        raise ValueError("Role names must be unique (they are used as lookup keys)")
    return roles


def build_ranges():
    ranges = {}
    for row in read_csv("posting_ranges.csv"):
        low, high = row["min"], row["max"]
        if row["field"] != "posting_date":
            low, high = int(low), int(high)
        ranges[row["field"]] = [low, high]
    return ranges


def optional(value):
    """Empty CSV cells become null rather than ''."""
    value = value.strip()
    return value or None


def build_data():
    roles = build_roles()
    return {
        "meta": {
            "source": "Job Description Dataset (Kaggle, ~1.6M synthetic postings)",
            "salary_currency": SALARY_CURRENCY,
            "benefits_per_posting": BENEFITS_PER_POSTING,
        },
        "job_titles": sorted({role["job_title"] for role in roles}),
        "roles": roles,
        "qualifications": {row["Code"]: row["Description"] for row in read_csv("faker_qualifications.csv")},
        "work_types": read_column("faker_contract.csv"),
        "job_portals": read_column("faker_job_portal.csv"),
        "benefits": {row["Benefit"]: int(row["posting_count"]) for row in read_csv("faker_benefits.csv")},
        "locations": [
            {
                "city": row["location"],
                "country": row["Country"],
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }
            for row in read_csv("faker_locations.csv")
        ],
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
    print(f"Wrote {OUTPUT_PATH}: {len(data['roles'])} roles in {len(data['job_titles'])} job titles, "
          f"{len(data['companies'])} companies, {len(data['locations'])} locations, "
          f"{len(data['benefits'])} benefits")


if __name__ == "__main__":
    main()
