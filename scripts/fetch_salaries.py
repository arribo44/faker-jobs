#!/usr/bin/env python3
"""
Fetch the earnings and labour figures used for the posting salaries and
contracts (build_occupations.py) and cache them in DATAS/salaries/:

- eurostat_ses2022.json: Eurostat Structure of Earnings Survey 2022, mean
  gross annual earnings in national currency (EUR, CHF for Switzerland;
  both sexes; all enterprise sizes, or those of 10 employees or more where
  only those are published, as for France and Italy) for France, Germany,
  Spain, Italy and the countries of COUNTRY_LOCALES with their own
  earnings (Belgium, Austria, Luxembourg, Ireland, Switzerland):
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
- oecd_wages.json: OECD average annual wages (full-time equivalent
  employees, national currency, current prices; DSD_EARNINGS@AV_AN_WAGE)
  and statutory minimum wages (yearly, national currency, current prices;
  DSD_EARNINGS@MW_CURP), 2022 onwards, for the countries of the locales:
  the earnings of the countries without a survey of their own (Canada,
  Mexico, Chile, Colombia, United Kingdom, Australia, New Zealand) are those
  of the country of their language scaled by the ratio of the average wages.

All are public APIs that need no key. Re-run when a newer survey is out.
"""
import csv
import io
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALARY_DIR = os.path.join(ROOT, "DATAS", "salaries")
EUROSTAT_PATH = os.path.join(SALARY_DIR, "eurostat_ses2022.json")
LFS_PATH = os.path.join(SALARY_DIR, "eurostat_lfs.json")
BLS_PATH = os.path.join(SALARY_DIR, "bls_oews.json")
OECD_PATH = os.path.join(SALARY_DIR, "oecd_wages.json")
LFS_YEAR = "2025"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?format=JSON&lang=EN"
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"
COUNTRIES = ("FR", "DE", "ES", "IT", "BE", "AT", "LU", "IE", "CH")
OECD_URL = "https://sdmx.oecd.org/public/rest/data/OECD.ELS.SAE,DSD_EARNINGS@{dataset},/all?startPeriod={start}&format=csv"
OECD_START = "2022"
# ISO 3166 alpha-3 codes of the OECD data → alpha-2.
OECD_COUNTRIES = {"FRA": "FR", "DEU": "DE", "ESP": "ES", "ITA": "IT", "USA": "US", "BEL": "BE", "AUT": "AT",
                  "LUX": "LU", "IRL": "IE", "CHE": "CH", "CAN": "CA", "MEX": "MX", "CHL": "CL", "COL": "CO",
                  "GBR": "GB", "AUS": "AU", "NZL": "NZ"}

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


def get_text(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=120) as r:
        return r.read().decode("utf-8")


def oecd(dataset, measure_filter):
    """{country (alpha-2): {year: value}} of an OECD earnings dataset (CSV),
    for the rows that pass `measure_filter(row)`."""
    rows = csv.DictReader(io.StringIO(get_text(OECD_URL.format(dataset=dataset, start=OECD_START))))
    result = {}
    for row in rows:
        code = OECD_COUNTRIES.get(row["REF_AREA"])
        if code and measure_filter(row) and row["OBS_VALUE"]:
            result.setdefault(code, {})[row["TIME_PERIOD"]] = float(row["OBS_VALUE"])
    return result


def fetch_oecd():
    # National currency (not USD PPP), current prices, yearly amounts.
    average = oecd("AV_AN_WAGE", lambda row: row["UNIT_MEASURE"] != "USD_PPP" and row["PRICE_BASE"] == "V")
    minimum = oecd("MW_CURP", lambda row: row["PAY_PERIOD"] == "A" and row["PRICE_BASE"] == "V")
    missing = sorted(set(OECD_COUNTRIES.values()) - set(average))
    if missing:
        sys.exit(f"OECD: no average wages for {missing}")
    return {"source": "OECD average annual wages (AV_AN_WAGE) and minimum wages at current prices "
                      "(MW_CURP), national currency, yearly",
            "average_wage": dict(sorted(average.items())), "minimum_wage": dict(sorted(minimum.items()))}


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"wrote {path}", file=sys.stderr)


def main():
    os.makedirs(SALARY_DIR, exist_ok=True)
    # National currency: EUR in the euro area, CHF in Switzerland.
    common = {"sex": "T", "indic_se": "ERN", "unit": "NAC", "freq": "A", "time": "2022"}
    data = {
        "source": "Eurostat SES 2022, mean gross annual earnings, national currency (earn_ses22_49, earn_ses22_28)",
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
    save(OECD_PATH, fetch_oecd())


if __name__ == "__main__":
    main()
