#!/usr/bin/env python3
"""
Script pour remplacer les coordonnées de faker_locations.csv (centre du pays
dans le dataset d'origine) par celles de la ville, via Nominatim (OpenStreetMap).

- 1 requête par seconde maximum (politique d'usage de Nominatim)
- Résultats mis en cache dans geocode_cache.json : une relance ne refait
  pas les requêtes déjà résolues
- Un résultat trop éloigné de l'ancienne position (centre du pays) est
  signalé et la ligne est laissée inchangée

Usage : python3 geocode_locations.py [fichier_sortie]
"""

import csv
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'DATAS'

input_file = DATA_DIR / 'faker_locations.csv'
output_file = Path(sys.argv[1]) if len(sys.argv) > 1 else input_file
cache_file = DATA_DIR / 'geocode_cache.json'

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
USER_AGENT = 'faker-jobs-geocoder/1.0'

# Distance maximale (km) entre la ville trouvée et l'ancienne position
MAX_DISTANCE_KM = 4000

# Lignes vérifiées à la main dont l'ancienne position est fausse :
# le contrôle de distance n'a pas de sens pour elles
DISTANCE_CHECK_EXCEPTIONS = {
    ('Mbabane', 'Eswatini'),  # ancienne latitude de signe inversé (+26.5 au lieu de -26.5)
}

# Requêtes forcées quand le nom du fichier ne suffit pas à Nominatim
QUERY_OVERRIDES = {
    ('Marigot', 'St. Martin (French part)'): 'Marigot, Saint-Martin',
    ('Philipsburg', 'Sint Maarten (Dutch part)'): 'Philipsburg, Sint Maarten',
    ('Charlotte Amalie', 'Virgin Islands (U.S.)'): 'Charlotte Amalie, U.S. Virgin Islands',
    ('Tarawa', 'Kiribati'): 'South Tarawa, Kiribati',
    ('Victoria', 'Hong Kong'): 'Central, Hong Kong',
    ('Sri Jayawardenepura Kotte', 'Sri Lanka'): 'Kotte, Sri Lanka',
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Distance orthodromique en kilomètres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def build_queries(location, country):
    """
    Requêtes (texte, villes uniquement ?) à essayer dans l'ordre, sans les
    mentions entre parenthèses. La ville seule sert quand Nominatim ne
    reconnaît pas le nom du pays (ex. 'Lao PDR') ; la recherche sans filtre
    sur les villes n'est qu'un dernier recours.
    """
    if (location, country) in QUERY_OVERRIDES:
        texts = [QUERY_OVERRIDES[(location, country)]]
    else:
        city = re.sub(r'\s*\(.*?\)', '', location).strip()
        country = re.sub(r'\s*\(.*?\)', '', country).strip()
        texts = [f'{city}, {country}', city]
    return [(t, True) for t in texts] + [(texts[0], False)]


last_request = 0.0


def nominatim(query, settlement_only):
    """Renvoie (lat, lon, display_name) du premier résultat, ou None."""
    global last_request
    wait = 1.0 - (time.monotonic() - last_request)
    if wait > 0:
        time.sleep(wait)
    params = {'q': query, 'format': 'json', 'limit': 1, 'accept-language': 'en'}
    if settlement_only:
        params['featureType'] = 'settlement'
    url = NOMINATIM_URL + '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        results = json.load(response)
    last_request = time.monotonic()
    if not results:
        return None
    return float(results[0]['lat']), float(results[0]['lon']), results[0]['display_name']


cache = json.loads(cache_file.read_text(encoding='utf-8')) if cache_file.exists() else {}

with open(input_file, 'r', encoding='utf-8', newline='') as infile:
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    rows = list(reader)

problems = []
for row in rows:
    key = f"{row['location']}|{row['Country']}"
    if key not in cache:
        for query, settlement_only in build_queries(row['location'], row['Country']):
            result = nominatim(query, settlement_only)
            if result:
                cache[key] = {'query': query, 'settlement_only': settlement_only,
                              'lat': result[0], 'lon': result[1], 'display_name': result[2]}
                break
        else:
            cache[key] = None
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding='utf-8')

    hit = cache[key]
    if hit is None:
        problems.append(f"Introuvable : {key}")
        continue

    distance = haversine_km(float(row['latitude']), float(row['longitude']), hit['lat'], hit['lon'])
    if distance > MAX_DISTANCE_KM and (row['location'], row['Country']) not in DISTANCE_CHECK_EXCEPTIONS:
        problems.append(f"Trop loin ({distance:.0f} km) : {key} -> {hit['display_name']}")
        continue

    row['latitude'] = f"{hit['lat']:.4f}"
    row['longitude'] = f"{hit['lon']:.4f}"

with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)

print(f"Géocodage terminé. Fichier généré : {output_file}")
if problems:
    print(f"{len(problems)} ligne(s) laissée(s) inchangée(s) :")
    for p in problems:
        print(f"  {p}")
else:
    print("Toutes les lignes ont été géocodées.")
