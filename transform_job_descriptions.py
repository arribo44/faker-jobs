#!/usr/bin/env python3
"""
Script pour transformer le job_descriptions.csv d'origine (dans save/archive.zip)
en job_descriptions2.csv
- Séparateur : ; (point-virgule) au lieu de , (virgule)
- Chaque champ entouré de guillemets "
- Noms de lieux / pays contenant une virgule normalisés (voir LOCATION_FIXES / COUNTRY_FIXES)

Le fichier est lu en flux directement dans l'archive (pas besoin de la décompresser).

Usage : python3 transform_job_descriptions.py [fichier_sortie]
"""

import csv
import io
import sys
import zipfile
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'DATAS'

# Chemins des fichiers
archive_file = DATA_DIR / 'save' / 'archive.zip'
archive_member = 'job_descriptions.csv'
output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / 'job_descriptions2.csv'

# Index des colonnes à normaliser
LOCATION_COL = 4
COUNTRY_COL = 5

LOCATION_FIXES = {
    'Capitol Hill, Saipan': 'Saipan',
    'Malabo (de jure),': 'Malabo',
    'Washington, D.C.': 'Washington D.C.',
}

COUNTRY_FIXES = {
    'Bahamas, The': 'The Bahamas',
    'Hong Kong SAR, China': 'China',
    'Iran, Islamic Rep.': 'Islamic Rep. of Iran',
    'Korea, Rep.': 'Rep. of Korea',
    'Macao SAR, China': 'China',
    'Macedonia, FYR': 'North Macedonia',
    'Micronesia, Fed. Sts.': 'Micronesia',
    'Venezuela, RB': 'Venezuela',
}

with zipfile.ZipFile(archive_file) as archive, archive.open(archive_member) as raw:
    infile = io.TextIOWrapper(raw, encoding='utf-8', newline='')
    reader = csv.reader(infile)

    # Écrire le fichier de sortie ligne par ligne avec ; comme séparateur et guillemets autour de chaque champ
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        for row in reader:
            row[LOCATION_COL] = LOCATION_FIXES.get(row[LOCATION_COL], row[LOCATION_COL])
            row[COUNTRY_COL] = COUNTRY_FIXES.get(row[COUNTRY_COL], row[COUNTRY_COL])
            writer.writerow(row)

print(f"Transformation terminée. Fichier généré : {output_file}")
