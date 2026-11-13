#!/usr/bin/env python3
"""
Fetch the earnings and labour figures used for the posting salaries and
contracts (build_occupations.py) and cache them in DATAS/salaries/:

- eurostat_ses2022.json: Eurostat Structure of Earnings Survey 2022, mean
  gross annual earnings in national currency (EUR, CHF for Switzerland;
  both sexes; all enterprise sizes, or those of 10 employees or more where
  only those are published, as for France and Italy) for France, Germany,
  Spain, Italy, Portugal, the Netherlands, Poland and the countries of
  COUNTRY_CONDITIONS with their own earnings (Belgium, Austria, Luxembourg,
  Ireland, Switzerland), and every other country of the survey:
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

- ilostat.json: ILOSTAT (International Labour Organization), for every
  country it covers: average monthly earnings of employees by ISCO-08 major
  group, local currency (DF_EAR_EMTA_SEX_OCU_NB), latest year (annual
  figure, else the mean of the quarters of the latest year); statutory
  monthly minimum wage, local currency (DF_EAR_INEE_NOC_NB), latest year
  (the lowest where there are several). With the currency ILOSTAT notes.
- worldbank_gdp.json: World Bank GDP per capita, current local currency
  (NY.GDP.PCAP.CN), 2010 onwards: it brings the ILOSTAT figures of past
  years to the latest one, and gives an earnings level to the countries
  ILOSTAT does not cover; its growth gives the yearly growth of the salaries
  (job datasets over several years).
- eurostat_telework.json: Eurostat LFS, employees aged 15-64 working from
  home usually / sometimes, % of the employees (lfsa_ehomp), latest year,
  every country of the survey and the EU: the share of postings offering
  hybrid or full remote work.

All are public APIs that need no key. Re-run when a newer survey is out;
`fetch_salaries.py telework` (or another name of FETCHERS) only fetches that one.
"""
import csv
import io
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALARY_DIR = os.path.join(ROOT, "DATAS", "salaries")
EUROSTAT_PATH = os.path.join(SALARY_DIR, "eurostat_ses2022.json")
LFS_PATH = os.path.join(SALARY_DIR, "eurostat_lfs.json")
BLS_PATH = os.path.join(SALARY_DIR, "bls_oews.json")
OECD_PATH = os.path.join(SALARY_DIR, "oecd_wages.json")
ILOSTAT_PATH = os.path.join(SALARY_DIR, "ilostat.json")
WORLD_BANK_PATH = os.path.join(SALARY_DIR, "worldbank_gdp.json")
TELEWORK_PATH = os.path.join(SALARY_DIR, "eurostat_telework.json")
TELEWORK_COUNTRIES = ("EU27_2020", "BE", "BG", "CZ", "DK", "DE", "EE", "IE", "EL", "ES", "FR", "HR", "IT", "CY",
                      "LV", "LT", "LU", "HU", "MT", "NL", "AT", "PL", "PT", "RO", "SI", "SK", "FI", "SE", "IS",
                      "NO", "CH", "UK", "BA", "ME", "MK", "RS", "TR")
ILOSTAT_URL = "https://sdmx.ilo.org/rest/data/ILO,{dataflow}/?startPeriod={start}&format=csvfile"
ILOSTAT_START = "2012"
# Series that are not mean gross monthly earnings: left out.
ILOSTAT_LEFT_OUT = ("Central tendency measure: Median", "Accounting concept: Net", "Value type: Real values",
                    "Time unit: Per day")
WORLD_BANK_URL = ("https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CN"
                  "?format=json&date=2010:2030&per_page=20000")
LFS_YEAR = "2025"

EUROSTAT_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?format=JSON&lang=EN"
BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"
COUNTRIES = ("FR", "DE", "ES", "IT", "BE", "AT", "LU", "IE", "CH", "PT", "NL", "PL")
# Every country of the Structure of Earnings Survey 2022 (Eurostat codes: EL
# for Greece): the earnings of the countries without conditions of their own
# (countries.json); the Labour Force Survey is only fetched for COUNTRIES.
SES_COUNTRIES = COUNTRIES + ("AL", "BA", "BG", "CY", "CZ", "DK", "EE", "EL", "FI", "HR", "HU", "IS", "LT", "LV",
                             "MK", "MT", "NO", "RO", "RS", "SE", "SI", "SK")
# Countries that adopted the euro after 2022: their earnings in EUR, their currency now.
EURO_SINCE_2022 = ("BG", "HR")
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


def eurostat_by_size(dataset, keep, countries=COUNTRIES, **fixed):
    """`eurostat()` for all enterprise sizes, or for 10 employees or more in
    the countries that only publish those; {country: {"size": ..., "values": ...}}."""
    every = eurostat(dataset, keep, countries, sizeclas="TOTAL", **fixed)
    large = eurostat(dataset, keep, countries, sizeclas="GE10", **fixed)
    return {geo: {"size": "TOTAL", "values": every[geo]} if every[geo] else {"size": "GE10", "values": large[geo]}
            for geo in countries}


def eurostat(dataset, keep, countries=COUNTRIES, **fixed):
    """{country: {key: value}} of a JSON-stat dataset, `key` made of the `keep` dimensions
    ("OC2|Q"), the other dimensions set to `fixed` (filtered by the API too)."""
    query = "".join(f"&geo={geo}" for geo in countries) + "".join(f"&{dim}={code}" for dim, code in fixed.items())
    raw = get_json(EUROSTAT_URL.format(dataset=dataset) + query)
    ids, sizes = raw["id"], raw["size"]
    positions = {dim: {code: index for code, index in raw["dimension"][dim]["category"]["index"].items()}
                 for dim in ids}
    codes = {dim: {index: code for code, index in positions[dim].items()} for dim in ids}
    result = {geo: {} for geo in countries}
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
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=300) as r:
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


def ilostat_rows(dataflow):
    return list(csv.DictReader(io.StringIO(get_text(ILOSTAT_URL.format(dataflow=dataflow, start=ILOSTAT_START)))))


def ilostat_currency(note):
    """The currency code of an ILOSTAT indicator note ('... | INR: Indian rupee' -> 'INR')."""
    match = re.search(r"(?:^|\| )([A-Z]{3}): ", note or "")
    return match.group(1) if match else None


def latest_values(rows, key):
    """{country: (year, currency, {key(row): value})}: the values of the
    latest year, annual where published, else the mean of its quarters."""
    by_year = {}
    for row in rows:
        year = row["TIME_PERIOD"][:4]
        entry = by_year.setdefault((row["REF_AREA"], year), {"A": {}, "Q": {}, "currency": set()})
        entry["A" if row["FREQ"] == "A" else "Q"].setdefault(key(row), []).append(float(row["OBS_VALUE"]))
        entry["currency"].add(ilostat_currency(row["NOTE_INDICATOR"]))
    result = {}
    for (country, year), entry in sorted(by_year.items()):
        values = entry["A"] or entry["Q"]
        currency = entry["currency"] - {None}
        if len(currency) == 1:
            result[country] = (year, currency.pop(), {k: sum(v) / len(v) for k, v in values.items()})
    return result


def fetch_ilostat():
    earnings = [row for row in ilostat_rows("DF_EAR_EMTA_SEX_OCU_NB")
                if row["SEX"] == "SEX_T" and row["OCU"].startswith("OCU_ISCO08_") and row["OBS_VALUE"]
                and row["UNIT_MEASURE"] == "LC" and not any(note in (row["NOTE_INDICATOR"] or "")
                                                            for note in ILOSTAT_LEFT_OUT)]
    minimum = [row for row in ilostat_rows("DF_EAR_INEE_NOC_NB") if row["OBS_VALUE"] and row["UNIT_MEASURE"] == "LC"]
    by_group = latest_values(earnings, lambda row: row["OCU"].removeprefix("OCU_ISCO08_"))
    # Several minimum wages (sectoral, by region...): the lowest.
    lowest = latest_values(minimum, lambda row: f"{row['OBS_VALUE']}|{row['NOTE_INDICATOR']}")
    return {
        "source": "ILOSTAT (ILO): average monthly earnings of employees by ISCO-08 major group "
                  "(DF_EAR_EMTA_SEX_OCU_NB) and monthly minimum wage (DF_EAR_INEE_NOC_NB), local currency",
        "earnings": {country: {"year": year, "currency": currency, "monthly": values}
                     for country, (year, currency, values) in by_group.items() if "TOTAL" in values},
        "minimum_wage": {country: {"year": year, "currency": currency, "monthly": min(values.values())}
                         for country, (year, currency, values) in lowest.items()},
    }


def fetch_world_bank():
    raw = json.loads(get_text(WORLD_BANK_URL))
    values = {}
    for row in raw[1]:
        if row["value"] is not None and row["countryiso3code"]:
            values.setdefault(row["countryiso3code"], {})[row["date"]] = row["value"]
    return {"source": "World Bank, GDP per capita (current LCU), NY.GDP.PCAP.CN", "gdp_per_capita": values}


def fetch_telework():
    """{country (Eurostat code): {"usually": %, "sometimes": %}} of the latest year with both."""
    query = "".join(f"&geo={geo}" for geo in TELEWORK_COUNTRIES)
    raw = get_json(EUROSTAT_URL.format(dataset="lfsa_ehomp") + query
                   + "&sex=T&age=Y15-64&wstatus=SAL&unit=PC&freq=A&frequenc=USU&frequenc=SMT&sinceTimePeriod=2019")
    ids, sizes = raw["id"], raw["size"]
    codes = {dim: {index: code for code, index in raw["dimension"][dim]["category"]["index"].items()} for dim in ids}
    by_year = {}
    for flat, value in raw["value"].items():
        flat, coords = int(flat), {}
        for dim, size in zip(reversed(ids), reversed(sizes), strict=True):
            coords[dim] = codes[dim][flat % size]
            flat //= size
        key = {"USU": "usually", "SMT": "sometimes"}[coords["frequenc"]]
        by_year.setdefault(coords["geo"], {}).setdefault(coords["time"], {})[key] = value
    values = {}
    for geo, years in by_year.items():
        complete = [year for year, entry in years.items() if len(entry) == 2]
        if complete:
            year = max(complete)
            values[geo] = {"year": int(year), **years[year]}
    return {"source": "Eurostat LFS, employees aged 15-64 working from home usually / sometimes, "
                      "% of the employees (lfsa_ehomp)", "values": values}


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"wrote {path}", file=sys.stderr)


FETCHERS = {"telework": (TELEWORK_PATH, fetch_telework)}


def main():
    os.makedirs(SALARY_DIR, exist_ok=True)
    if len(sys.argv) > 1:
        for name in sys.argv[1:]:
            if name not in FETCHERS:
                sys.exit(f"unknown data {name!r}: one of {', '.join(FETCHERS)}")
            path, fetcher = FETCHERS[name]
            save(path, fetcher())
        return
    # National currency (EUR in the euro area, CHF in Switzerland...), EUR for the
    # countries that adopted it since.
    common = {"sex": "T", "indic_se": "ERN", "freq": "A", "time": "2022"}
    national = tuple(geo for geo in SES_COUNTRIES if geo not in EURO_SINCE_2022)
    data = {
        "source": "Eurostat SES 2022, mean gross annual earnings, national currency (EUR for "
                  f"{', '.join(EURO_SINCE_2022)}) (earn_ses22_49, earn_ses22_28)",
        "by_isco_section": {**eurostat_by_size("earn_ses22_49", ("isco08", "nace_r2"), national, unit="NAC", **common),
                            **eurostat_by_size("earn_ses22_49", ("isco08", "nace_r2"), EURO_SINCE_2022, unit="EUR",
                                               **common)},
        "by_isco_age": {**eurostat_by_size("earn_ses22_28", ("isco08", "age"), national, unit="NAC", **common),
                        **eurostat_by_size("earn_ses22_28", ("isco08", "age"), EURO_SINCE_2022, unit="EUR",
                                           **common)},
    }
    for table in ("by_isco_section", "by_isco_age"):
        empty = [geo for geo, entry in data[table].items() if not entry["values"]]
        if empty:
            sys.exit(f"Eurostat: no {table} data for {empty}")
    save(EUROSTAT_PATH, data)
    save(LFS_PATH, fetch_lfs())
    save(BLS_PATH, fetch_bls())
    save(OECD_PATH, fetch_oecd())
    save(ILOSTAT_PATH, fetch_ilostat())
    save(WORLD_BANK_PATH, fetch_world_bank())
    save(TELEWORK_PATH, fetch_telework())


if __name__ == "__main__":
    main()
