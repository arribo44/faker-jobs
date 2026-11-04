#!/usr/bin/env python3
"""
Script pour corriger les problèmes d'encodage UTF-8 (mojibake, ex. 'BogotÃ¡')
dans un fichier CSV : le texte UTF-8 a été relu en Latin-1 / CP1252, on
inverse donc l'opération ligne par ligne.

Usage : python3 fix_locations_encoding.py [entrée] [sortie]
"""

import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'DATAS'

input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR / 'faker_locations.csv'
output_file = Path(sys.argv[2]) if len(sys.argv) > 2 else input_file.with_name(input_file.stem + '_fixed.csv')


def fix_mojibake(text):
    """Réencode en CP1252 puis Latin-1 et redécode en UTF-8 ; renvoie le texte inchangé si ce n'est pas du mojibake."""
    for encoding in ('cp1252', 'latin-1'):
        try:
            return text.encode(encoding).decode('utf-8')
        except UnicodeError:
            continue
    return text


with open(input_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_lines = []
for i, line in enumerate(lines):
    fixed = fix_mojibake(line).replace('Nuku?alofa', "Nuku'alofa")
    if fixed != line:
        print(f"Ligne {i+1}: {line.strip()} -> {fixed.strip()}")
    fixed_lines.append(fixed)

with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print(f"Fichier corrigé : {output_file}")
