#!/usr/bin/env python3
"""
Build faker_jobs/data/cities.json.gz, the job locations: every city of
15,000 inhabitants or more of GeoNames (cities15000, CC BY 4.0), picked in
proportion to its population, in the 244 countries that have one, under
their GeoNames English name ('United States', 'United Kingdom', 'France').

Names: the English name of the city (GeoNames preferred English name, else
its first English name, else its GeoNames name); for France, Germany, Spain
and Italy also the name in the country's language (preferred name, else the
first one), shown in the locales of that language.

Districts are left out, as their population is part of their city's:
feature codes PPLX (and abandoned places PPLQ, PPLH, PPLW), names made of a
bigger city's name and a number ("Paris 15 Vaugirard", "Marseille 13") and
places less than 3 km from the centre of a bigger city ("Quinze-Vingts").

Input, in DATAS/geonames/ (https://download.geonames.org/export/dump/):
cities15000.zip, countryInfo.txt, alternatenames/{FR,DE,ES,IT}.zip saved as
alt_{FR,DE,ES,IT}.zip. Run with --download to fetch them.
"""
import gzip
import io
import json
import math
import os
import re
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEONAMES_DIR = os.path.join(ROOT, "DATAS", "geonames")
OUTPUT_PATH = os.path.join(ROOT, "faker_jobs", "data", "cities.json.gz")
BASE_URL = "https://download.geonames.org/export/dump/"

# Country -> language of its local city names.
LOCAL_LANGUAGES = {"FR": "fr", "DE": "de", "ES": "es", "IT": "it"}
SKIPPED_FEATURES = {"PPLX", "PPLQ", "PPLH", "PPLW"}
DISTRICT_KM = 3

def download():
    os.makedirs(GEONAMES_DIR, exist_ok=True)
    files = {"cities15000.zip": "cities15000.zip", "countryInfo.txt": "countryInfo.txt"}
    files.update({f"alt_{code}.zip": f"alternatenames/{code}.zip" for code in LOCAL_LANGUAGES})
    for name, path in files.items():
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
    """{geonameid: (name, country code, latitude, longitude, population)}."""
    cities = {}
    with zipfile.ZipFile(os.path.join(GEONAMES_DIR, "cities15000.zip")) as archive:
        with archive.open("cities15000.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                fields = line.rstrip("\n").split("\t")
                if fields[7] in SKIPPED_FEATURES:
                    continue
                cities[fields[0]] = (fields[1], fields[8], round(float(fields[4]), 4),
                                     round(float(fields[5]), 4), int(fields[14]))
    return cities


def alternate_names(code, cities):
    """{geonameid: {language: name}} for English and the local language.

    English: the preferred English name, else the GeoNames name if it is
    one of the English names, else the first English name. Local language:
    the GeoNames name (usually the official one: "Torrent", "Greifswald"),
    unless it is an English name that is not a name in the language
    ("Rome", "Munich"): then the preferred name in the language, else the
    first one ("Roma", "München"). Colloquial and historic names are left out."""
    local = LOCAL_LANGUAGES[code]
    preferred, every = {}, {}
    with zipfile.ZipFile(os.path.join(GEONAMES_DIR, f"alt_{code}.zip")) as archive:
        with archive.open(f"{code}.txt") as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8"):
                fields = line.rstrip("\n").split("\t")
                geonameid, language, name = fields[1], fields[2], fields[3]
                if geonameid not in cities or language not in ("en", local) or "1" in fields[6:8]:
                    continue
                every.setdefault(geonameid, {}).setdefault(language, []).append(name)
                if fields[4] == "1":
                    preferred.setdefault(geonameid, {}).setdefault(language, name)
    chosen = {}
    for geonameid, names in every.items():
        own = cities[geonameid][0]
        best = preferred.get(geonameid, {})
        english, in_language = names.get("en", []), names.get(local, [])
        chosen[geonameid] = {
            "en": best.get("en") or (own if own in english or not english else english[0]),
            local: own if own in in_language or own not in english or not in_language
            else best.get(local, in_language[0]),
        }
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


def build():
    codes = country_codes()
    cities = read_cities()
    names = {}
    for code in LOCAL_LANGUAGES:
        names.update(alternate_names(code, cities))

    by_code = {}
    for geonameid, (name, code, latitude, longitude, population) in cities.items():
        found = names.get(geonameid, {})
        row = [found.get("en", name), latitude, longitude, population]
        if code in LOCAL_LANGUAGES:
            row.append(found.get(LOCAL_LANGUAGES[code], name))
        by_code.setdefault(code, []).append(row)

    countries = {}
    for country, code in sorted(codes.items()):
        if code in by_code:
            countries[country] = {"code": code, "cities": drop_districts(
                sorted(by_code[code], key=lambda row: (-row[3], row[0])))}
    data = {
        "meta": {
            "source": "GeoNames cities15000 (www.geonames.org, CC BY 4.0)",
            "row": ["city (English)", "latitude", "longitude", "population", "local name (FR, DE, ES, IT)"],
            "local_languages": LOCAL_LANGUAGES,
        },
        "countries": countries,
    }
    return data


def main():
    if "--download" in sys.argv:
        download()
    data = build()
    # Fixed timestamp: an unchanged build gives the same bytes.
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(OUTPUT_PATH, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as f:
        f.write(text.encode("utf-8"))
    total = sum(len(country["cities"]) for country in data["countries"].values())
    print(f"Wrote {OUTPUT_PATH}: {total} cities in {len(data['countries'])} countries "
          f"({os.path.getsize(OUTPUT_PATH) // 1024} KB)")


if __name__ == "__main__":
    main()
