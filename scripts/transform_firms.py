#!/usr/bin/env python3
"""
Script pour transformer firms.csv en faker_firms.csv
Extrait les champs : company, sector, industry, city, state, zip, website, ticker, ceo

Usage : python3 scripts/transform_firms.py [fichier_sortie]
"""

import csv
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / 'DATAS'

# Chemins des fichiers
input_file = DATA_DIR / 'firms.csv'
output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / 'faker_firms.csv'

# Champs à extraire dans l'ordre souhaité, avec leur clé dans le profil source
fields = ['company', 'sector', 'industry', 'city', 'state', 'zip', 'website', 'ticker', 'ceo']
profile_keys = ['Sector', 'Industry', 'City', 'State', 'Zip', 'Website', 'Ticker', 'CEO']

# Une paire 'Clé':'valeur' ; la valeur se termine sur une apostrophe suivie
# de la clé suivante ou de l'accolade finale, ce qui tolère les apostrophes
# dans les valeurs (ex. 'CEO':'Chris O'Shea')
PAIR_RE = re.compile(r"'(\w+)':'(.*?)'(?=,'\w+':|\s*}$)")

# Valeurs considérées comme manquantes, remplacées par un champ vide
MISSING_VALUES = {'N/A'}


def parse_profile(s):
    """Parse une chaîne de dict Python avec apostrophes en dict Python."""
    return dict(PAIR_RE.findall(s.strip()))


with open(input_file, 'r', encoding='utf-8', newline='') as infile:
    reader = csv.reader(infile, delimiter=';')
    next(reader)  # en-tête du CSV source
    rows = list(reader)

errors = 0
with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    writer = csv.writer(outfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(fields)

    for row in rows:
        if len(row) < 2 or not row[1].startswith('{'):
            errors += 1
            print(f"Ligne ignorée (colonne données vide/invalide) : {row}")
            continue

        company, data_str = row[0], row[1]
        data = parse_profile(data_str)

        missing = [k for k in profile_keys if k not in data]
        if missing:
            errors += 1
            print(f"Clés manquantes {missing} - {company}: {data_str[:100]}...")

        values = [data.get(k, '').strip() for k in profile_keys]
        writer.writerow([company] + ['' if v in MISSING_VALUES else v for v in values])

print(f"Transformation terminée. Fichier généré : {output_file}")
if errors > 0:
    print(f"Nombre d'erreurs/ignorées : {errors}")
else:
    print("Aucune erreur.")
