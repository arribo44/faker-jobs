#!/usr/bin/env python3
"""
Build faker_jobs/data/companies.json.gz from the People Data Labs "Free
Company Dataset" (7+ million companies, from LinkedIn company pages; CC BY 4.0):

    DATAS/7millionscompanies/companies_sorted.csv   (~1 GB, not published)

For the six countries of the locales (United States, United Kingdom,
France, Germany, Spain, Italy) and each of the 35 ROME activity sectors
(LinkedIn industry → sector, see INDUSTRY_SECTORS):

- `weights`: the share of jobs in each company size class. LinkedIn lists
  few small companies, so the shares are those of official statistics
  (fetch_business_sizes.py: Eurostat, US Census, UK business population
  estimates) by size group (e.g. 2-9, 10-49, 50-249, 250+ persons employed)
  in the NACE section of the sector, split between the LinkedIn classes of
  each group as LinkedIn splits them: the number of companies of the class
  times its typical size (TYPICAL_SIZES). Sectors without official figures
  (agriculture and public administration in Europe...) keep the LinkedIn
  shares; sectors with fewer than MIN_SECTOR_COMPANIES companies take the
  country's LinkedIn split.
- `companies`: up to PER_CLASS real companies per size class of 11
  employees or more, with a name, website, founding year, headquarters city
  (an index into the country's cities of cities.json.gz when GeoNames knows
  it, else its name), US state and a number of employees in the class. For
  10,001+ employees, the largest ones (by LinkedIn employee estimate), so
  that the best-known groups are there (IBM, Walmart, Apple...); else drawn
  at random (fixed seed: the build is reproducible). Rows without website
  or city are left out: many are noise. Companies of 1-10 employees are left
  out too (many are one-person businesses named after their owner): the
  provider makes them up.
- `counts`: the number of companies of each size class, so that the provider
  can make some up where a class has fewer than PER_CLASS companies (a
  single large group would otherwise get every job of its class).

Run build_cities.py, build_occupations.py (conditions.json) and
fetch_business_sizes.py first, then:

    python scripts/build_companies.py [path/to/companies_sorted.csv]
"""
import csv
import gzip
import heapq
import json
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(ROOT, "DATAS", "7millionscompanies", "companies_sorted.csv")
CITIES_PATH = os.path.join(ROOT, "faker_jobs", "data", "cities.json.gz")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "companies.json.gz")
# Official shares of employment by size (fetch_business_sizes.py), and the NACE
# section of each activity sector (conditions.json, built by build_occupations.py).
SIZES_PATH = os.path.join(ROOT, "DATAS", "business_sizes", "sizes.json")
CONDITIONS_PATH = os.path.join(ROOT, "faker_jobs", "data", "conditions.json")

SOURCE = ("People Data Labs Free Company Dataset (7+ million companies, LinkedIn company pages), CC BY 4.0, "
          "https://docs.peopledatalabs.com/docs/free-company-dataset")
SEED = 20261111
PER_CLASS = 10
MIN_SECTOR_COMPANIES = 200

# Dataset country → country name of cities.json.gz.
COUNTRIES = {"united states": "United States", "united kingdom": "United Kingdom", "france": "France",
             "germany": "Germany",
             "spain": "Spain", "italy": "Italy"}

# The dataset's size classes, their bounds and typical size (geometric mean
# of the bounds; 10001+: a typical large group).
SIZE_CLASSES = ["1 - 10", "11 - 50", "51 - 200", "201 - 500", "501 - 1000", "1001 - 5000", "5001 - 10000", "10001+"]
SIZE_BOUNDS = [[1, 10], [11, 50], [51, 200], [201, 500], [501, 1000], [1001, 5000], [5001, 10000], [10001, 50000]]
TYPICAL_SIZES = [math.sqrt(low * high) for low, high in SIZE_BOUNDS[:-1]] + [30000]

# LinkedIn industry → ROME activity sector code (see rome_labels.SECTORS).
INDUSTRY_SECTORS = {
    "accounting": "110", "airlines/aviation": "113", "alternative dispute resolution": "110",
    "alternative medicine": "86", "animation": "87", "apparel & fashion": "90", "architecture & planning": "98",
    "arts and crafts": "87", "automotive": "95", "aviation & aerospace": "84", "banking": "91",
    "biotechnology": "105", "broadcast media": "87", "building materials": "99",
    "business supplies and equipment": "88", "capital markets": "91", "chemicals": "106",
    "civic & social organization": "109", "civil engineering": "98", "commercial real estate": "92",
    "computer & network security": "96", "computer games": "96", "computer hardware": "104",
    "computer networking": "96", "computer software": "96", "construction": "99", "consumer electronics": "104",
    "consumer goods": "88", "consumer services": "86", "cosmetics": "106", "dairy": "83", "defense & space": "111",
    "design": "94", "e-learning": "112", "education management": "112", "electrical/electronic manufacturing": "104",
    "entertainment": "87", "environmental services": "80", "events services": "94", "executive office": "111",
    "facilities services": "81", "farming": "79", "financial services": "91", "fine art": "82", "fishery": "79",
    "food & beverages": "83", "food production": "83", "fund-raising": "109", "furniture": "107",
    "gambling & casinos": "93", "glass, ceramics & concrete": "84", "government administration": "111",
    "government relations": "111", "graphic design": "94", "health, wellness and fitness": "86",
    "higher education": "112", "hospital & health care": "85", "hospitality": "102", "human resources": "103",
    "import and export": "88", "individual & family services": "109", "industrial automation": "104",
    "information services": "96", "information technology and services": "96", "insurance": "91",
    "international affairs": "111", "international trade and development": "88", "internet": "96",
    "investment banking": "91", "investment management": "91", "judiciary": "110", "law enforcement": "111",
    "law practice": "110", "legal services": "110", "legislative office": "111", "leisure, travel & tourism": "101",
    "libraries": "82", "logistics and supply chain": "113", "luxury goods & jewelry": "90", "machinery": "84",
    "management consulting": "103", "maritime": "113", "market research": "94", "marketing and advertising": "94",
    "mechanical or industrial engineering": "98", "media production": "87", "medical devices": "84",
    "medical practice": "85", "mental health care": "85", "military": "111", "mining & metals": "100",
    "motion pictures and film": "87", "museums and institutions": "82", "music": "87", "nanotechnology": "105",
    "newspapers": "97", "non-profit organization management": "109", "nonprofit organization management": "109",
    "oil & energy": "108", "online media": "94", "outsourcing/offshoring": "103", "package/freight delivery": "113",
    "packaging and containers": "89", "paper & forest products": "89", "performing arts": "87",
    "pharmaceuticals": "106", "philanthropy": "109", "photography": "87", "plastics": "106",
    "political organization": "111", "primary/secondary education": "112", "printing": "89",
    "professional training & coaching": "112", "program development": "109", "public policy": "111",
    "public relations and communications": "94", "public safety": "111", "publishing": "97",
    "railroad manufacture": "84",
    "ranching": "79", "real estate": "92", "recreational facilities and services": "93",
    "religious institutions": "109", "renewables & environment": "108", "research": "105", "restaurants": "102",
    "retail": "88", "security and investigations": "111", "semiconductors": "104", "shipbuilding": "84",
    "sporting goods": "88", "sports": "93", "staffing and recruiting": "103", "supermarkets": "88",
    "telecommunications": "96", "textiles": "90", "think tanks": "105", "tobacco": "83",
    "translation and localization": "97", "transportation/trucking/railroad": "113", "utilities": "108",
    "venture capital & private equity": "91", "veterinary": "85", "warehousing": "113", "wholesale": "88",
    "wine and spirits": "83", "wireless": "96", "writing and editing": "97",
}

# Display names: the dataset is lower-case.
LEGAL_FORMS = {
    "ag": "AG", "bv": "BV", "co": "Co", "cv": "CV", "gmbh": "GmbH", "inc": "Inc", "kg": "KG", "llc": "LLC",
    "llp": "LLP", "lp": "LP", "ltd": "Ltd", "nv": "NV", "plc": "PLC", "sa": "SA", "sarl": "SARL", "sas": "SAS",
    "sasu": "SASU", "sl": "SL", "slu": "SLU", "spa": "SpA", "srl": "Srl", "snc": "SNC", "ug": "UG", "ohg": "OHG",
    "eurl": "EURL", "se": "SE", "ev": "eV", "e.v.": "e.V.", "s.a.": "S.A.", "s.l.": "S.L.", "s.p.a.": "S.p.A.",
    "s.r.l.": "S.r.l.", "inc.": "Inc.", "ltd.": "Ltd.", "co.": "Co.", "corp": "Corp", "corp.": "Corp.",
}
# Legal forms that are also words ("Resort & Spa"): only as the last word.
AMBIGUOUS_FORMS = {"spa", "sa", "se", "co"}
SMALL_WORDS = {"and", "of", "the", "for", "de", "du", "des", "la", "le", "les", "et", "en", "und", "der", "die",
               "das", "für", "y", "del", "e", "di", "della", "delle", "dei", "per", "a", "à", "von", "zu", "el", "los"}
VOWELS = set("aeiouyàâäéèêëîïôöùûüáíóú")
INVISIBLE = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
VALID_NAME = re.compile(r"^[^@/\\|<>{}]{2,60}$")


def display_word(word, first, last=True):
    lower = word.lower()
    if lower in LEGAL_FORMS and (last or lower not in AMBIGUOUS_FORMS):
        return LEGAL_FORMS[lower]
    if lower in SMALL_WORDS and not first:
        return lower
    if lower.isalnum() and len(lower) <= 3 and any(c.isdigit() for c in lower):
        return lower.upper()  # "3m", "4c"
    if "&" in lower and len(lower) <= 5:
        return lower.upper()  # "at&t", "h&m"
    if lower.isalpha() and len(lower) <= 4 and not VOWELS & set(lower):
        return lower.upper()  # an acronym: "kpmg", "bnp"
    # Capitalize, also after a hyphen or a one-letter elision ("l'oréal").
    parts = re.split(r"(-|(?<=\b[ldLD])')", lower)
    return "".join(part[:1].upper() + part[1:] for part in parts)


def display_name(name):
    words = name.split()
    if len(words) == 1 and words[0].isalnum() and len(words[0]) <= 3:
        return words[0].upper()  # "ibm", "ey", "sap", "3m"
    # A legal form ends the name, after a name word ("Enel SpA", not "Resort & Spa").
    return " ".join(display_word(word, i == 0, i == len(words) - 1 and i > 0 and words[i - 1] not in ("&", "and"))
                    for i, word in enumerate(words))


def clean_name(name):
    return " ".join(INVISIBLE.sub("", name).split())


# LinkedIn placeholders, not company names.
PLACEHOLDER_NAMES = re.compile(r"\b(private|confidential|stealth|self[- ]employed|freelancer?|n/a|none|unknown|"
                               r"undisclosed|various|retired|student)\b", re.IGNORECASE)


def valid_name(name):
    return (bool(VALID_NAME.match(name)) and name[0].isalnum() and any(c.isalpha() for c in name)
            and "http" not in name and not PLACEHOLDER_NAMES.search(name))


def place_name(text):
    return " ".join(display_word(word, True) for word in text.split())


def city_index(cities):
    """{country: {lower-case city name (English or local): index}}, the most populous city first."""
    index = {}
    for country in COUNTRIES.values():
        names = {}
        for i, row in enumerate(cities["countries"][country]["cities"]):
            for name in {row[0], row[4] if len(row) > 4 else None} - {None}:
                names.setdefault(name.lower(), i)
        for i, row in enumerate(cities["countries"][country]["cities"]):
            # "Frankfurt" for "Frankfurt am Main", "Halle" for "Halle (Saale)".
            short = re.split(r" am | an der | \(|,", row[0])[0].lower()
            names.setdefault(short, i)
        index[country] = names
    return index


def size_class(label):
    try:
        return SIZE_CLASSES.index(label)
    except ValueError:
        return None


def company_size(rng, size_class_index, estimate):
    """Employees: LinkedIn's estimate when it falls in the declared class,
    else a log-uniform number in the class."""
    low, high = SIZE_BOUNDS[size_class_index]
    if estimate and low <= estimate <= (high if size_class_index < len(SIZE_CLASSES) - 1 else math.inf):
        return estimate
    return round(math.exp(rng.uniform(math.log(low), math.log(high))))


def read(path, cities):
    """(counts {country: {sector: Counter(class)}}, samples {(country, sector, class): rows}).

    Samples are reservoirs of PER_CLASS rows, so a single pass over the file is enough."""
    rng = random.Random(SEED)
    counts = defaultdict(lambda: defaultdict(Counter))
    seen = Counter()
    samples = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            country = COUNTRIES.get(row["country"])
            sector = INDUSTRY_SECTORS.get(row["industry"])
            klass = size_class(row["size range"])
            if country is None or sector is None or klass is None:
                continue
            counts[country][sector][klass] += 1
            name = clean_name(row["name"])
            # Rows without website are often noise ("ecole maternelle" in renewables, in Germany).
            if klass == 0 or not valid_name(name) or not row["domain"] or row["locality"].count(",") < 2:
                continue
            key = (country, sector, klass)
            seen[key] += 1
            if klass == len(SIZE_CLASSES) - 1:
                # The largest groups: a min-heap of (estimate, rank, row).
                entry = (employee_estimate(row), -seen[key], row)
                if len(samples[key]) < PER_CLASS:
                    heapq.heappush(samples[key], entry)
                elif entry[:2] > samples[key][0][:2]:
                    heapq.heapreplace(samples[key], entry)
            elif len(samples[key]) < PER_CLASS:
                samples[key].append(row)
            else:
                j = rng.randrange(seen[key])
                if j < PER_CLASS:
                    samples[key][j] = row
    largest = len(SIZE_CLASSES) - 1
    for key, rows in samples.items():
        if key[2] == largest:
            samples[key] = [row for _, _, row in rows]
    return counts, samples


def employee_estimate(row):
    try:
        return int(row["current employee estimate"] or 0)
    except ValueError:
        return 0


def shares(counter):
    weighted = [counter[k] * TYPICAL_SIZES[k] for k in range(len(SIZE_CLASSES))]
    total = sum(weighted)
    return [round(w / total, 6) for w in weighted]


def size_group(groups, size):
    """Index of the official size group ([low, high], high None for no bound) that holds `size` employees."""
    return next(i for i, (low, high) in enumerate(groups) if size >= low and (high is None or size <= high))


def calibrate(weights, groups, employees, fallback):
    """LinkedIn job shares of the size classes (`weights`) brought to the official
    shares of the size groups (`employees` of each of `groups`): each group gets
    its official share, split between the LinkedIn classes it holds (the class
    of a typical size) as LinkedIn splits them (`fallback`, the country's shares,
    where LinkedIn has no company of the group)."""
    member = [size_group(groups, typical) for typical in TYPICAL_SIZES]
    if set(member) != set(range(len(groups))):
        raise ValueError(f"a size group holds no LinkedIn class: {groups}")
    total = sum(employees)
    calibrated = [0.0] * len(weights)
    for group, value in enumerate(employees):
        classes = [k for k in range(len(weights)) if member[k] == group]
        base = weights if sum(weights[k] for k in classes) > 0 else fallback
        within = sum(base[k] for k in classes)
        for k in classes:
            calibrated[k] = value / total * (base[k] / within if within else 1 / len(classes))
    return [round(w, 6) for w in calibrated]


def sector_sections():
    """{ROME sector code: NACE section} (the main section of each activity sector)."""
    with open(CONDITIONS_PATH, encoding="utf-8") as f:
        conditions = json.load(f)["en_US"]
    return {code: conditions["section_by_sector"][name] for name, code in conditions["sector_codes"].items()}


def company_record(row, klass, country, cities, industries, rng):
    """[name, website, founding year, city (index or name), state, employees, industry index]."""
    parts = [part.strip() for part in row["locality"].split(",")]  # city, region, country
    city = cities[country].get(parts[0].lower(), place_name(parts[0]))
    state = place_name(parts[1]) if country == "United States" else None
    year = row["year founded"]
    estimate = employee_estimate(row)
    if row["industry"] not in industries:
        industries.append(row["industry"])
    return [display_name(clean_name(row["name"])), row["domain"], int(float(year)) if year else None,
            city, state, company_size(rng, klass, estimate), industries.index(row["industry"])]


def build(path):
    with gzip.open(CITIES_PATH, "rt", encoding="utf-8") as f:
        cities = city_index(json.load(f))
    counts, samples = read(path, cities)
    with open(SIZES_PATH, encoding="utf-8") as f:
        official = json.load(f)
    sections = sector_sections()
    rng = random.Random(SEED)
    industries = []
    countries = {}
    for country in sorted(COUNTRIES.values()):
        total = Counter()
        for counter in counts[country].values():
            total.update(counter)
        weights, companies, class_counts = {}, {}, {}
        sizes = official[country]
        country_shares = shares(total)
        for sector in sorted(counts[country], key=int):
            counter = counts[country][sector]
            linkedin = shares(counter if counter.total() >= MIN_SECTOR_COMPANIES else total)
            employees = sizes["sections"].get(sections[sector])
            weights[sector] = (calibrate(linkedin, sizes["groups"], employees, country_shares) if employees
                               else linkedin)
            rows = []
            for klass in range(1, len(SIZE_CLASSES)):
                picked = sorted(samples[(country, sector, klass)], key=lambda row: row["name"])
                rows += [company_record(row, klass, country, cities, industries, rng) for row in picked]
            companies[sector] = rows
            class_counts[sector] = [counter[k] for k in range(len(SIZE_CLASSES))]
        every = [sum(values[i] for values in sizes["sections"].values()) for i in range(len(sizes["groups"]))]
        countries[country] = {"weights_all": calibrate(country_shares, sizes["groups"], every, country_shares),
                              "weights": weights, "counts": class_counts, "companies": companies,
                              "official_sizes": {"source": sizes["source"], "groups": sizes["groups"],
                                                 "sections": sorted(sizes["sections"])}}
    industries_sorted = sorted(industries)
    remap = [industries_sorted.index(name) for name in industries]
    for entry in countries.values():
        for rows in entry["companies"].values():
            for row in rows:
                row[6] = remap[row[6]]
    return {
        "meta": {
            "source": SOURCE,
            "size_classes": SIZE_BOUNDS,
            "row": ["name", "website", "founded", "city (index into the country's cities.json.gz rows, or name)",
                    "state (United States)", "employees", "industry (index into industries)"],
        },
        "industries": [name.capitalize() for name in industries_sorted],
        "countries": countries,
    }


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    data = build(path)
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    with open(OUTPUT_PATH, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as f:
        f.write(text.encode("utf-8"))
    for country, entry in data["countries"].items():
        n = sum(len(rows) for rows in entry["companies"].values())
        print(f"{country}: {n} companies in {len(entry['companies'])} sectors, "
              f"job shares by size class {entry['weights_all']}")
    print(f"→ {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH) // 1024} KB)")


if __name__ == "__main__":
    main()
