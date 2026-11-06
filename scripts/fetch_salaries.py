#!/usr/bin/env python3
"""
Fetch the earnings and labour figures used for the posting salaries and
contracts (build_occupations.py) and cache them in DATAS/salaries/:

- eurostat_ses2022.json: Eurostat Structure of Earnings Survey 2022, mean
  gross annual earnings in EUR (both sexes; all enterprise sizes, or those
  of 10 employees or more where only those are published, as for France
  and Italy) for France, Germany, Spain and Italy:
  - by ISCO-08 major group and NACE Rev. 2 section (earn_ses22_49);
  - by ISCO-08 major group and age band (earn_ses22_28).
- eurostat_lfs.json: Eurostat Labour Force Survey, latest year, people
  aged 15 to 64, in thousands, by ISCO-08 major group, for the same
  countries: employees (lfsa_eegais), temporary employees (lfsa_etgais),
  part-time workers and all workers (lfsa_epgais), self-employed
  (lfsa_esgais). They set the contract mix of each occupation.
- bls_oews.json: U.S. Bureau of Labor Statistics, Occupational Employment
  and Wage Statistics, national mean annual wage by SOC major group, latest
  year available.

Both are public APIs that need no key. Re-run when a newer survey is out.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALARY_DIR = os.path.join(ROOT, "DATAS", "salaries")
EUROSTAT_PATH = os.path.join(SALARY_DIR, "eurostat_ses2022.json")
LFS_PATH = os.path.join(SALARY_DIR, "eurostat_lfs.json")
BLS_PATH = os.path.join(SALARY_DIR, "bls_oews.json")
LFS_YEAR = "2025"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?format=JSON&lang=EN"
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"
COUNTRIES = ("FR", "DE", "ES", "IT")

# SOC 2018 major groups (BLS OEWS occupation codes).
SOC_MAJOR_GROUPS = {
    "000000": "All occupations",
    "110000": "Management", "130000": "Business and financial operations",
    "150000": "Computer and mathematical", "170000": "Architecture and engineering",
    "190000": "Life, physical, and social science", "210000": "Community and social service",
    "230000": "Legal", "250000": "Educational instruction and library",
    "270000": "Arts, design, entertainment, sports, and media",
    "290000": "Healthcare practitioners and technical", "310000": "Healthcare support",
    "330000": "Protective service", "350000": "Food preparation and serving related",
    "370000": "Building and grounds cleaning and maintenance", "390000": "Personal care and service",
    "410000": "Sales and related", "430000": "Office and administrative support",
    "450000": "Farming, fishing, and forestry", "470000": "Construction and extraction",
    "490000": "Installation, maintenance, and repair", "510000": "Production",
    "530000": "Transportation and material moving",
}


def get_json(url, data=None):
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=120) as response:
        return json.load(response)


def eurostat_by_size(dataset, keep, **fixed):
    """`eurostat()` for all enterprise sizes, or for 10 employees or more in
    the countries that only publish those; {country: {"size": ..., "values": ...}}."""
    every = eurostat(dataset, keep, sizeclas="TOTAL", **fixed)
    large = eurostat(dataset, keep, sizeclas="GE10", **fixed)
    return {geo: {"size": "TOTAL", "values": every[geo]} if every[geo] else {"size": "GE10", "values": large[geo]}
            for geo in COUNTRIES}


def eurostat(dataset, keep, **fixed):
    """{country: {key: value}} of a JSON-stat dataset, `key` made of the `keep` dimensions
    ("OC2|Q"), the other dimensions set to `fixed` (filtered by the API too)."""
    query = "".join(f"&geo={geo}" for geo in COUNTRIES) + "".join(f"&{dim}={code}" for dim, code in fixed.items())
    raw = get_json(EUROSTAT_URL.format(dataset=dataset) + query)
    ids, sizes = raw["id"], raw["size"]
    positions = {dim: {code: index for code, index in raw["dimension"][dim]["category"]["index"].items()}
                 for dim in ids}
    codes = {dim: {index: code for code, index in positions[dim].items()} for dim in ids}
    result = {geo: {} for geo in COUNTRIES}
    for flat, value in raw["value"].items():
        flat, coords = int(flat), {}
        for dim, size in zip(reversed(ids), reversed(sizes), strict=True):
            coords[dim] = codes[dim][flat % size]
            flat //= size
        if all(coords[dim] == code for dim, code in fixed.items()):
            result[coords["geo"]]["|".join(coords[dim] for dim in keep)] = value
    return result


def fetch_lfs():
    """{country: {table: {ISCO major group ("OC1"... and "TOTAL"): thousands}}}."""
    common = {"unit": "THS_PER", "sex": "T", "age": "Y15-64", "freq": "A", "time": LFS_YEAR}
    tables = {
        "employees": eurostat("lfsa_eegais", ("isco08",), **common),
        "temporary": eurostat("lfsa_etgais", ("isco08",), **common),
        "part_time": eurostat("lfsa_epgais", ("isco08",), worktime="PT", **common),
        "employed": eurostat("lfsa_epgais", ("isco08",), worktime="TOTAL", **common),
        "self_employed": eurostat("lfsa_esgais", ("isco08",), wstatus="SELF", **common),
    }
    result = {geo: {name: table[geo] for name, table in tables.items()} for geo in COUNTRIES}
    for geo, entry in result.items():
        missing = [name for name, values in entry.items() if "TOTAL" not in values]
        if missing:
            sys.exit(f"Eurostat LFS {LFS_YEAR}: no {missing} total for {geo}")
    return {"source": f"Eurostat LFS {LFS_YEAR}, aged 15-64, thousands (lfsa_eegais, lfsa_etgais, "
                      "lfsa_epgais, lfsa_esgais)", "year": LFS_YEAR, "values": result}


def fetch_bls():
    series = {f"OEUN0000000000000{soc}04": soc for soc in SOC_MAJOR_GROUPS}  # 04: annual mean wage
    raw = get_json(BLS_URL, {"seriesid": list(series)})
    if raw["status"] != "REQUEST_SUCCEEDED":
        sys.exit(f"BLS API: {raw['status']} {raw.get('message')}")
    wages, years = {}, set()
    for item in raw["Results"]["series"]:
        if not item["data"]:
            sys.exit(f"BLS API: no data for {item['seriesID']}")
        latest = max(item["data"], key=lambda row: row["year"])
        years.add(latest["year"])
        wages[series[item["seriesID"]]] = float(latest["value"])
    if len(years) != 1:
        sys.exit(f"BLS API: series from different years {sorted(years)}")
    return {"year": years.pop(), "labels": SOC_MAJOR_GROUPS, "mean_annual_wage": wages}


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"wrote {path}", file=sys.stderr)


def main():
    os.makedirs(SALARY_DIR, exist_ok=True)
    common = {"sex": "T", "indic_se": "ERN", "unit": "EUR", "freq": "A", "time": "2022"}
    data = {
        "source": "Eurostat SES 2022, mean gross annual earnings, EUR (earn_ses22_49, earn_ses22_28)",
        "by_isco_section": eurostat_by_size("earn_ses22_49", ("isco08", "nace_r2"), **common),
        "by_isco_age": eurostat_by_size("earn_ses22_28", ("isco08", "age"), **common),
    }
    for table in ("by_isco_section", "by_isco_age"):
        empty = [geo for geo, entry in data[table].items() if not entry["values"]]
        if empty:
            sys.exit(f"Eurostat: no {table} data for {empty}")
    save(EUROSTAT_PATH, data)
    save(LFS_PATH, fetch_lfs())
    save(BLS_PATH, fetch_bls())


if __name__ == "__main__":
    main()
