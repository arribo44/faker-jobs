#!/usr/bin/env python3
"""
Fetch the activities of the companies that employ each occupation, used by
build_occupations.py to pick the activity (NAF / NACE code) of the hiring
company, and cache them in DATAS/:

- DATAS/insee_rp/isco_naf.json: {ISCO-08 unit group: {NAF rév. 2 sub-class:
  employees}}, the employees of each occupation by activity of their
  employer in France, from the 2022 census, INSEE, Licence Ouverte / Etalab
  2.0: the detailed file "Individus localisés à la région"
  (RP2022_indreg.parquet: profession PROF, PCS 2020 in 311 positions, and
  NAF08, activity in 732 sub-classes, of the employees: STAT 10, weighted
  by IPONDI), and the PCS 2020 → ISCO-08 matrix
  (Matrice_PCS_ISCO_pour_programmes.csv: share of each profession in each
  ISCO unit group, Enquête Emploi 2021-2023; rare crossings "ns" left out).
  The employees of a profession are shared between its ISCO unit groups by
  those shares.
- DATAS/nace/labels.json: {language: {NACE Rev. 2 class (e.g. '62.01'):
  label}} in German, Spanish and Italian, from EU Vocabularies (Publications
  Office of the European Union, reuse authorised: Commission Decision
  2011/833/EU), the activities of the companies in de_DE, es_ES and it_IT.

Run with --download to fetch the census file (~620 MB) and the matrix into
DATAS/insee_rp/ first.

Needs pyarrow (`pip install -e ".[build]"`).
"""
import collections
import csv
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CENSUS_DIR = os.path.join(ROOT, "DATAS", "insee_rp")
CENSUS_PATH = os.path.join(CENSUS_DIR, "RP2022_indreg.parquet")
MATRIX_PATH = os.path.join(CENSUS_DIR, "Matrice_PCS_ISCO.csv")
OUTPUT_PATH = os.path.join(CENSUS_DIR, "isco_naf.json")
LABELS_PATH = os.path.join(ROOT, "DATAS", "nace", "labels.json")
USER_AGENT = "faker-jobs data build (https://github.com/arribo44/faker-jobs)"

DOWNLOADS = {
    CENSUS_PATH: "https://www.insee.fr/fr/statistiques/fichier/8590183/RP2022_indreg.parquet",
    MATRIX_PATH: "https://www.insee.fr/fr/statistiques/fichier/8292892/Matrice_PCS_ISCO_pour_programmes.csv",
}
SOURCE = ("employees by profession and activity of the employer: 2022 census (INSEE, RP2022 indreg: PROF × NAF08, "
          "employees), professions → ISCO-08 by the INSEE PCS 2020 × ISCO matrix, Licence Ouverte / Etalab 2.0")
LABELS_SOURCE = "NACE Rev. 2 labels: EU Vocabularies (Publications Office of the EU, Decision 2011/833/EU)"
SPARQL_URL = "https://publications.europa.eu/webapi/rdf/sparql"
LANGUAGES = ("de", "es", "it", "pt", "nl", "pl", "sv", "cs", "ro", "el")
SALARIED = "10"


def download():
    os.makedirs(CENSUS_DIR, exist_ok=True)
    for path, url in DOWNLOADS.items():
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=600) as response, open(path, "wb") as f:
            while chunk := response.read(1 << 20):
                f.write(chunk)
        print(f"{url} → {path}")


def naf_code(code):
    """'0311Z' -> '03.11Z' (the dotted form of the INSEE NAF list)."""
    return f"{code[:2]}.{code[2:]}"


def read_census():
    """{(profession, NAF sub-class): employees}."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    table = pq.read_table(CENSUS_PATH, columns=["PROF", "NAF08", "STAT", "IPONDI"])
    table = table.filter(pc.equal(table["STAT"], SALARIED))
    grouped = table.group_by(["PROF", "NAF08"]).aggregate([("IPONDI", "sum")])
    return {(row["PROF"], row["NAF08"]): row["IPONDI_sum"] for row in grouped.to_pylist()
            if row["PROF"] and row["NAF08"] and not row["NAF08"].startswith("Z")}


def read_matrix():
    """{profession (PCS 2020): {ISCO-08 unit group: share}}."""
    matrix = collections.defaultdict(dict)
    with open(MATRIX_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if row["PCT"] != "ns":
                matrix[row["PCS4"]][row["ISCO4"]] = float(row["PCT"]) / 100
    return matrix


def isco_naf(census, matrix):
    """{ISCO unit group: {NAF sub-class: employees}}, each profession's employees
    shared between its ISCO unit groups."""
    result = collections.defaultdict(collections.Counter)
    missing = collections.Counter()
    for (profession, naf), employees in census.items():
        shares = matrix.get(profession)
        if not shares:
            missing[profession] += employees
            continue
        for isco, share in shares.items():
            result[isco][naf_code(naf)] += employees * share
    if sum(missing.values()) > 0.01 * sum(census.values()):
        raise ValueError(f"professions without ISCO unit group: {missing.most_common(5)}")
    return {isco: {naf: round(n, 1) for naf, n in sorted(counter.items())}
            for isco, counter in sorted(result.items())}


def fetch_labels(language):
    """{NACE Rev. 2 class: label} in `language`."""
    query = ("PREFIX skos: <http://www.w3.org/2004/02/skos/core#> SELECT ?n ?l WHERE { "
             "?c skos:inScheme <http://data.europa.eu/ux2/nace2/nace2> ; skos:notation ?n ; skos:prefLabel ?l . "
             f'FILTER(lang(?l) = "{language}") }}')
    url = f"{SPARQL_URL}?{urllib.parse.urlencode({'query': query})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/csv"})
    with urllib.request.urlopen(request, timeout=120) as response:
        rows = list(csv.DictReader(response.read().decode("utf-8").splitlines()))
    labels = {}
    for row in rows:
        code = row["n"]
        if len(code) == 5:  # classes: '62.01'
            labels[code] = row["l"].removeprefix(code).strip()
    if len(labels) != 615:
        raise ValueError(f"{len(labels)} NACE Rev. 2 classes in {language}, expected 615")
    return dict(sorted(labels.items()))


def main():
    if "--labels-only" in sys.argv[1:]:  # the NACE labels of the languages missing from the cache
        with open(LABELS_PATH, encoding="utf-8") as f:
            cached = json.load(f)
        for language in LANGUAGES:
            if language not in cached["labels"]:
                cached["labels"][language] = fetch_labels(language)
        with open(LABELS_PATH, "w", encoding="utf-8") as f:
            json.dump(cached, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print(f"NACE labels ({', '.join(cached['labels'])}) → {LABELS_PATH}")
        return
    if "--download" in sys.argv[1:]:
        download()
    data = isco_naf(read_census(), read_matrix())
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"source": SOURCE, "isco_naf": data}, f, ensure_ascii=False, indent=0)
        f.write("\n")
    print(f"{len(data)} ISCO unit groups → {OUTPUT_PATH}")
    os.makedirs(os.path.dirname(LABELS_PATH), exist_ok=True)
    labels = {language: fetch_labels(language) for language in LANGUAGES}
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump({"source": LABELS_SOURCE, "labels": labels}, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"NACE labels ({', '.join(LANGUAGES)}) → {LABELS_PATH}")


if __name__ == "__main__":
    main()
