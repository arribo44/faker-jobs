#!/usr/bin/env python3
"""
Build faker_jobs/data/companies.json.gz from the People Data Labs "Free
Company Dataset" (7+ million companies, from LinkedIn company pages; CC BY 4.0):

    DATAS/7millionscompanies/companies_sorted.csv   (~1 GB, not published)

For the countries of the locales with posting conditions of their own
(United States, United Kingdom, France, Germany, Spain, Italy, Belgium,
Switzerland, Austria, Luxembourg, Ireland, Canada, Mexico, Chile, Colombia,
Australia, New Zealand, Portugal, the Netherlands, Poland, Brazil) and
each of the 35 ROME activity sectors (LinkedIn
industry → sector, see INDUSTRY_SECTORS):

- `weights`: the share of jobs in each company size class. LinkedIn lists
  few small companies, so the shares are those of official statistics
  (fetch_business_sizes.py: Eurostat, US Census, UK business population
  estimates) by size group (e.g. 2-9, 10-49, 50-249, 250+ persons employed)
  in the NACE section of the sector, split between the LinkedIn classes of
  each group as LinkedIn splits them: the number of companies of the class
  times its typical size (TYPICAL_SIZES). Sectors without official figures
  (agriculture and public administration in Europe...) and countries
  without them (Mexico, Chile, Colombia, Australia) keep the
  LinkedIn shares; sectors with fewer than MIN_SECTOR_COMPANIES
  companies take the country's LinkedIn split.
- `companies`: up to PER_CLASS real companies per size class of 11
  employees or more, with a name, website, founding year, headquarters city
  (an index into the country's cities of cities.json.gz when GeoNames knows
  it, else its name, None when LinkedIn gives a region or a country), US
  state and a number of employees in the class. The headquarters are those
  of Wikidata when it has the company (by LinkedIn ID, P4264 → P159) in the
  same country: LinkedIn often gives an office or a region (Walmart in
  Withee, Asda in "West Yorkshire"). For
  10,001+ employees, the largest ones (by LinkedIn employee estimate), so
  that the best-known groups are there (IBM, Walmart, Apple...); else drawn
  at random (a fixed seed per country: the build is reproducible, and
  adding a country leaves the others unchanged). Rows without website or
  city, or whose city is in another country, are left out: many are noise. Companies of 1-10 employees are left
  out too (many are one-person businesses named after their owner): the
  provider makes them up.
- `counts`: the number of companies of each size class, so that the provider
  can make some up where a class has fewer than PER_CLASS companies (a
  single large group would otherwise get every job of its class).

City names are matched to GeoNames with its alternate names, without
accents ("Dusseldorf", "Brunswick", "New York").

Run build_cities.py, build_occupations.py (conditions.json) and
fetch_business_sizes.py first, then:

    python scripts/build_companies.py [path/to/companies_sorted.csv] [--fetch-headquarters]

--fetch-headquarters queries Wikidata for the companies missing from the
cache, DATAS/wikidata/headquarters.json (Wikidata: CC0).
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
import time
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
import zipfile
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INPUT = os.path.join(ROOT, "DATAS", "7millionscompanies", "companies_sorted.csv")
CITIES_PATH = os.path.join(ROOT, "faker_jobs", "data", "cities.json.gz")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "companies.json.gz")
# Official shares of employment by size (fetch_business_sizes.py), and the NACE
# section of each activity sector (conditions.json, built by build_occupations.py).
SIZES_PATH = os.path.join(ROOT, "DATAS", "business_sizes", "sizes.json")
CONDITIONS_PATH = os.path.join(ROOT, "faker_jobs", "data", "conditions.json")
GEONAMES_PATH = os.path.join(ROOT, "DATAS", "geonames", "cities15000.zip")
HEADQUARTERS_PATH = os.path.join(ROOT, "DATAS", "wikidata", "headquarters.json")
SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"
HEADQUARTERS_BATCH = 200
QUERY_ATTEMPTS = 2
# A Wikidata headquarters is the GeoNames city of its name, or the nearest
# one, within this distance (a business district: La Défense -> Courbevoie).
MATCH_KM = 10

SOURCE = ("People Data Labs Free Company Dataset (7+ million companies, LinkedIn company pages), CC BY 4.0, "
          "https://docs.peopledatalabs.com/docs/free-company-dataset; headquarters: Wikidata (CC0) and GeoNames "
          "(CC BY 4.0)")
SEED = 20261111
PER_CLASS = 10
MIN_SECTOR_COMPANIES = 200

COUNTRY_CODES = {"United States": "US", "United Kingdom": "GB", "France": "FR", "Germany": "DE", "Spain": "ES",
                 "Italy": "IT", "Belgium": "BE", "Switzerland": "CH", "Austria": "AT", "Luxembourg": "LU",
                 "Ireland": "IE", "Canada": "CA", "Mexico": "MX", "Chile": "CL", "Colombia": "CO",
                 "Australia": "AU", "New Zealand": "NZ", "Portugal": "PT", "The Netherlands": "NL", "Poland": "PL",
                 "Brazil": "BR"}
# Dataset country → country name of cities.json.gz.
COUNTRIES = {country.lower(): country for country in COUNTRY_CODES} | {"netherlands": "The Netherlands"}
# Headquarters of large groups that neither LinkedIn nor Wikidata (by
# LinkedIn ID) place in their city: (country, dataset name) -> city of
# cities.json.gz. Hand-made.
HEADQUARTERS_FIXES = {
    ("United States", "walmart"): "Bentonville",
    ("United Kingdom", "asda"): "Leeds",
    ("United Kingdom", "rentokil initial"): "Crawley",
    ("United Kingdom", "waitrose"): "Bracknell",
    ("United Kingdom", "micro focus"): "Newbury",
    ("United Kingdom", "rb"): "Slough",
    ("United Kingdom", "telefónica uk"): "Slough",
    ("United Kingdom", "interserve"): "Reading",
    ("United Kingdom", "mott macdonald"): "Croydon",
    ("United Kingdom", "rwe npower"): "Swindon",
    ("United Kingdom", "leeds city council"): "Leeds",
    ("United Kingdom", "hampshire county council"): "Winchester",
    ("United Kingdom", "university of nottingham"): "Nottingham",
    ("United Kingdom", "university of birmingham"): "Birmingham",
    ("United Kingdom", "university of sheffield"): "Sheffield",
    ("United Kingdom", "university of bath"): "Bath",
    ("United Kingdom", "university of portsmouth"): "Portsmouth",
    ("United Kingdom", "plymouth university"): "Plymouth",
    ("France", "edf"): "Paris",
    ("France", "grdf"): "Paris",
    ("France", "sopra steria"): "Paris",
    ("France", "suez"): "Courbevoie",
    ("France", "geodis"): "Levallois-Perret",
    ("France", "decathlon france"): "Villeneuve-d'Ascq",
    ("Germany", "porsche"): "Stuttgart",
    ("Germany", "man diesel & turbo"): "Augsburg",
    ("Italy", "gucci"): "Florence",
    ("Italy", "politecnico di torino"): "Turin",
}
# Localities that are not a city: UK county abbreviations, provinces.
NOT_CITIES = {"none", "catalunya", "berks", "bucks", "hants", "herts", "oxon", "lancs", "yorks", "glos", "wilts",
              "notts", "beds", "cambs", "northants", "leics", "worcs", "staffs", "warks", "middx"}
NOT_CITY_PREFIXES = ("provincia di ", "province of ", "provincia de ", "county of ", "citta metropolitana di ")
# GeoNames admin1 codes of the United States: the state of a Wikidata headquarters.
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District Of Columbia", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

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


def fold(text):
    """`text` lower-case, without accents, hyphens as spaces: 'Düsseldorf' -> 'dusseldorf'."""
    decomposed = unicodedata.normalize("NFKD", text.lower().replace("-", " "))
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def alternate_names(name):
    """Whether a GeoNames alternate name can stand for a city in LinkedIn
    localities: no codes ('NYC', 'LON') or one- or two-letter names."""
    return len(name) >= 3 and not name.isupper() and any(c.isalpha() for c in name)


def read_geonames():
    """{country code: [(latitude, longitude, [names], admin1 code), ...]}, most populous first."""
    rows = defaultdict(list)
    codes = set(COUNTRY_CODES.values())
    with zipfile.ZipFile(GEONAMES_PATH) as archive, archive.open("cities15000.txt") as raw:
        for line in raw:
            fields = line.decode("utf-8").rstrip("\n").split("\t")
            if fields[8] in codes:
                names = [fields[1], fields[2], *filter(alternate_names, fields[3].split(","))]
                rows[fields[8]].append((int(fields[14]), round(float(fields[4]), 4), round(float(fields[5]), 4),
                                        names, fields[10]))
    return {code: [row[1:] for row in sorted(found, key=lambda row: -row[0])] for code, found in rows.items()}


def nearest(points, point, km):
    """Index of the point of `points` nearest to `point`, if within `km`."""
    best, found = km, None
    for i, other in enumerate(points):
        if abs(other[0] - point[0]) < 0.5 and (distance := distance_km(point, other)) <= best:
            best, found = distance, i
    return found


def city_index(cities, geonames=None):
    """{country: {"names": {folded city name: index}, "points": [(latitude,
    longitude)], "states": [US state or None]}}, indexes into the country's
    cities of cities.json.gz. Names: English and local names, short names
    ("Frankfurt" for "Frankfurt am Main"), then GeoNames alternate names
    (`geonames`, see read_geonames; a district's names point to its city);
    the most populous city first."""
    index = {}
    for country, code in COUNTRY_CODES.items():
        rows = cities["countries"][country]["cities"]
        names = {}
        for i, row in enumerate(rows):
            for name in {row[0], *(row[4].values() if len(row) > 4 else ())}:
                names.setdefault(fold(name), i)
        for i, row in enumerate(rows):
            # "Frankfurt" for "Frankfurt am Main", "Halle" for "Halle (Saale)".
            names.setdefault(fold(re.split(r" am | an der | \(|,", row[0])[0]), i)
        # The last word of a compound name, when no other city ends with it:
        # LinkedIn cuts "Levallois-Perret" to "perret".
        compounds = [(fold(row[0]), i) for i, row in enumerate(rows)]
        points = [(row[1], row[2]) for row in rows]
        by_point = {point: i for i, point in enumerate(points)}
        states = [None] * len(rows)
        for latitude, longitude, alternates, admin1 in (geonames or {}).get(code, []):
            i = by_point.get((latitude, longitude))
            if i is None:
                i = nearest(points, (latitude, longitude), 5)  # a district left out of cities.json.gz
                if i is None:
                    continue
            elif country == "United States":
                states[i] = US_STATES.get(admin1)
            for name in alternates:
                names.setdefault(fold(name), i)
            compounds.append((fold(alternates[0]), i))
        last_words = Counter(name.split()[-1] for name in {name for name, _ in compounds} if " " in name)
        suffixes = {name.split()[-1]: i for name, i in compounds if " " in name and last_words[name.split()[-1]] == 1}
        index[country] = {"names": names, "points": points, "states": states,
                          "suffixes": {word: i for word, i in suffixes.items() if len(word) >= 5 and word not in names}}
    return index


def linkedin_id(row):
    """The company's LinkedIn ID ('linkedin.com/company/ibm' -> 'ibm'), None without."""
    match = re.search(r"linkedin\.com/company/([^/?#]+)", row.get("linkedin url") or "")
    return match.group(1).lower() if match else None


def query_headquarters(ids):
    """{LinkedIn ID: [[headquarters label, latitude, longitude, country code], ...]} from Wikidata."""
    values = " ".join(json.dumps(i) for i in ids)
    query = ("SELECT ?li ?hqLabel ?coord ?cc WHERE { VALUES ?li { " + values + " } "
             "?item wdt:P4264 ?li ; wdt:P159 ?hq . ?hq wdt:P625 ?coord ; wdt:P17 ?c . ?c wdt:P297 ?cc . "
             'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }')
    request = urllib.request.Request(SPARQL_URL, data=urllib.parse.urlencode({"query": query}).encode(),
                                     headers={"User-Agent": USER_AGENT, "Accept": "text/csv"})
    for attempt in range(QUERY_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                rows = list(csv.DictReader(response.read().decode("utf-8").splitlines()))
            break
        except urllib.error.HTTPError as error:
            # The query service often times out (504) or throttles (429): wait and
            # retry, then query each half of the batch on its own.
            if error.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == QUERY_ATTEMPTS - 1:
                if len(ids) < 2:
                    raise
                half = len(ids) // 2
                found = query_headquarters(ids[:half])
                for key, entries in query_headquarters(ids[half:]).items():
                    found[key].extend(entries)
                return found
            time.sleep(10 * (attempt + 1))
    found = defaultdict(list)
    for row in rows:
        point = re.match(r"Point\(([-\d.eE]+) ([-\d.eE]+)\)", row["coord"])
        if point is None:
            continue
        entry = [row["hqLabel"], round(float(point.group(2)), 4), round(float(point.group(1)), 4), row["cc"]]
        if entry not in found[row["li"].lower()]:
            found[row["li"].lower()].append(entry)
    return found


def headquarters(ids, fetch=False):
    """{LinkedIn ID: Wikidata headquarters (see query_headquarters), [] if none},
    from the cache, completed from Wikidata with `fetch`."""
    cache = {}
    if os.path.exists(HEADQUARTERS_PATH):
        with open(HEADQUARTERS_PATH, encoding="utf-8") as f:
            cache = json.load(f)["headquarters"]
    missing = sorted(set(ids) - set(cache))
    if fetch and missing:
        for start in range(0, len(missing), HEADQUARTERS_BATCH):
            batch = missing[start:start + HEADQUARTERS_BATCH]
            found = query_headquarters(batch)
            cache.update({i: found.get(i, []) for i in batch})
            save_headquarters(cache)  # after each batch: a failed run keeps what it found
            print(f"Wikidata: {min(start + HEADQUARTERS_BATCH, len(missing))}/{len(missing)} companies")
    return cache


def save_headquarters(cache):
    os.makedirs(os.path.dirname(HEADQUARTERS_PATH), exist_ok=True)
    with open(HEADQUARTERS_PATH, "w", encoding="utf-8") as f:
        json.dump({"source": "Wikidata (CC0): P4264 LinkedIn company ID -> P159 headquarters location",
                   "headquarters": dict(sorted(cache.items()))}, f, ensure_ascii=False, indent=0)
        f.write("\n")


def not_a_city(name, country, regions):
    """Whether a LinkedIn locality or Wikidata headquarters is a region or a country ("west sussex", "france")."""
    folded = fold(name)
    return (folded in regions[country] or folded in {fold(name) for name in COUNTRIES} or folded in NOT_CITIES
            or folded.startswith(NOT_CITY_PREFIXES))


def headquarters_city(row, country, cities, regions, found):
    """(city: index into the country's cities, name or None, US state or None)
    of a company: HEADQUARTERS_FIXES, else its Wikidata headquarters
    (`found`) in the country, else its LinkedIn locality ("city, region,
    country"); None for a region or a country given as city."""
    entry = cities[country]
    fixed = HEADQUARTERS_FIXES.get((country, clean_name(row["name"])))
    if fixed is not None:
        i = entry["names"][fold(fixed)]
        return i, entry["states"][i]
    for label, latitude, longitude, code in found:
        if code != COUNTRY_CODES[country]:
            continue
        i = entry["names"].get(fold(label))
        if i is None or distance_km(entry["points"][i], (latitude, longitude)) > MATCH_KM:
            i = nearest(entry["points"], (latitude, longitude), MATCH_KM)
        if i is not None and (country != "United States" or entry["states"][i]):
            return i, entry["states"][i]
        if i is None and country != "United States" and not not_a_city(label, country, regions):
            return label, None
    parts = [part.strip() for part in row["locality"].split(",")]  # city, region, country
    state = place_name(parts[1]) if country == "United States" else None
    i = entry["names"].get(fold(parts[0]))
    if i is None:
        i = entry["suffixes"].get(fold(parts[0]))
    if i is not None:
        return i, state
    if not_a_city(parts[0], country, regions):
        return None, state
    return place_name(parts[0]), state


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
    """(counts {country: {sector: Counter(class)}}, samples {(country, sector, class): rows},
    regions {country: folded region names of the localities}).

    Samples are reservoirs of PER_CLASS rows, so a single pass over the file is enough."""
    rngs = {country: country_random(country) for country in COUNTRIES.values()}
    counts = defaultdict(lambda: defaultdict(Counter))
    seen = Counter()
    samples = defaultdict(list)
    regions = defaultdict(set)
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            country = COUNTRIES.get(row["country"])
            sector = INDUSTRY_SECTORS.get(row["industry"])
            klass = size_class(row["size range"])
            if country is None or sector is None or klass is None:
                continue
            counts[country][sector][klass] += 1
            if row["locality"].count(",") >= 2:
                regions[country].add(fold(row["locality"].split(",")[1]))
            name = clean_name(row["name"])
            # Rows without website are often noise ("ecole maternelle" in renewables, in Germany).
            if klass == 0 or not valid_name(name) or not row["domain"] or row["locality"].count(",") < 2:
                continue
            # A locality in another country ("moscow, moscow city, russia" for a Swiss company) is noise.
            if fold(row["locality"].rsplit(",", 1)[1]) != fold(row["country"]):
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
                j = rngs[country].randrange(seen[key])
                if j < PER_CLASS:
                    samples[key][j] = row
    largest = len(SIZE_CLASSES) - 1
    for key, rows in samples.items():
        if key[2] == largest:
            samples[key] = [row for _, _, row in rows]
    return counts, samples, regions


def country_random(country):
    """The random generator of a country's samples: its own, so that adding a
    country leaves the companies of the others unchanged."""
    return random.Random(f"{SEED}:{country}")


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


def company_record(row, klass, country, cities, industries, rng, regions, found):
    """[name, website, founding year, city (index, name or None), state, employees, industry index]."""
    city, state = headquarters_city(row, country, cities, regions, found)
    year = row["year founded"]
    estimate = employee_estimate(row)
    if row["industry"] not in industries:
        industries.append(row["industry"])
    return [display_name(clean_name(row["name"])), row["domain"], int(float(year)) if year else None,
            city, state, company_size(rng, klass, estimate), industries.index(row["industry"])]


def build(path, fetch=False):
    with gzip.open(CITIES_PATH, "rt", encoding="utf-8") as f:
        cities = city_index(json.load(f), read_geonames())
    counts, samples, regions = read(path, cities)
    found = headquarters([i for rows in samples.values() for row in rows if (i := linkedin_id(row))], fetch)
    with open(SIZES_PATH, encoding="utf-8") as f:
        official = json.load(f)
    sections = sector_sections()
    industries = []
    countries = {}
    for country in sorted(COUNTRIES.values()):
        total = Counter()
        for counter in counts[country].values():
            total.update(counter)
        weights, companies, class_counts = {}, {}, {}
        # Countries without official figures keep the LinkedIn shares.
        rng = country_random(country)
        sizes = official.get(country)
        country_shares = shares(total)
        for sector in sorted(counts[country], key=int):
            counter = counts[country][sector]
            linkedin = shares(counter if counter.total() >= MIN_SECTOR_COMPANIES else total)
            employees = sizes["sections"].get(sections[sector]) if sizes else None
            weights[sector] = (calibrate(linkedin, sizes["groups"], employees, country_shares) if employees
                               else linkedin)
            rows = []
            for klass in range(1, len(SIZE_CLASSES)):
                picked = sorted(samples[(country, sector, klass)], key=lambda row: row["name"])
                rows += [company_record(row, klass, country, cities, industries, rng, regions,
                                        found.get(linkedin_id(row)) or []) for row in picked]
            companies[sector] = rows
            class_counts[sector] = [counter[k] for k in range(len(SIZE_CLASSES))]
        countries[country] = {"weights_all": country_shares, "weights": weights, "counts": class_counts,
                              "companies": companies, "official_sizes": None}
        if sizes:
            every = [sum(values[i] for values in sizes["sections"].values()) for i in range(len(sizes["groups"]))]
            countries[country]["weights_all"] = calibrate(country_shares, sizes["groups"], every, country_shares)
            countries[country]["official_sizes"] = {"source": sizes["source"], "groups": sizes["groups"],
                                                    "sections": sorted(sizes["sections"])}
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
            "row": ["name", "website", "founded",
                    "city (index into the country's cities.json.gz rows, name, or None)",
                    "state (United States)", "employees", "industry (index into industries)"],
        },
        "industries": [name.capitalize() for name in industries_sorted],
        "countries": countries,
    }


def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    data = build(args[0] if args else DEFAULT_INPUT, "--fetch-headquarters" in sys.argv[1:])
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
