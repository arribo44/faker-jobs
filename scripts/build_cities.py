#!/usr/bin/env python3
"""
Build faker_jobs/data/cities.json.gz, the job locations: every city of
15,000 inhabitants or more of GeoNames (cities15000, CC BY 4.0), picked in
proportion to its population, in the 244 countries that have one, under
their GeoNames English name ('United States', 'United Kingdom', 'France').

Names: the English name of the city (GeoNames preferred English name, else
its first English name, else its GeoNames name); for the countries of the
locales with conditions of their own (France, Germany, Spain, Italy,
Portugal, the Netherlands, Poland, Belgium, Switzerland, Austria,
Luxembourg, Canada, Mexico, Chile, Colombia, Brazil: LOCAL_LANGUAGES)
also the names in their languages, shown in the locales of that language
('München', 'Anvers', 'Genf', 'Lisboa', 'Den Haag', 'Warszawa'), when they
differ from the English name.

Country names in the languages of the occupations (fr, de, es, it, pt,
nl, pl; English is the GeoNames name), from the Wikidata labels (CC0) of
the item of each ISO 3166-1 alpha-2 code, cached in
DATAS/wikidata/country_names.json (--fetch-country-names).

For Belgium, Switzerland and Canada, the region (GeoNames admin1 code:
'VLG', 'GE', '10' for Quebec...) of each city, for the locales that place
their jobs in the regions of their language (fr_CA in Quebec...).

Districts are left out, as their population is part of their city's:
feature codes PPLX (and abandoned places PPLQ, PPLH, PPLW), names made of a
bigger city's name and a number ("Paris 15 Vaugirard", "Marseille 13") and
places less than 3 km from the centre of a bigger city ("Quinze-Vingts").

Input, in DATAS/geonames/ (https://download.geonames.org/export/dump/):
cities15000.zip, countryInfo.txt, alternatenames/<code>.zip of the
countries of LOCAL_LANGUAGES saved as alt_<code>.zip. Run with --download
to fetch the missing ones.
"""
import gzip
import io
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEONAMES_DIR = os.path.join(ROOT, "DATAS", "geonames")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "cities.json.gz")
BASE_URL = "https://download.geonames.org/export/dump/"

# Country -> languages of its local city names (those of its Faker locales
# with conditions of their own, see posting_conditions.py).
LOCAL_LANGUAGES = {"FR": ["fr"], "DE": ["de"], "ES": ["es"], "IT": ["it"], "BE": ["fr", "nl"],
                   "CH": ["fr", "de", "it"], "AT": ["de"], "LU": ["de"], "CA": ["fr"], "MX": ["es"], "CL": ["es"],
                   "CO": ["es"], "PT": ["pt"], "NL": ["nl"], "PL": ["pl"], "BR": ["pt"]}
COUNTRY_NAMES_PATH = os.path.join(ROOT, "DATAS", "wikidata", "country_names.json")
COUNTRY_NAME_LANGUAGES = ("fr", "de", "es", "it", "pt", "nl", "pl")
SPARQL_URL = "https://query.wikidata.org/sparql"
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"
# Codes whose Wikidata item is not the usual name of the country: the
# Kingdom of the Netherlands (Royaume des Pays-Bas), the People's Republic of
# China (République populaire de Chine): the items of the country instead.
COUNTRY_ITEMS = {"NL": "Q55", "CN": "Q29520"}
# Countries whose locales place their jobs in the regions of their language
# (posting_conditions.py, `regions`): the GeoNames admin1 code of each city.
REGION_COUNTRIES = {"BE", "CH", "CA"}
# Countries of several languages, where the official GeoNames name is often
# in another one ("Antwerpen", "Genève"): the name in the language comes first.
MULTILINGUAL = {"BE", "CH", "LU", "CA"}
SKIPPED_FEATURES = {"PPLX", "PPLQ", "PPLH", "PPLW"}
DISTRICT_KM = 3

def download():
    os.makedirs(GEONAMES_DIR, exist_ok=True)
    files = {"cities15000.zip": "cities15000.zip", "countryInfo.txt": "countryInfo.txt"}
    files.update({f"alt_{code}.zip": f"alternatenames/{code}.zip" for code in LOCAL_LANGUAGES})
    for name, path in files.items():
        if os.path.exists(os.path.join(GEONAMES_DIR, name)):
            continue  # delete a file to fetch it again
        print(f"Downloading {BASE_URL}{path}")
        urllib.request.urlretrieve(BASE_URL + path, os.path.join(GEONAMES_DIR, name))


def country_codes():
    """{GeoNames country name: ISO code}."""
    codes = {}
    with open(os.path.join(GEONAMES_DIR, "countryInfo.txt"), encoding="utf-8") as f:
        for line in f:
            if not line.startswith("#"):
                fields = line.rstrip("\n").split("\t")
                codes[fields[4]] = fields[0]
    return codes


def read_cities():
    """{geonameid: (name, country code, latitude, longitude, population, admin1 code)}."""
    cities = {}
    with zipfile.ZipFile(os.path.join(GEONAMES_DIR, "cities15000.zip")) as archive:
        with archive.open("cities15000.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                fields = line.rstrip("\n").split("\t")
                if fields[7] in SKIPPED_FEATURES:
                    continue
                cities[fields[0]] = (fields[1], fields[8], round(float(fields[4]), 4),
                                     round(float(fields[5]), 4), int(fields[14]), fields[10])
    return cities


def alternate_names(code, cities):
    """{geonameid: {language: name}} for English and the local languages.

    English: the preferred English name, else the GeoNames name if it is
    one of the English names, else the first English name ('Lisboa', 'Den Haag', 'Warszawa'). Local language:
    the GeoNames name (usually the official one: "Torrent", "Greifswald"),
    unless it is an English name that is not a name in the language
    ("Rome", "Munich"): then the preferred name in the language, else the
    first one ("Roma", "München"). In MULTILINGUAL countries, the preferred
    name in the language, else the GeoNames name if it is one of its names,
    else its first name ("Anvers", "Genf"), else the GeoNames name.
    Colloquial and historic names are left out."""
    languages = LOCAL_LANGUAGES[code]
    preferred, every = {}, {}
    with zipfile.ZipFile(os.path.join(GEONAMES_DIR, f"alt_{code}.zip")) as archive:
        with archive.open(f"{code}.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                fields = line.rstrip("\n").split("\t")
                geonameid, language, name = fields[1], fields[2], fields[3]
                if geonameid not in cities or (language != "en" and language not in languages) or "1" in fields[6:8]:
                    continue
                every.setdefault(geonameid, {}).setdefault(language, []).append(name)
                if fields[4] == "1":
                    preferred.setdefault(geonameid, {}).setdefault(language, name)
    chosen = {}
    for geonameid, names in every.items():
        own = cities[geonameid][0]
        best = preferred.get(geonameid, {})
        english = names.get("en", [])
        chosen[geonameid] = {"en": best.get("en") or (own if own in english or not english else english[0])}
        for local in languages:
            in_language = names.get(local, [])
            if code in MULTILINGUAL:
                chosen[geonameid][local] = best.get(local) or (own if own in in_language or not in_language
                                                               else in_language[0])
            else:
                chosen[geonameid][local] = (own if own in in_language or own not in english or not in_language
                                            else best.get(local, in_language[0]))
    return chosen


def distance_km(a, b):
    """Great-circle distance between two (latitude, longitude) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def drop_districts(rows):
    """Rows (sorted by decreasing population) without the districts of a
    bigger city: "<city> <number>..." names, or less than DISTRICT_KM from it."""
    kept = []
    names = set()
    for row in rows:
        prefix = re.match(r"(.+?) \d", row[0])
        if prefix and prefix.group(1) in names:
            continue
        point = (row[1], row[2])
        if any(abs(big[1] - row[1]) < 0.05 and distance_km(point, (big[1], big[2])) < DISTRICT_KM
               for big in kept):
            continue
        kept.append(row)
        names.add(row[0])
    return kept


def sparql(query):
    request = urllib.request.Request(SPARQL_URL, data=urllib.parse.urlencode({"query": query}).encode(),
                                     headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.load(response)["results"]["bindings"]


def fetch_country_names():
    """{ISO alpha-2 code: {language: name}} from Wikidata: the labels of the
    current item (no dissolution date) with the code (P297), the most linked
    one where there are several, COUNTRY_ITEMS where set; capitalised
    ('île Bouvet' -> 'Île Bouvet')."""
    languages = ", ".join(f'"{language}"' for language in COUNTRY_NAME_LANGUAGES)
    labels = (f"?item rdfs:label ?label . FILTER(LANG(?label) IN ({languages})) "
              "BIND(LANG(?label) AS ?lang) ?item wikibase:sitelinks ?links . ")
    rows = sparql("SELECT ?code ?item ?links ?label ?lang WHERE { ?item wdt:P297 ?code . "
                  "FILTER NOT EXISTS { ?item wdt:P576 ?end } " + labels + "}")
    rows = [row for row in rows if row["code"]["value"] not in COUNTRY_ITEMS]
    values = " ".join(f'("{code}" wd:{item})' for code, item in COUNTRY_ITEMS.items())
    rows += sparql(f"SELECT ?code ?item ?links ?label ?lang WHERE {{ VALUES (?code ?item) {{ {values} }} {labels}}}")
    best = {}
    for row in rows:
        code, item, links = row["code"]["value"], row["item"]["value"], int(row["links"]["value"])
        if code not in best or links > best[code][0]:
            best[code] = (links, item)
    names = {}
    for row in rows:
        code = row["code"]["value"]
        if best[code][1] == row["item"]["value"]:
            label = row["label"]["value"]
            names.setdefault(code, {})[row["lang"]["value"]] = label[:1].upper() + label[1:]
    return dict(sorted(names.items()))


def country_names(fetch=False):
    """The cached Wikidata country names (see fetch_country_names), fetched with `fetch`."""
    if fetch or not os.path.exists(COUNTRY_NAMES_PATH):
        names = fetch_country_names()
        os.makedirs(os.path.dirname(COUNTRY_NAMES_PATH), exist_ok=True)
        with open(COUNTRY_NAMES_PATH, "w", encoding="utf-8") as f:
            json.dump({"source": "Wikidata (CC0): labels of the item with the ISO 3166-1 alpha-2 code (P297)",
                       "names": names}, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write("\n")
    with open(COUNTRY_NAMES_PATH, encoding="utf-8") as f:
        return json.load(f)["names"]


def build(fetch_names=False):
    codes = country_codes()
    translated = country_names(fetch_names)
    cities = read_cities()
    names = {}
    for code in LOCAL_LANGUAGES:
        names.update(alternate_names(code, cities))

    by_code, admin1 = {}, {}
    for geonameid, (name, code, latitude, longitude, population, region) in cities.items():
        found = names.get(geonameid, {})
        row = [found.get("en", name), latitude, longitude, population]
        local = {language: found.get(language, name) for language in LOCAL_LANGUAGES.get(code, [])}
        local = {language: value for language, value in local.items() if value != row[0]}
        if local:
            row.append(local)
        by_code.setdefault(code, []).append(row)
        admin1[id(row)] = region

    countries = {}
    for country, code in sorted(codes.items()):
        if code in by_code:
            countries[country] = {"code": code, "cities": drop_districts(
                sorted(by_code[code], key=lambda row: (-row[3], row[0])))}
            if code in REGION_COUNTRIES:
                countries[country]["regions"] = [admin1[id(row)] for row in countries[country]["cities"]]
            names = {language: name for language, name in translated.get(code, {}).items() if name != country}
            if names:
                countries[country]["names"] = names
    data = {
        "meta": {
            "source": "GeoNames cities15000 (www.geonames.org, CC BY 4.0); country names: Wikidata (CC0)",
            "row": ["city (English)", "latitude", "longitude", "population",
                    "optional: {language: local name} where it differs from the English name (LOCAL_LANGUAGES)"],
            "local_languages": LOCAL_LANGUAGES,
        },
        "countries": countries,
    }
    return data


def main():
    if "--download" in sys.argv:
        download()
    data = build("--fetch-country-names" in sys.argv)
    # Fixed timestamp: an unchanged build gives the same bytes.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(OUTPUT_PATH, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as f:
        f.write(text.encode("utf-8"))
    total = sum(len(country["cities"]) for country in data["countries"].values())
    print(f"Wrote {OUTPUT_PATH}: {total} cities in {len(data['countries'])} countries "
          f"({os.path.getsize(OUTPUT_PATH) // 1024} KB)")


if __name__ == "__main__":
    main()
