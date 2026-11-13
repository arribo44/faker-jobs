#!/usr/bin/env python3
"""
Fetch the official share of employees by enterprise size class and
industry, used by build_companies.py to pick the size of the hiring
companies (LinkedIn, the source of the companies, lists few small ones),
and cache it in DATAS/business_sizes/sizes.json:

- France, Germany, Spain, Italy, and Belgium, Austria, Luxembourg, Ireland
  and Switzerland where Eurostat has enough figures (OPTIONAL_COUNTRIES:
  left out with a warning otherwise, their companies then keep the
  LinkedIn shares): Eurostat structural business statistics
  (sbs_sc_ovw), persons employed (EMP_NR: employees and working owners;
  employees alone are not published by size for services) by NACE Rev. 2
  section (B to R: market economy, without agriculture, public
  administration and other services) and size class 2-9 (one-person
  businesses left out: they do not hire), 10-49, 50-249, 250+ persons
  employed; latest year with the figures (a single confidential class is
  the total minus the others; where only 0-9 is published, 2-9 is estimated
  with the country's share of 2-9 in 0-9 elsewhere). A section with two
  confidential classes or more (France: mining, water supply and waste)
  takes the split of the European Union (EU27_2020), brought to the
  persons employed of the section in the country.
  Also the persons employed of every NACE division and group (all sizes,
  latest year: "employment_by_nace"), the weight of the NAF activities of
  the French companies (build_occupations.py).
- United States: Census Statistics of US Businesses 2022, employment by
  NAICS sector and enterprise size (employer firms; sizes up to 10,000+),
  from two spreadsheets saved in DATAS/business_sizes/ (no API):
  us_state_naics_detailedsizes_2022.xlsx and
  us_naicssector_large_emplsize_2022.xlsx, from
  https://www.census.gov/data/tables/2022/econ/susb/2022-susb-annual.html
  (run with --download to fetch them).
- United Kingdom: Business population estimates 2026 (Department for
  Business and Trade), table 5, private sector employment by SIC section
  and employee size band (businesses with employees), from
  BPE_2026_detailed_tables.xlsx, saved in DATAS/business_sizes/ (--download).

- Canada, New Zealand: OECD Structural and Demographic Business Statistics
  (SDBS, DSD_SDBSBSC_ISIC4@DF_SDBS_ISIC4), employees (Canada) or persons
  employed (New Zealand) by ISIC Rev. 4 section (as NACE's) and size class
  1-9, 10-49, 50-249, 250+ (New Zealand: 1-9, 10+ only), latest year with
  figures. The OECD has no such
  split for Mexico, Chile, Colombia and Australia: their companies keep the
  LinkedIn shares.

NAICS sectors and the UK section groups are mapped to NACE sections. Every
country gets {section: [employees of each size group]} with its own size
groups (`groups`, [low, high] employees, high None for no upper bound).

Needs openpyxl (`pip install -e ".[build]"`).
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZES_DIR = os.path.join(ROOT, "DATAS", "business_sizes")
OUTPUT_PATH = os.path.join(SIZES_DIR, "sizes.json")
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"

EUROSTAT_URL = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sbs_sc_ovw"
                "?format=JSON&lang=EN&indic_sbs=EMP_NR")
EUROSTAT_COUNTRIES = {"FR": "France", "DE": "Germany", "ES": "Spain", "IT": "Italy", "BE": "Belgium",
                      "AT": "Austria", "LU": "Luxembourg", "IE": "Ireland", "CH": "Switzerland"}
OPTIONAL_COUNTRIES = {"Belgium", "Austria", "Luxembourg", "Ireland", "Switzerland", "Canada", "New Zealand"}
MIN_SECTIONS = 13
EU_GEO = "EU27_2020"
# Eurostat size classes, and the group of EUROSTAT_GROUPS of each.
# 2-9: without the one-person businesses (0_1), which do not hire.
EUROSTAT_CLASSES = {"2-9": 0, "10-19": 1, "20-49": 1, "50-249": 2, "GE250": 3}
EUROSTAT_GROUPS = [[2, 9], [10, 49], [50, 249], [250, None]]

US_FILES = {
    "us_state_naics_detailedsizes_2022.xlsx":
        "https://www2.census.gov/programs-surveys/susb/tables/2022/us_state_naics_detailedsizes_2022.xlsx",
    "us_naicssector_large_emplsize_2022.xlsx":
        "https://www2.census.gov/programs-surveys/susb/tables/2022/us_naicssector_large_emplsize_2022.xlsx",
}
UK_FILE = ("BPE_2026_detailed_tables.xlsx",
           "https://assets.publishing.service.gov.uk/media/6ae3162ec591dbfc31fb67f0/BPE_2026_detailed_tables.xlsx")

# The groups of the LinkedIn size classes of the companies (1-10, 11-50,
# 51-200, 201-500, 501-1,000, 1,001-5,000, 5,001-10,000, 10,001+).
US_GROUPS = [[1, 9], [10, 49], [50, 199], [200, 499], [500, 999], [1000, 4999], [5000, 9999], [10000, None]]
# SUSB size rows ("02: <5 employees") → index into US_GROUPS.
US_DETAILED_ROWS = {"02": 0, "03": 0, "04": 1, "05": 1, "07": 1, "08": 1, "09": 1, "10": 1, "11": 1,
                    "12": 2, "13": 2, "14": 2, "15": 2, "16": 3, "17": 3, "18": 3, "20": 4, "21": 4,
                    "22": 5, "23": 5, "24": 5, "25": 5}
US_LARGE_ROWS = {"09": 6, "10": 7, "11": 7}  # 5,000-9,999, 10,000-19,999, 20,000+
# NACE section → NAICS sectors (approximate: water and waste with utilities,
# head offices with professional services).
NAICS_SECTIONS = {
    "A": ["11"], "B": ["21"], "C": ["31-33"], "D": ["22"], "E": ["22"], "F": ["23"], "G": ["42", "44-45"],
    "H": ["48-49"], "I": ["72"], "J": ["51"], "K": ["52"], "L": ["53"], "M": ["54", "55"], "N": ["56"],
    "P": ["61"], "Q": ["62"], "R": ["71"], "S": ["81"],
}

UK_GROUPS = [[1, 9], [10, 49], [50, 199], [200, 499], [500, None]]
UK_BANDS = {"1": 0, "2 to 4": 0, "5 to 9": 0, "10 to 19": 1, "20 to 49": 1, "50 to 99": 2, "100 to 199": 2,
            "200 to 249": 3, "250 to 499": 3, "500 or more": 4}


def download():
    os.makedirs(SIZES_DIR, exist_ok=True)
    for name, url in [*US_FILES.items(), UK_FILE]:
        print(f"Downloading {url}", file=sys.stderr)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=300) as response, \
                open(os.path.join(SIZES_DIR, name), "wb") as f:
            f.write(response.read())


def read_eurostat():
    """{(geo, NACE code, size class, year): persons employed}, from the Eurostat API."""
    url = EUROSTAT_URL + "".join(f"&geo={geo}" for geo in [*EUROSTAT_COUNTRIES, EU_GEO])
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=300) as r:
        raw = json.load(r)
    ids, sizes = raw["id"], raw["size"]
    codes = {dim: {index: code for code, index in raw["dimension"][dim]["category"]["index"].items()} for dim in ids}
    values = {}
    for flat, value in raw["value"].items():
        flat, coords = int(flat), {}
        for dim, size in zip(reversed(ids), reversed(sizes), strict=True):
            coords[dim] = codes[dim][flat % size]
            flat //= size
        values[(coords["geo"], coords["nace_r2"], coords["size_emp"], coords["time"])] = value
    return values


def size_groups(values, geo, sections, years):
    """{section: {"year": year, "employees": [persons employed of each EUROSTAT_GROUPS]}}
    for the sections of `geo` with figures, latest year first."""
    # Where only 0-9 is published (French industry), 2-9 is estimated with the
    # country's share of 2-9 in 0-9 in the other sections.
    both = [(values[(geo, s, "2-9", y)], values[(geo, s, "0-9", y)]) for s in sections for y in years
            if (geo, s, "2-9", y) in values and (geo, s, "0-9", y) in values]
    micro_ratio = sum(pair[0] for pair in both) / sum(pair[1] for pair in both)
    found = {}
    for section in sections:
        for year in years:
            row = [values.get((geo, section, size, year)) for size in EUROSTAT_CLASSES]
            total = values.get((geo, section, "TOTAL", year))
            micro = values.get((geo, section, "0-9", year))
            if row[0] is None and micro is not None:
                row[0] = round(micro * micro_ratio)
            if total is not None and micro is not None:
                total -= micro - row[0]  # without the one-person businesses
            missing = [i for i, value in enumerate(row) if value is None]
            if len(missing) == 1 and total is not None:
                row[missing[0]] = max(total - sum(value for value in row if value is not None), 0)
                missing = []
            if not missing:
                grouped = [0] * len(EUROSTAT_GROUPS)
                for size, value in zip(EUROSTAT_CLASSES.values(), row, strict=True):
                    grouped[size] += value
                found[section] = {"year": year, "employees": grouped}
                break
    return found


def section_employment(values, geo, section, years):
    """(persons employed of `section` in `geo`, year): the section's total, else
    the sum of its divisions (all sizes); None without figures."""
    for year in years:
        if (geo, section, "TOTAL", year) in values:
            return values[(geo, section, "TOTAL", year)], year
        divisions = [value for (g, nace, size, y), value in values.items()
                     if g == geo and y == year and size == "TOTAL" and len(nace) == 3 and nace[0] == section]
        if divisions:
            return sum(divisions), year
    return None


def fetch_eurostat():
    """{country: {"sections": {section: [employees of each EUROSTAT_GROUPS]}, "years": ...,
    "employment_by_nace": ...}}."""
    values = read_eurostat()
    sections = sorted({key[1] for key in values if len(key[1]) == 1})
    years = sorted({key[3] for key in values}, reverse=True)
    europe = size_groups(values, EU_GEO, sections, years)
    result = {}
    for geo, country in EUROSTAT_COUNTRIES.items():
        found = size_groups(values, geo, sections, years)
        for section in sorted(set(europe) - set(found)):
            # The EU split, brought to the country's persons employed in the section
            # (without the one-person businesses, at the EU rate).
            employed = section_employment(values, geo, section, years)
            eu_total = section_employment(values, EU_GEO, section, [europe[section]["year"]])
            if employed is None or eu_total is None:
                continue
            scale = employed[0] / eu_total[0]
            found[section] = {"year": f"{employed[1]} (EU27_2020 split of {europe[section]['year']})",
                              "employees": [round(value * scale) for value in europe[section]["employees"]]}
        # Employment of every NACE division and group (all sizes, latest year), the
        # weight of the NAF / NACE activities of the companies (build_occupations.py).
        employment = {}
        for (key_geo, nace, size, _year), value in sorted(values.items(), key=lambda item: item[0][3]):
            if key_geo == geo and size == "TOTAL" and len(nace) in (3, 4):
                employment[nace] = value
        result[country] = {"employment_by_nace": dict(sorted(employment.items())),
                           "source": "Eurostat SBS (sbs_sc_ovw), persons employed (EMP_NR) by size class "
                                     "of persons employed, without one-person businesses", "groups": EUROSTAT_GROUPS,
                           "sections": {section: entry["employees"] for section, entry in sorted(found.items())},
                           "years": {section: entry["year"] for section, entry in sorted(found.items())}}
    return result


def sheet_rows(name, sheet=None):
    import openpyxl
    workbook = openpyxl.load_workbook(os.path.join(SIZES_DIR, name), read_only=True, data_only=True)
    try:
        worksheet = workbook[sheet] if sheet else workbook.worksheets[0]
        return list(worksheet.iter_rows(values_only=True))
    finally:
        workbook.close()


def read_us():
    """{"groups": US_GROUPS, "sections": {NACE section: [employment of each group]}}."""
    by_naics = {}
    for row in sheet_rows("us_state_naics_detailedsizes_2022.xlsx"):
        if row[0] == "00" and isinstance(row[4], str) and row[4][:2] in US_DETAILED_ROWS:
            group = US_DETAILED_ROWS[row[4][:2]]
            by_naics.setdefault(row[2], [0] * len(US_GROUPS))[group] += row[7]
    for row in sheet_rows("us_naicssector_large_emplsize_2022.xlsx"):
        if isinstance(row[2], str) and row[2][:2] in US_LARGE_ROWS and row[0] in by_naics:
            by_naics[row[0]][US_LARGE_ROWS[row[2][:2]]] += row[5]
    sections = {}
    for section, sectors in NAICS_SECTIONS.items():
        sections[section] = [sum(by_naics[sector][i] for sector in sectors) for i in range(len(US_GROUPS))]
    return {"source": "Census Statistics of US Businesses 2022, employment by enterprise employment size",
            "groups": US_GROUPS, "sections": sections}


def read_uk():
    """{"groups": UK_GROUPS, "sections": {NACE section: [employment (thousands) of each group]}}."""
    sections, current = {}, None
    for row in sheet_rows(UK_FILE[0], "Table 5"):
        label = row[0]
        if isinstance(label, str) and row[1] is None and label[:1].isupper() and label[1:2] in (" ", ","):
            # "B, D and E Mining..." / "C Manufacturing": the sections of the rows below.
            letters = label.split(" ")[0].rstrip(",")
            current = [letters] + ([part.strip(" ,") for part in label.split(" ")[1:4]
                                    if len(part.strip(" ,")) == 1 and part.strip(" ,").isupper()]
                                   if label[1] == "," else [])
            for section in current:
                sections[section] = [0] * len(UK_GROUPS)
        elif current and str(label).strip() in UK_BANDS and isinstance(row[2], (int, float)):
            for section in current:
                sections[section][UK_BANDS[str(label).strip()]] += row[2]
    return {"source": "Business population estimates for the UK and regions 2026 (Department for Business and "
                      "Trade), table 5, employment of businesses with employees", "groups": UK_GROUPS,
            "sections": sections}


OECD_SDBS_URL = ("https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_SDBSBSC_ISIC4@DF_SDBS_ISIC4,"
                 "/A.{areas}.EMPE+EMPN...?startPeriod=2018&format=csv")
# OECD country -> (country, measure: EMPE employees, EMPN persons employed,
# {size class: [low, high] employees}, the size groups it publishes by section).
OECD_COUNTRIES = {
    "CAN": ("Canada", "EMPE", {"S1T9": [1, 9], "S10T49": [10, 49], "S50T249": [50, 249], "S_GE250": [250, None]}),
    "NZL": ("New Zealand", "EMPN", {"S1T9": [1, 9], "S_GE10": [10, None]}),
}


def read_oecd():
    """{country: {"groups": [low, high] employees, "sections": {NACE section: [employment of each group]}}}."""
    import csv
    import io

    url = OECD_SDBS_URL.format(areas="+".join(OECD_COUNTRIES))
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=300) as r:
        rows = list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
    values = {}
    for row in rows:
        country, measure, classes = OECD_COUNTRIES[row["REF_AREA"]]
        if row["MEASURE"] == measure and row["SIZE_CLASS"] in classes and row["OBS_VALUE"]:
            values[(country, row["ACTIVITY"], row["SIZE_CLASS"], row["TIME_PERIOD"])] = float(row["OBS_VALUE"])
    result = {}
    for country, measure, classes in OECD_COUNTRIES.values():
        sections = {}
        activities = {key[1] for key in values if key[0] == country}
        for activity in sorted(activities):
            # Sections ('C'), or joined ones ('D_E': the same split for each).
            letters = activity.split("_")
            if not all(len(letter) == 1 and letter.isalpha() for letter in letters):
                continue
            years = sorted({key[3] for key in values if key[:2] == (country, activity)}, reverse=True)
            for year in years:
                row = [values.get((country, activity, size, year)) for size in classes]
                if None not in row:
                    for letter in letters:
                        sections[letter] = [round(value) for value in row]
                    break
        employment = "employees" if measure == "EMPE" else "persons employed"
        result[country] = {"source": f"OECD SDBS (DSD_SDBSBSC_ISIC4), {employment} by ISIC Rev. 4 section "
                                     "and size class", "groups": list(classes.values()), "sections": sections}
    return result


def main():
    if "--download" in sys.argv:
        download()
    data = {**fetch_eurostat(), "United States": read_us(), "United Kingdom": read_uk(), **read_oecd()}
    for country, entry in list(data.items()):
        if len(entry["sections"]) < MIN_SECTIONS:
            if country not in OPTIONAL_COUNTRIES:
                sys.exit(f"{country}: only {sorted(entry['sections'])} sections")
            print(f"{country}: left out, only {sorted(entry['sections'])} sections", file=sys.stderr)
            del data[country]
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    for country, entry in data.items():
        total = [sum(values[i] for values in entry["sections"].values()) for i in range(len(entry["groups"]))]
        shares = [round(value / sum(total), 3) for value in total]
        print(f"{country}: {len(entry['sections'])} sections, employees by size group {shares}")
    print(f"→ {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
