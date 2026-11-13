#!/usr/bin/env python3
"""
Fetch from the ESCO web-service API the data of every ESCO occupation
mapped to a ROME 4.0 job title, in one language, and cache it in
DATAS/esco/esco_occupations_v1.0.9.json (English) or
DATAS/esco/esco_occupations_v1.0.9_<language>.json (read by build_occupations.py).

Usage: fetch_esco.py [language]   (en, de, es, it, pt, nl, pl, ar, sv, cs, ro or el; default en)

Input: DATAS/esco/EURESmapping_occs_FR_v1.0.9.csv, the official ROME 4.0 →
ESCO 1.0.9 crosswalk published by France Travail on the ESCO portal:
https://esco.ec.europa.eu/en/use-esco/eures-countries-mapping-tables

The cache is saved as it goes: re-running the script only fetches the
occupations still missing. One request per occupation (the API's batch
endpoint returns no details), a few in parallel.
"""
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESCO_DIR = os.path.join(ROOT, "DATAS", "esco")
MAPPING_PATH = os.path.join(ESCO_DIR, "EURESmapping_occs_FR_v1.0.9.csv")
CACHE_PATH = os.path.join(ESCO_DIR, "esco_occupations_v1.0.9.json")
LANGUAGES = ("en", "de", "es", "it", "pt", "nl", "pl", "ar", "sv", "cs", "ro", "el")


def cache_path(language="en"):
    """The cache file of a language (the English one keeps its original name)."""
    if language == "en":
        return CACHE_PATH
    return os.path.join(ESCO_DIR, f"esco_occupations_v1.0.9_{language}.json")

ESCO_VERSION = "v1.0.9"
# A few v1.0.9 occupations always answer HTTP 500 (server-side bug): they are
# fetched from the next version instead, and the record says which one.
FALLBACK_VERSION = "v1.1.0"
API_URL = "https://ec.europa.eu/esco/api/resource/occupation"
WORKERS = 4
RETRIES = 6
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"


def read_mapping():
    """Rows of the crosswalk: (ESCO URI, ROME appellation id, appellation label, SKOS relation)."""
    # The file is Windows-1252 encoded, ';' separated, with a 17-line header block.
    import csv
    with open(MAPPING_PATH, encoding="cp1252", newline="") as f:
        rows = list(csv.reader(f, delimiter=";"))
    header = next(i for i, row in enumerate(rows) if row and row[0] == "Classification 1 URI")
    return [(row[0], row[5], row[6], row[8]) for row in rows[header + 1:] if len(row) > 8 and row[0]]


def fetch(uri, language="en"):
    try:
        return fetch_version(uri, ESCO_VERSION, language)
    except urllib.error.HTTPError as error:
        if error.code != 500:
            raise
        return fetch_version(uri, FALLBACK_VERSION, language)


def fetch_version(uri, version, language="en"):
    # `language` sets the labels and the titles of the linked skills.
    query = urllib.parse.urlencode({"uri": uri, "language": language, "selectedVersion": version})
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    # The API answers 500 now and then under load: retry with a growing pause.
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = json.load(response)
            break
        except OSError:
            if attempt == RETRIES - 1:
                raise
            time.sleep(2 ** attempt)
    links = raw.get("_links", {})

    def skills(kind):
        return [{"label": link["title"], "type": link.get("skillType", "").rsplit("/", 1)[-1]}
                for link in links.get(kind, [])]

    return {
        "uri": uri,
        "version": version,
        "label": raw["preferredLabel"].get(language) or raw["title"],
        "alt_labels": raw.get("alternativeLabel", {}).get(language, []),
        "description": (raw.get("description", {}).get(language) or {}).get("literal", "").strip(),
        "isco_code": raw.get("code"),
        "isco_group": next((link["title"] for link in links.get("broaderIscoGroup", [])), None),
        "essential_skills": skills("hasEssentialSkill"),
        "optional_skills": skills("hasOptionalSkill"),
    }


def save(cache, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)


def main():
    language = sys.argv[1] if len(sys.argv) > 1 else "en"
    if language not in LANGUAGES:
        sys.exit(f"language must be one of {LANGUAGES}, got {language!r}")
    path = cache_path(language)
    uris = sorted({uri for uri, *_ in read_mapping()})
    cache = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cache = json.load(f)
    todo = [uri for uri in uris if uri not in cache]
    print(f"{len(uris)} ESCO occupations, {len(todo)} to fetch ({language})", file=sys.stderr)
    failed = []
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        futures = {pool.submit(fetch, uri, language): uri for uri in todo}
        for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                record = future.result()
            except OSError as error:
                failed.append(futures[future])
                print(f"failed: {futures[future]} ({error})", file=sys.stderr)
                continue
            cache[record["uri"]] = record
            if done % 100 == 0:
                save(cache, path)
                print(f"{done}/{len(todo)}", file=sys.stderr)
    save(cache, path)
    print(f"cached {len(cache)} occupations in {path}", file=sys.stderr)
    if failed:
        sys.exit(f"{len(failed)} occupations failed: re-run the script to fetch them")


if __name__ == "__main__":
    main()
