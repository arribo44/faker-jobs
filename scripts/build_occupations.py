#!/usr/bin/env python3
"""
Build the occupation data of each locale from the ROME 4.0 job directory
and its official ESCO crosswalk:

- faker_jobs/data/occupations_fr_FR.json: the ROME 4.0 job sheets (France
  Travail), in French: job titles ("appellations"), activity sectors,
  know-how (savoir-faire), knowledge (savoirs), soft skills (savoir-être).
- faker_jobs/data/occupations_en_US.json: the ESCO occupations mapped to
  those ROME job titles, in English: labels, description, skills and
  knowledge come from ESCO; sectors, domains and soft skills come from the
  linked ROME sheets, with the English labels below.

Inputs (DATAS/ is not published):
- DATAS/metiers/rome-4-0-métiers-×-secteurs-d-activité.xlsx (ROME v62)
- DATAS/esco/EURESmapping_occs_FR_v1.0.9.csv (ROME 4.0 → ESCO 1.0.9)
- DATAS/esco/esco_occupations_v1.0.9.json (see fetch_esco.py)
- faker_jobs/data/jobs_data.json: companies, matched to the ROME sectors
  (re-run this script after build_data.py)

Requires openpyxl (`pip install -e ".[dev]"`). Re-run whenever an input changes.
"""
import collections
import json
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_esco  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROME_PATH = os.path.join(ROOT, "DATAS", "metiers", "rome-4-0-métiers-×-secteurs-d-activité.xlsx")
OUTPUT_DIR = os.path.join(ROOT, "faker_jobs", "data")
# Companies of the Kaggle data (built by build_data.py), matched to ROME sectors.
JOBS_DATA_PATH = os.path.join(OUTPUT_DIR, "jobs_data.json")
LOCALES = ("en_US", "fr_FR")

ROME_SOURCE = "ROME 4.0 v62 (France Travail, 19/10/2026), Licence Ouverte / Etalab 2.0"
ESCO_SOURCE = ("ESCO 1.0.9 (© European Union), reused under Commission Decision 2011/833/EU; "
               "ROME 4.0 → ESCO crosswalk by France Travail (19.11.2025)")

# English labels of the ROME classifications ESCO does not cover. ESCO
# provides the occupations, skills and knowledge in English; these lists
# are short and translated by hand.
SECTORS_EN = {
    "100": "Metalworking industry",
    "101": "Tourism",
    "102": "Hotels and restaurants",
    "103": "Administration and human resources",
    "104": "Electronics industry",
    "105": "Research",
    "106": "Chemical industry",
    "107": "Wood industry",
    "108": "Energy",
    "109": "Social work",
    "110": "Legal and accounting",
    "111": "Public service, defence and security",
    "112": "Education and training",
    "113": "Logistics and transport",
    "79": "Agriculture and livestock",
    "80": "Environment",
    "81": "Maintenance and cleaning",
    "82": "Culture and heritage",
    "83": "Food industry",
    "84": "Manufacturing",
    "85": "Healthcare",
    "86": "Personal care services",
    "87": "Crafts, audiovisual and performing arts",
    "88": "Retail and distribution",
    "89": "Paper and printing industry",
    "90": "Textile and fashion industry",
    "91": "Finance, banking and insurance",
    "92": "Real estate",
    "93": "Sport and leisure",
    "94": "Communication and marketing",
    "95": "Automotive",
    "96": "IT and telecommunications",
    "97": "Publishing",
    "98": "Architecture, engineering studies and standards",
    "99": "Construction and public works",
}

DOMAINS_EN = {
    "A": "Agriculture, fishing, green spaces and animal care",
    "B": "Arts and crafts",
    "C": "Banking, insurance and real estate",
    "D": "Sales, retail and distribution",
    "E": "Communication, media and multimedia",
    "F": "Construction and public works",
    "G": "Hospitality, tourism, leisure and entertainment",
    "H": "Industry",
    "I": "Installation and maintenance",
    "J": "Healthcare",
    "K": "Personal and community services",
    "L": "Performing arts",
    "M": "Business support",
    "N": "Transport and logistics",
}

SOFT_SKILLS_EN = {
    "Avoir l'esprit d'équipe": "Teamwork",
    "Avoir le sens du service": "Customer service orientation",
    "Etre force de proposition": "Proactiveness",
    "Etre ouvert aux changements": "Adaptability to change",
    "Etre à l'écoute, faire preuve d'empathie": "Active listening and empathy",
    "Faire preuve d'autonomie": "Autonomy",
    "Faire preuve de contrôle de soi": "Self-control",
    "Faire preuve de créativité, d'inventivité": "Creativity",
    "Faire preuve de curiosité, d'ouverture d'esprit": "Curiosity and open-mindedness",
    "Faire preuve de leadership": "Leadership",
    "Faire preuve de persévérance": "Perseverance",
    "Faire preuve de rigueur et de précision": "Attention to detail",
    "Faire preuve de réactivité": "Responsiveness",
    "Faire preuve de sens des responsabilités": "Sense of responsibility",
    "Inspirer, donner du sens": "Inspiring others",
    "Organiser son travail selon les priorités et les objectifs": "Prioritisation and time management",
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
        })
    return {"meta": meta, "sectors": sorted(sectors), "strings": pool.strings, "occupations": records}


OFFICE_DOMAIN_CODES = {"C", "E", "M"}

ROME_ATTRIBUTES = ("qualifications", "executive", "regulated", "riasec", "transitions")

# Job conditions of the French postings (job_occupation_posting() in French
# locales), instead of the Kaggle ones (USD, US degrees, worldwide places).
# Hand-made and ILLUSTRATIVE: contract weights and salary ranges give
# plausible postings, they are not statistics.
CONDITIONS_FR = {
    "country": "France",
    "currency": "EUR",
    # Contract type -> relative weight.
    "contracts": {"CDI": 55, "CDD": 20, "Intérim": 12, "Alternance": 6, "Stage": 4, "Freelance": 3},
    # Yearly gross salary, in k€: [min, max] of the lower bound, [min, max] of the gap to the upper bound.
    "salary_k": {
        "executive": {"low": [35, 60], "gap": [5, 15]},
        "other": {"low": [22, 32], "gap": [2, 8]},
    },
    # Years of experience asked: [min, max] of the minimum, [min, max] of the gap to the maximum.
    "experience": {
        "executive": {"low": [1, 8], "gap": [2, 5]},
        "other": {"low": [0, 5], "gap": [2, 5]},
    },
    # Asked when the ROME sheet lists no diploma.
    "qualifications": {
        "executive": ["Bac+5 (Master, école d'ingénieur ou de commerce)", "Bac+3 (Licence, BUT)"],
        "other": ["CAP / BEP", "Bac pro", "Bac", "Bac+2 (BTS, DUT)"],
    },
    # Benefit -> who can get it: "requires" is "office" (an office job or an
    # executive one: see office_domains), "executive", or None for every job;
    # "not_for" lists contract types that never get it (a freelancer is not an
    # employee: no employee benefits).
    "benefits": {
        "Mutuelle d'entreprise": {"requires": None, "not_for": ["Freelance"]},
        "Tickets restaurant": {"requires": None, "not_for": ["Freelance"]},
        "RTT": {"requires": None, "not_for": ["Stage", "Freelance"]},
        "Prime annuelle": {"requires": None, "not_for": ["Stage", "Freelance"]},
        "13e mois": {"requires": None, "not_for": ["Stage", "Freelance"]},
        "Intéressement et participation": {"requires": None, "not_for": ["Stage", "Freelance", "Intérim"]},
        "Plan d'épargne entreprise (PEE)": {"requires": None, "not_for": ["Stage", "Freelance", "Intérim"]},
        "Télétravail partiel": {"requires": "office", "not_for": []},
        "Remboursement à 50 % du titre de transport": {"requires": None, "not_for": ["Freelance"]},
        "Comité social et économique (CSE)": {"requires": None, "not_for": ["Freelance"]},
        "Formation continue": {"requires": None, "not_for": ["Freelance"]},
        "Horaires flexibles": {"requires": "office", "not_for": []},
        "Prime de vacances": {"requires": None, "not_for": ["Stage", "Freelance"]},
        "Chèques cadeaux": {"requires": None, "not_for": ["Freelance"]},
        "Véhicule de fonction": {"requires": "executive", "not_for": ["Stage", "Alternance", "Freelance"]},
        "Forfait mobilités durables": {"requires": None, "not_for": ["Freelance"]},
    },
    "benefits_per_posting": 4,
    # Job boards for every posting, plus those for executive ("cadre") jobs only.
    "job_portals": {
        "all": ["France Travail", "HelloWork", "Indeed", "LinkedIn", "Welcome to the Jungle", "Meteojob",
                "Jobteaser", "Monster", "Le Bon Coin Emploi"],
        "executive": ["APEC", "Cadremploi"],
    },
}


def build_fr(sectors, jobs):
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
    } for job in jobs.values()]
    meta = {"source": ROME_SOURCE, "language": "fr"}
    # Office jobs (remote work, flexible hours): the domains of banking,
    # insurance and real estate (C), communication and media (E), business support (M).
    office_domains = sorted({job["domain"] for job in jobs.values() if job["domain_code"] in OFFICE_DOMAIN_CODES})
    conditions = {**CONDITIONS_FR, "office_domains": office_domains}
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


def build_en(jobs):
    with open(fetch_esco.CACHE_PATH, encoding="utf-8") as f:
        esco = json.load(f)
    occupations = []
    for uri, counts in link_esco_to_rome(jobs).items():
        if uri not in esco:
            raise ValueError(f"ESCO occupation {uri} missing from the cache: re-run fetch_esco.py")
        record = esco[uri]
        linked = [jobs[code] for code, _ in counts.most_common()]
        sector_codes = esco_sectors(jobs, counts)
        domain_code = collections.Counter({jobs[code]["domain_code"]: 0 for code in counts})
        for code, n in counts.items():
            domain_code[jobs[code]["domain_code"]] += n
        domain_code = domain_code.most_common(1)[0][0]
        soft_skills = list(dict.fromkeys(SOFT_SKILLS_EN[skill] for job in linked for skill in job["soft_skills"]))
        # Executive status, regulation, RIASEC profile and transitions: those
        # of the ROME sheet holding most of the mapped titles. French diplomas
        # have no English equivalent: no qualifications.
        main_job = linked[0]
        essential = record["essential_skills"]
        occupations.append({
            "code": uri.rsplit("/", 1)[-1],
            "title": record["label"],
            "titles": sorted({record["label"], *record["alt_labels"]}),
            "domain": DOMAINS_EN[domain_code],
            "sectors": [SECTORS_EN[code] for code in sector_codes],
            "description": record["description"] or None,
            "skills": [s["label"] for s in essential if s["type"] != "knowledge"],
            "knowledge": [s["label"] for s in essential if s["type"] == "knowledge"],
            "soft_skills": soft_skills,
            **{field: main_job[field] for field in ROME_ATTRIBUTES if field != "qualifications"},
            "qualifications": [],
        })
    meta = {"source": ESCO_SOURCE + "; sectors, domains and soft skills: " + ROME_SOURCE, "language": "en"}
    return package(meta, SECTORS_EN.values(), occupations)


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


def build_occupations():
    """{locale: packaged data}."""
    sectors, jobs = load_rome(read_rome())
    missing = set(sectors) ^ set(SECTORS_EN)
    if missing:
        raise ValueError(f"SECTORS_EN out of sync with the ROME sectors: {sorted(missing)}")
    built = {"en_US": build_en(jobs), "fr_FR": build_fr(sectors, jobs)}
    built["en_US"]["companies_by_sector"] = companies_by_sector(SECTORS_EN)
    built["fr_FR"]["companies_by_sector"] = companies_by_sector(sectors)
    return built


def output_path(locale):
    return os.path.join(OUTPUT_DIR, f"occupations_{locale}.json")


def main():
    for locale, data in build_occupations().items():
        with open(output_path(locale), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        print(f"{locale}: {len(data['occupations'])} occupations, {len(data['sectors'])} sectors, "
              f"{len(data['strings'])} strings → {output_path(locale)}")


if __name__ == "__main__":
    main()
