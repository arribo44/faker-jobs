#!/usr/bin/env python3
"""
Build the occupation data of each locale from the ROME 4.0 job directory
and its official ESCO crosswalk:

- faker_jobs/data/occupations_fr_FR.json.gz: the ROME 4.0 job sheets (France
  Travail), in French: job titles ("appellations"), activity sectors,
  know-how (savoir-faire), knowledge (savoirs), soft skills (savoir-être).
- faker_jobs/data/occupations_{en_US,de_DE,es_ES,it_IT}.json.gz: the ESCO
  occupations mapped to those ROME job titles, in English, German, Spanish
  and Italian: labels, description, skills and knowledge come from ESCO;
  sectors, domains and soft skills come from the linked ROME sheets, with
  the labels of rome_labels.py.

Inputs (DATAS/ is not published):
- DATAS/metiers/rome-4-0-métiers-×-secteurs-d-activité.xlsx (ROME v62)
- DATAS/esco/EURESmapping_occs_FR_v1.0.9.csv (ROME 4.0 → ESCO 1.0.9)
- DATAS/esco/esco_occupations_v1.0.9[_de|_es|_it].json (see fetch_esco.py)
- DATAS/bmo/Base-open-data-BMO-2026.xlsx (France Travail, "Besoins en
  Main-d'Œuvre" 2026: recruitment projects by job family, FAP 2021) and
  DATAS/bmo/Dares_FAP2021_Table_passage_ROME.xlsx (DARES, FAP 2021 → ROME):
  the demand weight and the seasonal share of each occupation (see
  bmo_weights() and bmo_seasonal())
- DATAS/salaries/ (see fetch_salaries.py): Eurostat earnings (SES 2022) and
  BLS wages for the salaries, Eurostat Labour Force Survey figures for the
  contract mix (see contract_weights())
- DATAS/naf/naf2008_liste_n5.xls (INSEE, NAF rév. 2 sub-classes): the
  activity codes of the French companies (see NAF_BY_SECTOR)
- faker_jobs/data/jobs_data.json: companies, matched to the ROME sectors
  (re-run this script after build_data.py)

The occupation files are gzipped JSON (~4x smaller installed), written
with a fixed timestamp so that an unchanged build gives the same bytes.
The posting conditions of every locale (contracts, diplomas, benefits,
salaries...) go to faker_jobs/data/conditions.json, plain indented JSON:
they change more often than the occupations, and git stores and diffs a
text file line by line, where each change to a gzipped file would add a
full copy of it to the history. Floats are rounded to FLOAT_DIGITS so that
a build with another Python version gives the same files.

Requires openpyxl and xlrd (`pip install -e ".[dev]"`). Re-run whenever an input changes.
"""
import collections
import gzip
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_esco  # noqa: E402
import fetch_salaries  # noqa: E402
from posting_conditions import BENEFITS_PER_POSTING, CONDITIONS, EXPERIENCE, FIELDS_OF_STUDY, SKILL_LEVELS  # noqa: E402
from rome_labels import DOMAINS, SECTORS, SOFT_SKILLS  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROME_PATH = os.path.join(ROOT, "DATAS", "metiers", "rome-4-0-métiers-×-secteurs-d-activité.xlsx")
OUTPUT_DIR = os.path.join(ROOT, "faker_jobs", "data")
# Companies of the Kaggle data (built by build_data.py), matched to ROME sectors.
JOBS_DATA_PATH = os.path.join(OUTPUT_DIR, "jobs_data.json")
LOCALES = ("de_DE", "en_US", "es_ES", "fr_FR", "it_IT")

BMO_PATH = os.path.join(ROOT, "DATAS", "bmo", "Base-open-data-BMO-2026.xlsx")
FAP_ROME_PATH = os.path.join(ROOT, "DATAS", "bmo", "Dares_FAP2021_Table_passage_ROME.xlsx")
BMO_SOURCE = ("demand weights: BMO 2026 (France Travail) and FAP 2021 → ROME table (DARES), "
              "Licence Ouverte / Etalab 2.0")
NAF_PATH = os.path.join(ROOT, "DATAS", "naf", "naf2008_liste_n5.xls")
NAF_SOURCE = "NAF rév. 2 (INSEE), Licence Ouverte / Etalab 2.0"
ROME_SOURCE = "ROME 4.0 v62 (France Travail, 19/10/2026), Licence Ouverte / Etalab 2.0"
ESCO_SOURCE = ("ESCO 1.0.9 (© European Union), reused under Commission Decision 2011/833/EU; "
               "ROME 4.0 → ESCO crosswalk by France Travail (19.11.2025)")

# Labels of the ROME sectors, domains and soft skills in the ESCO languages.
SECTORS_EN, DOMAINS_EN, SOFT_SKILLS_EN = SECTORS["en"], DOMAINS["en"], SOFT_SKILLS["en"]

# Locales built from ESCO -> ESCO language.
ESCO_LOCALES = {"en_US": "en", "de_DE": "de", "es_ES": "es", "it_IT": "it"}

# How job titles name both genders, by language ('rome': "Conducteur /
# Conductrice de bus"; 'esco': "Busfahrer/Busfahrerin", two full forms), and
# the mark that follows the masculine form in a posting title, as job ads
# must address every gender (France: "(H/F)", Germany: "(m/w/d)", Italy:
# "(m/f)"). Spanish postings keep both forms ("conductor/conductora").
GENDER = {
    "fr": {"titles": "rome", "posting_suffix": "(H/F)"},
    "de": {"titles": "esco", "posting_suffix": "(m/w/d)"},
    "es": {"titles": "esco", "posting_suffix": None},
    "it": {"titles": "esco", "posting_suffix": "(m/f)"},
}


# ROME "Transition écologique" values counted as ecological jobs ("Emploi
# Blanc" and "Emploi Brun", jobs bound to shrink, are not).
ECOLOGICAL_JOBS = {"Emploi Vert", "Emploi stratégique pour la Transition écologique"}

# Knowledge labels that are diplomas (CAP, Bac pro, BTS, Master...), as opposed
# to know-how or certifications (CACES, habilitations), which stay knowledge.
DIPLOMA = re.compile(r"(CAP|BEP|BP|Bac|BTSA?|BUT|DUT|DEUST|Licence|Master|Mastère|Doctorat|Diplôme|MC|CQP"
                     r"|Brevet|Titre professionnel|Ingénieur diplômé)\b")


def normalize(label):
    """Key used to join appellation labels across files (quotes, spaces, case)."""
    return " ".join(unicodedata.normalize("NFC", label).replace("’", "'").split()).lower()


def read_rome():
    """The workbook's sheets as lists of value tuples (header rows and the blank first column dropped)."""
    import openpyxl
    workbook = openpyxl.load_workbook(ROME_PATH, read_only=True)
    try:
        return {sheet.title: [tuple(row[1:]) for row in sheet.iter_rows(min_row=5, values_only=True) if any(row)]
                for sheet in workbook.worksheets}
    finally:
        workbook.close()


def load_rome(sheets):
    """ROME job sheets keyed by code, with their titles, sectors and skills (French)."""
    sectors = {str(row[0]): row[1] for row in sheets["Secteurs"] if row[0]}
    jobs = {}
    for row in sheets["Fiches métiers"]:
        code = row[0]
        riasec, ecological, digital, demographic, regulated, executive = row[9:15]
        jobs[code] = {
            "code": code, "title": row[1], "domain_code": row[2], "domain": row[3],
            "titles": [], "sector_codes": [], "main_sector_code": None,
            "skills": [], "knowledge": [], "soft_skills": [], "qualifications": [],
            # "R – Réaliste / C – Conventionnel" -> ["R", "C"]
            "riasec": [part.strip()[0] for part in riasec.split("/")] if riasec else [],
            "transitions": [name for name, flag in (
                ("ecological", ecological in ECOLOGICAL_JOBS),
                ("digital", digital == "Oui"),
                ("demographic", demographic == "Oui"),
            ) if flag],
            "regulated": regulated == "Oui",
            "executive": executive == "Oui",
        }
    for label, code, _sheet_title, rare in sheets["Appellations"]:
        if rare != "Oui":
            jobs[code]["titles"].append(label)
    for sector_code, _sector, _sub_sector, code, _title, main in sheets["Métier x Secteur"]:
        sector_code = str(sector_code)
        if sector_code not in sectors:
            raise ValueError(f"Unknown ROME sector {sector_code!r} for {code}")
        job = jobs[code]
        if sector_code not in job["sector_codes"]:
            job["sector_codes"].append(sector_code)
        if main == "Oui":
            job["main_sector_code"] = sector_code
    for sheet, field in (("Savoir-faire", "skills"), ("Savoirs", "knowledge"),
                         ("Savoir-être professionnels", "soft_skills")):
        for code, _title, label in sheets[sheet]:
            # Diplomas are listed among the knowledge: they get their own field.
            target = "qualifications" if field == "knowledge" and DIPLOMA.match(label) else field
            if label not in jobs[code][target]:
                jobs[code][target].append(label)
    for job in jobs.values():
        if job["main_sector_code"] is None:
            raise ValueError(f"ROME job {job['code']} has no main sector")
        job["titles"].sort()
        # Main sector first.
        job["sector_codes"].sort(key=lambda code, main=job["main_sector_code"]: (code != main, int(code)))
    return sectors, jobs


def read_bmo():
    """({BMO job code (FAP 2021, 5 characters): recruitment projects in
    France}, {BMO job code: seasonal recruitment projects}), all areas summed.

    Areas with too few answers are masked ('*') in the open data: they count
    as 0, so the seasonal share is a lower bound (32 % of all projects)."""
    import openpyxl
    workbook = openpyxl.load_workbook(BMO_PATH, read_only=True)
    try:
        rows = workbook["BMO_2026_open_data"].iter_rows(min_row=2, values_only=True)
        projects, seasonal = collections.Counter(), collections.Counter()
        for row in rows:
            # 'Code métier BMO', 'met' (recruitment projects), 'smet' (seasonal ones)
            code, value, season = row[1], row[12], row[14]
            if code and value not in (None, "*"):
                projects[code] += float(value)
                if season not in (None, "*"):
                    seasonal[code] += float(season)
        return projects, seasonal
    finally:
        workbook.close()


def read_fap_rome():
    """{FAP 2021 code (finest level, e.g. 'A0X41f'): ROME codes}, from the DARES table."""
    import openpyxl
    workbook = openpyxl.load_workbook(FAP_ROME_PATH, read_only=True)
    try:
        table = collections.defaultdict(set)
        for fap, _label, rome, _qualification, _rome_label in workbook["FAP_ROME_niveau_FAP341"].iter_rows(
                min_row=2, values_only=True):
            if fap and rome:
                table[fap].add(rome)
        return table
    finally:
        workbook.close()


def bmo_weights(jobs, projects, fap_rome):
    """{ROME code: estimated recruitment projects}, the demand weight of each job sheet.

    The projects of a BMO job (a FAP 2021 family like 'A0X41') are shared
    evenly between the ROME codes of its finer families ('A0X41a',
    'A0X41b'...). The DARES table only knows the ROME codes that predate
    ROME 4.0 (532 of them): a newer sheet gets the mean weight of the known
    sheets of its ROME group (same first 3 characters, e.g. 'M18'), or the
    median weight when its group has none. The weights are then scaled so
    that they add up to the BMO total. An estimate, not a statistic."""
    weights = collections.Counter()
    for bmo_code, n in projects.items():
        codes = set().union(*(romes for fap, romes in fap_rome.items() if fap.startswith(bmo_code)))
        if not codes:
            raise ValueError(f"BMO job {bmo_code} has no ROME code in the FAP 2021 table")
        for code in codes:
            weights[code] += n / len(codes)
    unknown = set(weights) - set(jobs)
    if unknown:
        raise ValueError(f"ROME codes of the FAP 2021 table not in ROME 4.0: {sorted(unknown)}")
    by_group = collections.defaultdict(list)
    for code, weight in weights.items():
        by_group[code[:3]].append(weight)
    known = sorted(weights.values())
    median = known[len(known) // 2]
    estimated = {}
    for code in jobs:
        if code in weights:
            estimated[code] = weights[code]
        elif by_group.get(code[:3]):
            estimated[code] = sum(by_group[code[:3]]) / len(by_group[code[:3]])
        else:
            estimated[code] = median
    scale = sum(projects.values()) / sum(estimated.values())
    return {code: weight * scale for code, weight in estimated.items()}


def bmo_seasonal(jobs, projects, seasonal, fap_rome):
    """{ROME code: share of its recruitment projects that are seasonal}.

    The projects of a BMO job are shared between its ROME codes as in
    bmo_weights(); a sheet missing from the DARES table takes the share of
    its ROME group, or the national share."""
    total, season = collections.Counter(), collections.Counter()
    for bmo_code, n in projects.items():
        codes = set().union(*(romes for fap, romes in fap_rome.items() if fap.startswith(bmo_code)))
        for code in codes:
            total[code] += n / len(codes)
            season[code] += seasonal[bmo_code] / len(codes)
    group_total, group_season = collections.Counter(), collections.Counter()
    for code in total:
        group_total[code[:3]] += total[code]
        group_season[code[:3]] += season[code]
    national = sum(seasonal.values()) / sum(projects.values())
    shares = {}
    for code in jobs:
        if total[code]:
            shares[code] = season[code] / total[code]
        elif group_total[code[:3]]:
            shares[code] = group_season[code[:3]] / group_total[code[:3]]
        else:
            shares[code] = national
    return shares


class Pool:
    """Interns repeated strings (skills, sectors...): records store indexes into one list."""

    def __init__(self):
        self.strings = []
        self.index = {}

    def __call__(self, value):
        if value not in self.index:
            self.index[value] = len(self.strings)
            self.strings.append(value)
        return self.index[value]

    def many(self, values):
        return [self(value) for value in values]


def package(meta, sectors, occupations):
    """Final JSON layout: sector names and every repeated label stored once in `strings`."""
    pool = Pool()
    records = []
    for occupation in sorted(occupations, key=lambda o: o["code"]):
        records.append({
            "code": occupation["code"],
            "title": occupation["title"],
            "titles": occupation["titles"],
            "domain": pool(occupation["domain"]),
            "sectors": pool.many(occupation["sectors"]),
            "description": occupation["description"],
            "skills": pool.many(occupation["skills"]),
            "knowledge": pool.many(occupation["knowledge"]),
            "soft_skills": pool.many(occupation["soft_skills"]),
            "qualifications": pool.many(occupation["qualifications"]),
            "executive": occupation["executive"],
            "regulated": occupation["regulated"],
            "riasec": occupation["riasec"],
            "transitions": occupation["transitions"],
            "isco_code": occupation["isco_code"],
            "isco_group": occupation["isco_group"],
            "seasonal": round(occupation["seasonal"], 3),
            # Demand weight: estimated yearly recruitment projects in France (at least 1).
            "weight": max(1, round(occupation["weight"])),
        })
    return {"meta": meta, "sectors": sorted(sectors), "strings": pool.strings, "occupations": records}


# Office jobs (remote work, flexible hours): the ROME domains of banking,
# insurance and real estate (C), communication and media (E), business support (M).
OFFICE_DOMAIN_CODES = {"C", "E", "M"}

ROME_ATTRIBUTES = ("qualifications", "executive", "regulated", "riasec", "transitions")

# Countries of the Eurostat earnings, by locale (en_US: BLS earnings).
EUROSTAT_COUNTRIES = {"fr_FR": "FR", "de_DE": "DE", "es_ES": "ES", "it_IT": "IT"}
# ISCO-08 major groups the earnings survey does not cover (agriculture,
# armed forces), and the group whose earnings they take instead.
ISCO_FALLBACK = {"6": "9", "0": "3"}
# Age bands of the earnings survey (the experience asked picks one).
AGE_BANDS = ("Y_LT30", "Y30-49", "Y_GE50")
# ISCO-08 major group -> the BLS SOC major groups it gathers (a rough match:
# SOC and ISCO do not split occupations the same way).
ISCO_TO_SOC = {
    "1": ["110000"],
    "2": ["150000", "170000", "190000", "230000", "250000", "290000"],
    "3": ["130000", "210000", "270000"],
    "4": ["430000"],
    "5": ["310000", "330000", "350000", "390000", "410000"],
    "6": ["450000"],
    "7": ["470000", "490000"],
    "8": ["510000", "530000"],
    "9": ["350000", "370000"],
    "0": ["330000"],
}
SALARY_SOURCES = {
    "eurostat": "salaries: Eurostat SES 2022 (© European Union), by ISCO-08 major group, NACE section and age",
    "bls": "salaries: U.S. BLS OEWS {year}, by SOC major group (public domain)",
}

# NACE Rev. 2 section of each NAF / NACE division (first two digits).
NACE_SECTIONS = [
    ("A", 1, 3), ("B", 5, 9), ("C", 10, 33), ("D", 35, 35), ("E", 36, 39), ("F", 41, 43), ("G", 45, 47),
    ("H", 49, 53), ("I", 55, 56), ("J", 58, 63), ("K", 64, 66), ("L", 68, 68), ("M", 69, 75), ("N", 77, 82),
    ("O", 84, 84), ("P", 85, 85), ("Q", 86, 88), ("R", 90, 93), ("S", 94, 96), ("T", 97, 98), ("U", 99, 99),
]


def nace_section(code):
    """NACE section letter of a NAF code ('86.10Z' -> 'Q')."""
    division = int(code[:2])
    return next(section for section, low, high in NACE_SECTIONS if low <= division <= high)


# NAF rév. 2 activities of the companies of each ROME sector (French
# postings: a company made up by Faker, with an activity that fits the
# occupation). Prefixes of NAF codes: a division ("86"), a group ("86.2") or
# a sub-class ("86.10Z"); every sub-class they cover is used. Hand-made.
NAF_BY_SECTOR = {
    "79": ["01", "02", "03"],                                   # Agriculture et élevage
    "80": ["36", "37", "38", "39", "81.30Z"],                   # Environnement
    "81": ["33", "81.10Z", "81.2"],                             # Maintenance, entretien et nettoyage
    "82": ["91"],                                               # Culture et patrimoine
    "83": ["10", "11", "12"],                                   # Industrie - Alimentaire
    "84": ["22", "23", "27", "28", "30", "32"],                 # Industries
    "85": ["86", "87.1", "75.00Z"],                             # Santé
    "86": ["88.10A", "96.02", "96.04Z", "97.00Z"],              # Service à la personne
    "87": ["32.1", "32.20Z", "59", "60", "74.20Z", "90"],       # Artisanat d'art, audiovisuel et spectacle
    "88": ["46", "47"],                                         # Commerce et distribution
    "89": ["17", "18"],                                         # Industrie - Papier et imprimerie
    "90": ["13", "14", "15"],                                   # Industrie - Textile et mode
    "91": ["64", "65", "66"],                                   # Finance, banque et assurance
    "92": ["68"],                                               # Immobilier
    "93": ["92", "93"],                                         # Sport, animation et loisir
    "94": ["70.21Z", "73"],                                     # Communication et marketing
    "95": ["29", "45"],                                         # Automobile
    "96": ["61", "62", "63", "95.1"],                           # Informatique et télécommunication
    "97": ["58"],                                               # Édition
    "98": ["71"],                                               # Architecture, études et normes
    "99": ["41", "42", "43"],                                   # Bâtiment et travaux publics (BTP)
    "100": ["24", "25"],                                        # Industrie - Métallurgie
    "101": ["55.20Z", "55.30Z", "79"],                          # Tourisme
    "102": ["55.10Z", "56"],                                    # Hôtellerie et restauration
    "103": ["70.10Z", "70.22Z", "78", "82"],                    # Gestion administrative et ressources humaines
    "104": ["26"],                                              # Industrie - Électronique
    "105": ["72"],                                              # Recherche
    "106": ["19", "20", "21"],                                  # Industrie - Chimie
    "107": ["16", "31"],                                        # Industrie - Bois
    "108": ["05", "06", "35"],                                  # Énergie
    "109": ["87.2", "87.3", "87.90", "88", "94.99Z"],           # Social
    "110": ["69"],                                              # Activités juridiques et comptables
    "111": ["80", "84"],                                        # Service public, défense et sécurité
    "112": ["85"],                                              # Enseignement et formation
    "113": ["49", "50", "51", "52", "53"],                      # Logistique et transport
}


def read_naf():
    """{NAF rév. 2 sub-class code (e.g. '86.10Z'): label}, from the INSEE list."""
    import xlrd
    sheet = xlrd.open_workbook(NAF_PATH).sheet_by_index(0)
    rows = (sheet.row_values(i) for i in range(sheet.nrows))
    return {code: label.strip() for code, label, *_ in rows if re.fullmatch(r"\d\d\.\d\d[A-Z]", str(code))}


def naf_by_sector(sectors, naf):
    """{ROME sector name: [[NAF code, label, NACE section], ...]}, from NAF_BY_SECTOR."""
    missing = set(NAF_BY_SECTOR) ^ set(sectors)
    if missing:
        raise ValueError(f"NAF_BY_SECTOR out of sync with the ROME sectors: {sorted(missing)}")
    result = {}
    for sector_code, prefixes in NAF_BY_SECTOR.items():
        codes = []
        for prefix in prefixes:
            matched = [code for code in naf if code.startswith(prefix)]
            if not matched:
                raise ValueError(f"NAF prefix {prefix!r} (sector {sector_code}) matches no NAF sub-class")
            codes += matched
        result[sectors[sector_code]] = [[code, naf[code], nace_section(code)] for code in sorted(set(codes))]
    return dict(sorted(result.items()))


def section_by_sector(sector_names, naf):
    """{sector name: NACE section of most of its NAF sub-classes}, sector names from {code: name}."""
    result = {}
    for sector_code, prefixes in NAF_BY_SECTOR.items():
        counts = collections.Counter(nace_section(code) for code in naf if code.startswith(tuple(prefixes)))
        result[sector_names[sector_code]] = counts.most_common(1)[0][0]
    return dict(sorted(result.items()))


def rome_isco(jobs, links, esco):
    """{ROME code: (ISCO-08 unit group or None, major group)}: the ISCO code of
    the ESCO occupations its job titles are mapped to (most titles wins). A
    sheet without ESCO occupation takes the most common major group of its
    ROME group (same first 3 characters), else 2 for executive jobs, 5 otherwise."""
    votes = collections.defaultdict(collections.Counter)
    for uri, counts in links.items():
        unit = esco[uri]["isco_code"].split(".")[0]
        for code, n in counts.items():
            votes[code][unit] += n
    result = {code: (counter.most_common(1)[0][0], counter.most_common(1)[0][0][0]) for code, counter in votes.items()}
    by_group = collections.defaultdict(collections.Counter)
    for code, (_unit, major) in result.items():
        by_group[code[:3]][major] += 1
    for code, job in jobs.items():
        if code not in result:
            groups = by_group.get(code[:3])
            major = groups.most_common(1)[0][0] if groups else ("2" if job["executive"] else "5")
            result[code] = (None, major)
    return result


def salary_table(locale, eurostat, bls):
    """Mean gross annual earnings of the locale's country: {"base": {ISCO
    major group: {NACE section or "*": mean}}, "age_ratio": {group: {age
    band: mean of the band / mean of the group}}}.

    Eurostat countries: by group and section ("*": all sections), and by
    group and age. United States: the BLS mean of the SOC major groups of
    each ISCO group (ISCO_TO_SOC), for every section, with the mean age
    ratios of the Eurostat countries. Groups the survey misses take the
    earnings of ISCO_FALLBACK."""
    groups = sorted(SKILL_LEVELS)

    def source(group, ages):
        # Cells under statistical confidentiality are missing: a group with no
        # mean at all takes the earnings of its fallback group.
        return f"OC{group}" if f"OC{group}|TOTAL" in ages else f"OC{ISCO_FALLBACK[group]}"

    def age_ratios(country):
        ages = eurostat["by_isco_age"][country]["values"]
        ratios = {}
        for group in groups:
            occupation = source(group, ages)
            ratios[group] = {band: ages.get(f"{occupation}|{band}", ages[f"{occupation}|TOTAL"])
                             / ages[f"{occupation}|TOTAL"] for band in AGE_BANDS}
        return ratios

    if locale in EUROSTAT_COUNTRIES:
        country = EUROSTAT_COUNTRIES[locale]
        table = eurostat["by_isco_section"][country]["values"]
        ages = eurostat["by_isco_age"][country]["values"]
        base = {}
        for group in groups:
            occupation = source(group, ages)
            sections = {key.split("|")[1]: value for key, value in table.items()
                        if key.startswith(f"{occupation}|") and len(key.split("|")[1]) == 1}
            # "*": every section (the age table covers sections B to S except O).
            base[group] = {"*": ages[f"{occupation}|TOTAL"], **sections}
        return {"base": base, "age_ratio": age_ratios(country)}
    wages = bls["mean_annual_wage"]
    ratios = [age_ratios(country) for country in EUROSTAT_COUNTRIES.values()]
    return {
        "base": {group: {"*": sum(wages[soc] for soc in ISCO_TO_SOC[group]) / len(ISCO_TO_SOC[group])}
                 for group in groups},
        "age_ratio": {group: {band: sum(r[group][band] for r in ratios) / len(ratios) for band in AGE_BANDS}
                      for group in groups},
    }


# Labour Force Survey figure that adapts each contract kind to the ISCO
# group: (part of the group, of all the group's ...).
LFS_SHARES = {"temporary": ("temporary", "employees"), "part_time": ("part_time", "employed"),
              "freelance": ("self_employed", "employed")}
# Cap on the ratio of a group's share to the national one: managers are
# 64 % self-employed in Italy (shopkeepers), but postings seldom hire them so.
MAX_LFS_RATIO = 3
# The permanent contract keeps at least this share of the postings.
MIN_PERMANENT = 0.1


def contract_weights(contracts, lfs):
    """{ISCO major group: {contract: weight}}: the national mix of the
    posting contracts (posting_conditions.py), adapted to each group.

    The weight of a temporary, part-time or freelance contract is multiplied
    by the ratio of the group's share of temporary employees (of employees),
    part-time or self-employed workers (of all workers) to the country's
    share (Eurostat LFS), capped at MAX_LFS_RATIO; a figure the survey does
    not publish (too few people, e.g. part-time soldiers) counts as 0. The
    permanent contract takes what is left of the total, at least
    MIN_PERMANENT of it (the other contracts are scaled down when needed);
    apprenticeships, internships and 'other' kinds keep their weight. Without
    figures (`lfs` None: the United States), every group gets the national
    mix. Seasonal contracts are weighted per occupation when the posting is made."""
    total = sum(spec["weight"] for spec in contracts.values())
    result = {}
    for group in sorted(SKILL_LEVELS):
        weights = {}
        for name, spec in contracts.items():
            ratio = 1
            if lfs is not None and spec["kind"] in LFS_SHARES:
                part, whole = LFS_SHARES[spec["kind"]]
                group_share = lfs[part].get(f"OC{group}", 0) / lfs[whole][f"OC{group}"]
                ratio = min(MAX_LFS_RATIO, group_share / (lfs[part]["TOTAL"] / lfs[whole]["TOTAL"]))
            weights[name] = spec["weight"] * ratio
        permanent = [name for name, spec in contracts.items() if spec["kind"] == "permanent"]
        if len(permanent) != 1:
            raise ValueError(f"one permanent contract expected, got {permanent}")
        others = sum(weight for name, weight in weights.items() if name != permanent[0])
        if others > (1 - MIN_PERMANENT) * total:
            # Too many non-permanent postings: scale them down to leave the minimum.
            weights = {name: weight * (1 - MIN_PERMANENT) * total / others for name, weight in weights.items()}
            others = (1 - MIN_PERMANENT) * total
        weights[permanent[0]] = total - others
        result[group] = {name: round(weight, 2) for name, weight in weights.items()}
    return result


def make_conditions(locale, office_domains, salary, sector_names, naf, lfs, naf_sectors=None):
    """The posting conditions of a locale (see posting_conditions.py), with
    its salaries, contract weights, the NACE section and field of study of
    each activity sector ({ROME sector code: name} in `sector_names`)."""
    local = CONDITIONS[locale]
    contracts = {name: {"kind": spec["kind"], "salary_factor": spec.get("salary_factor", 1),
                        "max_experience": spec.get("max_experience"), "employee": spec.get("employee", True)}
                 for name, spec in local["contracts"].items()}
    conditions = {**local, "contracts": contracts, "contract_weights": contract_weights(local["contracts"], lfs),
                  "experience": EXPERIENCE, "skill_levels": SKILL_LEVELS,
                  "benefits_per_posting": BENEFITS_PER_POSTING, "office_domains": sorted(office_domains),
                  "salary": salary, "section_by_sector": section_by_sector(sector_names, naf),
                  "fields_of_study": {sector_names[code]: field for code, field in FIELDS_OF_STUDY[locale].items()}}
    if naf_sectors is not None:
        conditions["naf_by_sector"] = naf_sectors
    return conditions


def build_fr(sectors, jobs, weights, seasonal, naf, isco, salary, lfs):
    occupations = [{
        "code": job["code"],
        "title": job["title"],
        "titles": job["titles"] or [job["title"]],
        "domain": job["domain"],
        "sectors": [sectors[code] for code in job["sector_codes"]],
        "description": None,
        "skills": job["skills"],
        "knowledge": job["knowledge"],
        "soft_skills": job["soft_skills"],
        **{field: job[field] for field in ROME_ATTRIBUTES},
        "isco_code": isco[job["code"]][0],
        "isco_group": isco[job["code"]][1],
        "seasonal": seasonal[job["code"]],
        "weight": weights[job["code"]],
    } for job in jobs.values()]
    meta = {"source": f"{ROME_SOURCE}; {BMO_SOURCE}; NAF: {NAF_SOURCE}; {SALARY_SOURCES['eurostat']}; "
                      f"{lfs_source(lfs)}",
            "language": "fr", "gender": GENDER["fr"]}
    office_domains = {job["domain"] for job in jobs.values() if job["domain_code"] in OFFICE_DOMAIN_CODES}
    conditions = make_conditions("fr_FR", office_domains, salary, sectors, naf,
                                 lfs_country("fr_FR", lfs), naf_by_sector(sectors, naf))
    return {**package(meta, sectors.values(), occupations), "conditions": conditions}


def link_esco_to_rome(jobs):
    """ESCO occupation URI → {ROME code: number of its job titles mapped to the occupation}."""
    codes_by_title = collections.defaultdict(set)
    for job in jobs.values():
        for title in job["titles"]:
            codes_by_title[normalize(title)].add(job["code"])
    links = collections.defaultdict(collections.Counter)
    for uri, _appellation_id, label, _relation in fetch_esco.read_mapping():
        for code in codes_by_title.get(normalize(label), ()):
            links[uri][code] += 1
    return links


# A sector of the linked ROME sheets is kept only if it covers this share of
# the job titles mapped to the ESCO occupation: a broad occupation is linked
# to many sheets, and the secondary sectors of a sheet that holds one of its
# titles do not describe it (e.g. 'warfare specialist' is not in healthcare).
MIN_SECTOR_SHARE = 0.25


def esco_sectors(jobs, counts):
    """Sector codes of an ESCO occupation from its {ROME code: mapped titles}, best covered first."""
    total = sum(counts.values())
    weight = collections.Counter()
    for code, n in counts.items():
        for sector_code in jobs[code]["sector_codes"]:
            weight[sector_code] += n
    kept = [code for code, n in weight.items() if n >= MIN_SECTOR_SHARE * total]
    return sorted(kept, key=lambda code: (-weight[code], int(code)))


def esco_weights(jobs, links, weights, seasonal):
    """({ESCO URI: demand weight}, {ESCO URI: seasonal share}): each ROME
    sheet's weight shared between the ESCO occupations its job titles are
    mapped to, by number of titles; the seasonal share is the mean of the
    linked sheets' shares, weighted by those parts."""
    titles_by_code = collections.Counter()
    for counts in links.values():
        titles_by_code.update(counts)
    demand, shares = {}, {}
    for uri, counts in links.items():
        parts = {code: weights[code] * n / titles_by_code[code] for code, n in counts.items()}
        demand[uri] = sum(parts.values())
        shares[uri] = sum(seasonal[code] * part for code, part in parts.items()) / demand[uri]
    return demand, shares


def build_esco(locale, jobs, weights, seasonal, naf, salary, salary_source, lfs):
    """Occupations of an ESCO language, with the ROME sectors, domains and soft skills in it."""
    language = ESCO_LOCALES[locale]
    sector_labels, domain_labels, soft_skill_labels = SECTORS[language], DOMAINS[language], SOFT_SKILLS[language]
    with open(fetch_esco.cache_path(language), encoding="utf-8") as f:
        esco = json.load(f)
    occupations = []
    links = link_esco_to_rome(jobs)
    weight_by_uri, seasonal_by_uri = esco_weights(jobs, links, weights, seasonal)
    for uri, counts in links.items():
        if uri not in esco:
            raise ValueError(f"ESCO occupation {uri} missing from the {language} cache: "
                             f"re-run fetch_esco.py {language}")
        record = esco[uri]
        linked = [jobs[code] for code, _ in counts.most_common()]
        sector_codes = esco_sectors(jobs, counts)
        domain_code = collections.Counter({jobs[code]["domain_code"]: 0 for code in counts})
        for code, n in counts.items():
            domain_code[jobs[code]["domain_code"]] += n
        domain_code = domain_code.most_common(1)[0][0]
        soft_skills = list(dict.fromkeys(soft_skill_labels[skill] for job in linked for skill in job["soft_skills"]))
        # Executive status, regulation, RIASEC profile and transitions: those
        # of the ROME sheet holding most of the mapped titles. French diplomas
        # have no equivalent in other countries: no qualifications.
        main_job = linked[0]
        essential = record["essential_skills"]
        occupations.append({
            "code": uri.rsplit("/", 1)[-1],
            "title": record["label"],
            "titles": sorted({record["label"], *record["alt_labels"]}),
            "domain": domain_labels[domain_code],
            "sectors": [sector_labels[code] for code in sector_codes],
            "description": record["description"] or None,
            "skills": [s["label"] for s in essential if s["type"] != "knowledge"],
            "knowledge": [s["label"] for s in essential if s["type"] == "knowledge"],
            "soft_skills": soft_skills,
            **{field: main_job[field] for field in ROME_ATTRIBUTES if field != "qualifications"},
            "qualifications": [],
            "isco_code": record["isco_code"].split(".")[0],
            "isco_group": record["isco_code"][0],
            "seasonal": seasonal_by_uri[uri],
            "weight": weight_by_uri[uri],
        })
    meta = {"source": f"{ESCO_SOURCE}; sectors, domains and soft skills: {ROME_SOURCE}; {BMO_SOURCE}; "
                      f"{salary_source}" + (f"; {lfs_source(lfs)}" if lfs_country(locale, lfs) else ""),
            "language": language, "gender": GENDER.get(language)}
    office_domains = {domain_labels[code] for code in OFFICE_DOMAIN_CODES}
    conditions = make_conditions(locale, office_domains, salary, sector_labels, naf,
                                 lfs_country(locale, lfs))
    return {**package(meta, sector_labels.values(), occupations), "conditions": conditions}


# ROME activity sector of the companies (faker_jobs/data/jobs_data.json), from
# their Kaggle sector label: the first rule whose regex matches the label
# wins, so specific rules come before broad ones. Used by
# job_occupation_posting() to pick a company that fits the occupation.
COMPANY_SECTOR_RULES = [
    (r"Payroll|Staffing|Online Job Search|Professional Services|Business Services|^Services$", "103"),
    (r"Real Estate", "92"),
    (r"Financ|Bank|Insurance|Asset Management", "91"),
    (r"Advertising", "94"),
    (r"Publishing", "97"),
    (r"Restaurant|Food Services|Hospitality|Hotel", "102"),
    (r"Travel|Cruise|Aviation", "101"),
    (r"Gambling", "93"),
    (r"Agricult", "79"),
    (r"Waste", "80"),
    (r"Airline|Airport|Transport|Logistic|Shipping|Postal|Rail|Rental Cars|Ridesharing", "113"),
    (r"Rental & Leasing|Equipment Rental", "88"),
    (r"Automotive|Motorcycle|Recreational Vehicles", "95"),
    (r"Education", "112"),
    (r"Health|Medical|Hospital", "85"),
    (r"Semiconductor|Electronics|Electrical|Lighting|Communication Equipment", "104"),
    (r"Software|Technolog|IT |Internet|Data and Analytics|Telecom|Communication Services", "96"),
    (r"Pharma|Biotech|Chemical|Fertilizer|Agrochemical|Paints|Industrial Gases|Flavor|Beauty|Hygiene"
     r"|Homecare|Lubricant|Lab Equipment", "106"),
    (r"Food|Beverage|Tobacco", "83"),
    (r"Media|Entertainment", "87"),
    (r"Apparel|Fashion", "90"),
    (r"Timber|Paper|Packaging", "89"),
    (r"Steel|Metal|Aluminum", "100"),
    (r"Oil|Gas|Energy|Utilities", "108"),
    (r"Construct|Building|Cement|Infrastructure|Flooring", "99"),
    (r"Engineering|Testing and Certification", "98"),
    (r"Retail|E-commerce|Wholesale|Consumer|Appliances", "88"),
    (r"Mining|Conglomerate|Diversified|Industr|Manufacturing|Aerospace|Machinery|Tools|Motion|HVAC|Elevator"
     r"|Materials", "84"),
]


def company_sector_code(label):
    """ROME sector code of a Kaggle company sector label (see COMPANY_SECTOR_RULES)."""
    for pattern, code in COMPANY_SECTOR_RULES:
        if re.search(pattern, label):
            return code
    raise ValueError(f"No ROME sector for the company sector {label!r}: add a rule to COMPANY_SECTOR_RULES")


def companies_by_sector(sector_names):
    """{sector name: company names} for the packaged companies, sector names from {code: name}."""
    with open(JOBS_DATA_PATH, encoding="utf-8") as f:
        companies = json.load(f)["companies"]
    grouped = collections.defaultdict(list)
    for company in companies:
        if company["sector"]:
            grouped[sector_names[company_sector_code(company["sector"])]].append(company["company"])
    return {sector: sorted(names) for sector, names in sorted(grouped.items())}


def lfs_country(locale, lfs):
    """The Labour Force Survey figures of the locale's country, None for the United States."""
    country = EUROSTAT_COUNTRIES.get(locale)
    return lfs["values"][country] if country else None


def lfs_source(lfs):
    return f"contract mix: {lfs['source']}"


def build_occupations():
    """{locale: packaged data}."""
    sectors, jobs = load_rome(read_rome())
    domain_codes = {job["domain_code"] for job in jobs.values()}
    for language in ESCO_LOCALES.values():
        for name, labels, codes in (("SECTORS", SECTORS, set(sectors)), ("DOMAINS", DOMAINS, domain_codes)):
            missing = codes ^ set(labels[language])
            if missing:
                raise ValueError(f"rome_labels.{name}[{language!r}] out of sync with ROME: {sorted(missing)}")
    projects, seasonal_projects = read_bmo()
    fap_rome = read_fap_rome()
    weights = bmo_weights(jobs, projects, fap_rome)
    seasonal = bmo_seasonal(jobs, projects, seasonal_projects, fap_rome)
    naf = read_naf()
    with open(fetch_esco.CACHE_PATH, encoding="utf-8") as f:
        isco = rome_isco(jobs, link_esco_to_rome(jobs), json.load(f))
    with open(fetch_salaries.EUROSTAT_PATH, encoding="utf-8") as f:
        eurostat = json.load(f)
    with open(fetch_salaries.BLS_PATH, encoding="utf-8") as f:
        bls = json.load(f)
    with open(fetch_salaries.LFS_PATH, encoding="utf-8") as f:
        lfs = json.load(f)
    built = {"fr_FR": build_fr(sectors, jobs, weights, seasonal, naf, isco,
                               salary_table("fr_FR", eurostat, bls), lfs)}
    for locale, language in ESCO_LOCALES.items():
        source = SALARY_SOURCES["bls"].format(year=bls["year"]) if locale == "en_US" else SALARY_SOURCES["eurostat"]
        built[locale] = build_esco(locale, jobs, weights, seasonal, naf, salary_table(locale, eurostat, bls),
                                   source, lfs)
        built[locale]["companies_by_sector"] = companies_by_sector(SECTORS[language])
    return dict(sorted(built.items()))


CONDITIONS_PATH = os.path.join(OUTPUT_DIR, "conditions.json")
FLOAT_DIGITS = 6


def output_path(locale):
    return os.path.join(OUTPUT_DIR, f"occupations_{locale}.json.gz")


def round_floats(value):
    """`value` with every float rounded to FLOAT_DIGITS digits."""
    if isinstance(value, float):
        return round(value, FLOAT_DIGITS)
    if isinstance(value, dict):
        return {key: round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_floats(item) for item in value]
    return value


def split_outputs(built):
    """({locale: occupation data}, {locale: posting conditions}), floats rounded."""
    occupations, conditions = {}, {}
    for locale, data in built.items():
        data = round_floats(data)
        conditions[locale] = data.pop("conditions")
        occupations[locale] = data
    return occupations, conditions


def main():
    occupations, conditions = split_outputs(build_occupations())
    for locale, data in occupations.items():
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
        with open(output_path(locale), "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
            f.write(text.encode("utf-8"))
        print(f"{locale}: {len(data['occupations'])} occupations, {len(data['sectors'])} sectors, "
              f"{len(data['strings'])} strings → {output_path(locale)}")
    with open(CONDITIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(conditions, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"conditions of {', '.join(conditions)} → {CONDITIONS_PATH}")


if __name__ == "__main__":
    main()
