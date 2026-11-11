"""
Local job conditions of the occupation postings (job_occupation_posting()
and job_posting()), by occupation locale: contract types, benefits, job
boards, diplomas, wording of the experience and salary, minimum wage.

Hand-made and ILLUSTRATIVE: the national contract mix of the postings,
benefit rules and default diplomas give plausible postings, they are not
statistics. Salaries are not here: build_occupations.py derives them from
Eurostat (France, Germany, Spain, Italy) and BLS (United States) earnings,
and adapts the contract mix to each occupation (see contract_weights()
there): Eurostat shares of temporary, part-time and self-employed workers
of its ISCO major group, and in French locales the share of seasonal
recruitment projects of the occupation (BMO).

Shared vocabulary:
- skill levels, from the ISCO-08 major group of the occupation: 'high'
  (1 managers, 2 professionals), 'mid' (3 technicians and associate
  professionals, 0 armed forces), 'low' (4 to 9);
- contracts: name -> {"weight": relative weight in the national mix (they
  add up to 100), "kind": 'permanent', 'temporary', 'part_time',
  'seasonal', 'apprentice', 'intern', 'freelance' or 'other' (the
  kind says which figure adapts the weight to the occupation; 'other',
  'apprentice' and 'intern' keep it), "salary_factor": share of
  a full-time salary (internships, apprenticeships, part-time),
  "max_experience": cap on the years of experience asked (0 for
  internships and apprenticeships), "employee": False for freelancers};
- benefits: name -> {"requires": None (every job), "office" (an office job
  or an executive one) or "executive", "not_for": contract types that
  never get it}; non-employees (freelancers) only get the "office" benefits
  (remote work, flexible hours);
- salary_format: the posting's salary text, with {min} / {max} formatted
  with the `thousands` separator;
- qualifications: default diplomas by skill level, asked when the
  occupation has none of its own (ESCO occupations; ROME sheets without
  diploma); "{field}" is the field of study of the occupation's sector
  (FIELDS_OF_STUDY), e.g. "Bachelor im Bereich Logistik";
- experience_none / experience_range: texts for 0 years and for a range.
- place_names (optional): {"country": local name of the country}, shown
  for the locations in the country (`country` is the English name of the
  location data); the local names of its cities come from GeoNames (see
  build_cities.py).
"""

# Years of experience asked, by skill level: [min, max] of the minimum,
# [min, max] of the gap to the maximum.
EXPERIENCE = {
    "high": {"low": [0, 8], "gap": [2, 5]},
    "mid": {"low": [0, 6], "gap": [2, 4]},
    "low": {"low": [0, 4], "gap": [1, 3]},
}

CONDITIONS = {
    "fr_FR": {
        "country": "France",
        "currency": "EUR",
        "contracts": {
            "CDI": {"weight": 55, "kind": "permanent"},
            "CDD": {"weight": 20, "kind": "temporary"},
            # Weight set by the share of seasonal recruitment projects of the occupation (BMO).
            "CDD saisonnier": {"weight": 0, "kind": "seasonal"},
            "Intérim": {"weight": 12, "kind": "temporary"},
            "Alternance": {"weight": 6, "kind": "apprentice", "salary_factor": 0.55, "max_experience": 0},
            "Stage": {"weight": 4, "kind": "intern", "salary_factor": 0.3, "max_experience": 0},
            "Freelance": {"weight": 3, "kind": "freelance", "employee": False},
        },
        "salary_format": {"template": "{min} € - {max} € brut/an", "thousands": " "},
        # SMIC 2022 (35 h/week), yearly.
        "minimum_wage": 20_150,
        "experience_none": "Débutant accepté",
        "experience_range": "{min} à {max} ans",
        # Asked when the ROME sheet lists no diploma.
        "qualifications": {
            "high": ["Bac+5 (Master, école d'ingénieur ou de commerce)", "Bac+3 (Licence, BUT)",
                     "Master {field}", "Licence professionnelle {field}"],
            "mid": ["Bac+2 (BTS, DUT)", "Bac+3 (Licence, BUT)", "BTS {field}", "BUT {field}"],
            "low": ["CAP / BEP", "Bac pro", "Bac", "CAP {field}", "Bac pro {field}"],
        },
        "benefits": {
            "Mutuelle d'entreprise": {"requires": None, "not_for": []},
            "Tickets restaurant": {"requires": None, "not_for": []},
            "RTT": {"requires": None, "not_for": ["Stage"]},
            "Prime annuelle": {"requires": None, "not_for": ["Stage"]},
            "13e mois": {"requires": None, "not_for": ["Stage"]},
            "Intéressement et participation": {"requires": None, "not_for": ["Stage", "Intérim"]},
            "Plan d'épargne entreprise (PEE)": {"requires": None, "not_for": ["Stage", "Intérim"]},
            "Télétravail partiel": {"requires": "office", "not_for": []},
            "Remboursement à 50 % du titre de transport": {"requires": None, "not_for": []},
            "Comité social et économique (CSE)": {"requires": None, "not_for": []},
            "Formation continue": {"requires": None, "not_for": []},
            "Horaires flexibles": {"requires": "office", "not_for": []},
            "Prime de vacances": {"requires": None, "not_for": ["Stage"]},
            "Chèques cadeaux": {"requires": None, "not_for": []},
            "Véhicule de fonction": {"requires": "executive", "not_for": ["Stage", "Alternance"]},
            "Forfait mobilités durables": {"requires": None, "not_for": []},
        },
        "job_portals": {
            "all": ["France Travail", "HelloWork", "Indeed", "LinkedIn", "Welcome to the Jungle", "Meteojob",
                    "Jobteaser", "Monster", "Le Bon Coin Emploi"],
            "executive": ["APEC", "Cadremploi"],
        },
    },
    "de_DE": {
        "country": "Germany",
        # Names shown in the postings of the country (the location data is in English).
        "place_names": {"country": "Deutschland"},
        "currency": "EUR",
        "contracts": {
            "Unbefristet": {"weight": 58, "kind": "permanent"},
            "Befristet": {"weight": 18, "kind": "temporary"},
            "Zeitarbeit": {"weight": 10, "kind": "temporary"},
            "Teilzeit": {"weight": 6, "kind": "part_time", "salary_factor": 0.5},
            "Ausbildung": {"weight": 4, "kind": "apprentice", "salary_factor": 0.35, "max_experience": 0},
            "Praktikum": {"weight": 2, "kind": "intern", "salary_factor": 0.3, "max_experience": 0},
            "Freiberuflich": {"weight": 2, "kind": "freelance", "employee": False},
        },
        "salary_format": {"template": "{min} € - {max} € brutto/Jahr", "thousands": "."},
        # Mindestlohn 12 €/h (October 2022), 40 h/week, yearly.
        "minimum_wage": 24_960,
        "experience_none": "Berufseinsteiger willkommen",
        "experience_range": "{min} bis {max} Jahre Berufserfahrung",
        "qualifications": {
            "high": ["Master", "Diplom", "Bachelor", "Master im Bereich {field}", "Bachelor im Bereich {field}",
                     "Abgeschlossenes Studium im Bereich {field}", "Promotion"],
            "mid": ["Bachelor", "Techniker / Meister", "Abgeschlossene Berufsausbildung", "Fachwirt",
                    "Bachelor im Bereich {field}", "Meister oder Techniker im Bereich {field}",
                    "Abgeschlossene Berufsausbildung im Bereich {field}"],
            "low": ["Abgeschlossene Berufsausbildung", "Hauptschulabschluss", "Realschulabschluss",
                    "Mittlere Reife", "Abgeschlossene Berufsausbildung im Bereich {field}"],
        },
        "benefits": {
            "Betriebliche Altersvorsorge": {"requires": None, "not_for": ["Praktikum", "Zeitarbeit"]},
            "Deutschlandticket / Jobticket": {"requires": None, "not_for": []},
            "30 Tage Urlaub": {"requires": None, "not_for": ["Praktikum"]},
            "Weihnachtsgeld": {"requires": None, "not_for": ["Praktikum"]},
            "Urlaubsgeld": {"requires": None, "not_for": ["Praktikum"]},
            "Homeoffice": {"requires": "office", "not_for": []},
            "Flexible Arbeitszeiten": {"requires": "office", "not_for": []},
            "JobRad": {"requires": None, "not_for": ["Praktikum", "Zeitarbeit"]},
            "Weiterbildungsmöglichkeiten": {"requires": None, "not_for": []},
            "Betriebliches Gesundheitsmanagement": {"requires": None, "not_for": []},
            "Mitarbeiterrabatte": {"requires": None, "not_for": []},
            "Firmenwagen": {"requires": "executive", "not_for": ["Praktikum", "Ausbildung", "Teilzeit"]},
        },
        "job_portals": {
            "all": ["StepStone", "Indeed", "LinkedIn", "XING", "Bundesagentur für Arbeit", "Monster",
                    "Jobware", "kununu"],
        },
    },
    "es_ES": {
        "country": "Spain",
        "place_names": {"country": "España"},
        "currency": "EUR",
        "contracts": {
            "Indefinido": {"weight": 55, "kind": "permanent"},
            "Temporal": {"weight": 20, "kind": "temporary"},
            "Fijo discontinuo": {"weight": 8, "kind": "other"},
            "A través de ETT": {"weight": 7, "kind": "temporary"},
            "Formación en alternancia": {"weight": 4, "kind": "apprentice", "salary_factor": 0.55, "max_experience": 0},
            "Prácticas": {"weight": 3, "kind": "intern", "salary_factor": 0.4, "max_experience": 0},
            "Autónomo": {"weight": 3, "kind": "freelance", "employee": False},
        },
        "salary_format": {"template": "{min} € - {max} € brutos/año", "thousands": "."},
        # Salario mínimo interprofesional 2022, yearly (14 payments).
        "minimum_wage": 14_000,
        "experience_none": "Sin experiencia previa",
        "experience_range": "De {min} a {max} años de experiencia",
        "qualifications": {
            "high": ["Grado universitario", "Máster", "Ingeniería superior", "Grado en {field}", "Máster en {field}",
                     "Doctorado"],
            "mid": ["Ciclo Formativo de Grado Superior", "Grado universitario",
                    "Ciclo Formativo de Grado Superior en {field}", "Grado en {field}"],
            "low": ["ESO", "Ciclo Formativo de Grado Medio", "Bachillerato", "FP Básica",
                    "Ciclo Formativo de Grado Medio en {field}", "Certificado de profesionalidad en {field}"],
        },
        "benefits": {
            "Seguro médico privado": {"requires": None, "not_for": ["Prácticas"]},
            "Ticket restaurante": {"requires": None, "not_for": []},
            "Retribución flexible": {"requires": None, "not_for": ["Prácticas", "A través de ETT"]},
            "Teletrabajo parcial": {"requires": "office", "not_for": []},
            "Horario flexible": {"requires": "office", "not_for": []},
            "Jornada intensiva en verano": {"requires": "office", "not_for": []},
            "Formación continua": {"requires": None, "not_for": []},
            "Plan de pensiones": {"requires": None, "not_for": ["Prácticas", "Temporal", "A través de ETT"]},
            "Bonus anual por objetivos": {"requires": None, "not_for": ["Prácticas"]},
            "Descuentos para empleados": {"requires": None, "not_for": []},
            "Coche de empresa": {"requires": "executive", "not_for": ["Prácticas", "Formación en alternancia"]},
        },
        "job_portals": {
            "all": ["InfoJobs", "Indeed", "LinkedIn", "InfoEmpleo", "Jooble", "Trabajos.com", "SEPE Empléate"],
        },
    },
    "it_IT": {
        "country": "Italy",
        "place_names": {"country": "Italia"},
        "currency": "EUR",
        "contracts": {
            "Tempo indeterminato": {"weight": 50, "kind": "permanent"},
            "Tempo determinato": {"weight": 24, "kind": "temporary"},
            "Somministrazione": {"weight": 10, "kind": "temporary"},
            "Apprendistato": {"weight": 7, "kind": "apprentice", "salary_factor": 0.65, "max_experience": 0},
            "Stage": {"weight": 5, "kind": "intern", "salary_factor": 0.3, "max_experience": 0},
            "Partita IVA": {"weight": 4, "kind": "freelance", "employee": False},
        },
        "salary_format": {"template": "RAL {min} € - {max} €", "thousands": "."},
        # No statutory minimum wage in Italy (wages are set by the collective agreements).
        "minimum_wage": None,
        "experience_none": "Anche prima esperienza",
        "experience_range": "Da {min} a {max} anni di esperienza",
        "qualifications": {
            "high": ["Laurea magistrale", "Laurea triennale", "Laurea magistrale in {field}",
                     "Laurea triennale in {field}", "Master di I livello in {field}", "Dottorato di ricerca"],
            "mid": ["Laurea triennale", "Diploma ITS", "Diploma di scuola superiore", "Diploma di istituto tecnico",
                    "Laurea triennale in {field}", "Diploma ITS Academy in {field}"],
            "low": ["Licenza media", "Qualifica professionale", "Diploma di scuola superiore",
                    "Diploma di istituto professionale", "Qualifica professionale in {field}"],
        },
        "benefits": {
            "Buoni pasto": {"requires": None, "not_for": []},
            "Assistenza sanitaria integrativa": {"requires": None, "not_for": ["Stage"]},
            "Welfare aziendale": {"requires": None, "not_for": ["Stage", "Somministrazione"]},
            "Smart working": {"requires": "office", "not_for": []},
            "Orario flessibile": {"requires": "office", "not_for": []},
            "Premio di produzione": {"requires": None, "not_for": ["Stage"]},
            "Quattordicesima": {"requires": None, "not_for": ["Stage"]},
            "Fondo pensione integrativo": {"requires": None, "not_for": ["Stage", "Somministrazione"]},
            "Formazione continua": {"requires": None, "not_for": []},
            "Convenzioni per i dipendenti": {"requires": None, "not_for": []},
            "Auto aziendale": {"requires": "executive", "not_for": ["Stage", "Apprendistato"]},
        },
        "job_portals": {
            "all": ["Indeed", "LinkedIn", "InfoJobs", "Monster", "Subito Lavoro", "Bakeca", "Jobrapido"],
        },
    },
    "en_US": {
        "country": "United States",
        "currency": "USD",
        "contracts": {
            "Full-time": {"weight": 62, "kind": "permanent"},
            "Part-time": {"weight": 15, "kind": "part_time", "salary_factor": 0.5},
            "Contract": {"weight": 10, "kind": "temporary"},
            "Temporary": {"weight": 7, "kind": "temporary"},
            "Internship": {"weight": 4, "kind": "intern", "salary_factor": 0.4, "max_experience": 0},
            "Freelance": {"weight": 2, "kind": "freelance", "employee": False},
        },
        "salary_format": {"template": "${min} - ${max} a year", "thousands": ","},
        # Federal minimum wage, $7.25/h, 2,080 h/year.
        "minimum_wage": 15_080,
        "experience_none": "Entry level",
        "experience_range": "{min}-{max} years of experience",
        "qualifications": {
            "high": ["Bachelor's degree", "Master's degree", "Bachelor's degree in {field}",
                     "Master's degree in {field}", "Doctoral degree"],
            "mid": ["Associate degree", "Bachelor's degree", "Professional certification",
                    "Associate degree in {field}", "Bachelor's degree in {field}",
                    "Postsecondary certificate in {field}"],
            "low": ["High school diploma or GED", "Vocational training", "Vocational training in {field}",
                    "Apprenticeship in {field}"],
        },
        "benefits": {
            "Health insurance": {"requires": None, "not_for": ["Part-time", "Temporary", "Internship"]},
            "Dental insurance": {"requires": None, "not_for": ["Part-time", "Temporary", "Internship"]},
            "Vision insurance": {"requires": None, "not_for": ["Part-time", "Temporary", "Internship"]},
            "401(k) matching": {"requires": None, "not_for": ["Temporary", "Internship", "Contract"]},
            "Paid time off": {"requires": None, "not_for": ["Contract"]},
            "Remote work": {"requires": "office", "not_for": []},
            "Flexible schedule": {"requires": "office", "not_for": []},
            "Tuition reimbursement": {"requires": None, "not_for": ["Temporary", "Internship", "Contract"]},
            "Life insurance": {"requires": None, "not_for": ["Part-time", "Temporary", "Internship"]},
            "Performance bonus": {"requires": None, "not_for": ["Internship"]},
            "Stock options": {"requires": "executive", "not_for": ["Internship", "Part-time", "Temporary"]},
            "Commuter benefits": {"requires": None, "not_for": []},
            "Employee discount": {"requires": None, "not_for": []},
            "Paid parental leave": {"requires": None, "not_for": ["Temporary", "Internship", "Contract"]},
        },
        "job_portals": {
            "all": ["Indeed", "LinkedIn", "Glassdoor", "ZipRecruiter", "Monster", "CareerBuilder",
                    "SimplyHired"],
        },
    },
}

BENEFITS_PER_POSTING = 4

# ISCO-08 major group -> skill level.
SKILL_LEVELS = {"1": "high", "2": "high", "3": "mid", "0": "mid",
                "4": "low", "5": "low", "6": "low", "7": "low", "8": "low", "9": "low"}


# Field of study of the default diplomas, by ROME activity sector code (see
# rome_labels.SECTORS) and occupation locale: the "{field}" of the
# qualifications. Hand-made, after the national names of the study fields
# (Ausbildungsberufe, familias profesionales de FP, classi di laurea...).
FIELDS_OF_STUDY = {
    "fr_FR": {
        "100": "mécanique et productique", "101": "tourisme", "102": "hôtellerie-restauration",
        "103": "gestion des entreprises et des administrations", "104": "électronique", "105": "sciences",
        "106": "chimie", "107": "bois et ameublement", "108": "énergétique", "109": "travail social",
        "110": "droit ou comptabilité", "111": "administration publique et sécurité",
        "112": "sciences de l'éducation", "113": "transport et logistique", "79": "agriculture",
        "80": "environnement", "81": "maintenance et hygiène des locaux", "82": "patrimoine culturel",
        "83": "industries agroalimentaires", "84": "productique", "85": "santé", "86": "coiffure et esthétique",
        "87": "arts et audiovisuel", "88": "commerce", "89": "industries graphiques", "90": "mode et textile",
        "91": "banque, finance et assurance", "92": "immobilier", "93": "sport et animation",
        "94": "communication et marketing", "95": "maintenance automobile", "96": "informatique",
        "97": "édition et journalisme", "98": "architecture ou ingénierie", "99": "bâtiment et travaux publics",
    },
    "de_DE": {
        "100": "Metalltechnik", "101": "Tourismus", "102": "Hotellerie und Gastronomie", "103": "Betriebswirtschaft",
        "104": "Elektrotechnik", "105": "Naturwissenschaften", "106": "Chemie", "107": "Holztechnik",
        "108": "Energietechnik", "109": "Soziale Arbeit", "110": "Recht oder Rechnungswesen",
        "111": "Öffentliche Verwaltung", "112": "Pädagogik", "113": "Logistik", "79": "Agrarwirtschaft",
        "80": "Umwelttechnik", "81": "Gebäudetechnik", "82": "Kulturwissenschaften", "83": "Lebensmitteltechnik",
        "84": "Produktionstechnik", "85": "Pflege und Gesundheit", "86": "Körperpflege",
        "87": "Medien und darstellende Kunst", "88": "Handel", "89": "Druck- und Medientechnik",
        "90": "Textil und Mode", "91": "Bank- und Finanzwesen", "92": "Immobilienwirtschaft",
        "93": "Sportwissenschaft", "94": "Kommunikation und Marketing", "95": "Kfz-Technik", "96": "Informatik",
        "97": "Medien und Publizistik", "98": "Architektur oder Ingenieurwesen", "99": "Bautechnik",
    },
    "es_ES": {
        "100": "Fabricación Mecánica", "101": "Turismo", "102": "Hostelería", "103": "Administración y Gestión",
        "104": "Electricidad y Electrónica", "105": "Ciencias", "106": "Química", "107": "Madera y Mueble",
        "108": "Energía y Agua", "109": "Servicios Socioculturales y a la Comunidad",
        "110": "Derecho o Contabilidad", "111": "Administración Pública", "112": "Educación",
        "113": "Transporte y Logística", "79": "Agraria", "80": "Ciencias Ambientales",
        "81": "Instalación y Mantenimiento", "82": "Historia del Arte y Patrimonio", "83": "Industrias Alimentarias",
        "84": "Ingeniería Industrial", "85": "Sanidad", "86": "Imagen Personal", "87": "Imagen y Sonido",
        "88": "Comercio y Marketing", "89": "Artes Gráficas", "90": "Textil, Confección y Piel",
        "91": "Finanzas", "92": "Gestión Inmobiliaria", "93": "Actividades Físicas y Deportivas",
        "94": "Marketing y Publicidad", "95": "Transporte y Mantenimiento de Vehículos",
        "96": "Informática y Comunicaciones", "97": "Periodismo", "98": "Arquitectura o Ingeniería",
        "99": "Edificación y Obra Civil",
    },
    "it_IT": {
        "100": "Meccanica", "101": "Turismo", "102": "Enogastronomia e ospitalità alberghiera",
        "103": "Economia aziendale", "104": "Elettronica", "105": "Scienze naturali", "106": "Chimica",
        "107": "Tecnologia del legno", "108": "Ingegneria energetica", "109": "Servizio sociale",
        "110": "Giurisprudenza o Economia", "111": "Scienze dell'amministrazione", "112": "Scienze della formazione",
        "113": "Logistica e trasporti", "79": "Scienze agrarie", "80": "Scienze ambientali",
        "81": "Manutenzione e assistenza tecnica", "82": "Beni culturali", "83": "Scienze e tecnologie alimentari",
        "84": "Ingegneria industriale", "85": "Professioni sanitarie", "86": "Acconciatura ed estetica",
        "87": "Arti e spettacolo", "88": "Servizi commerciali", "89": "Grafica e comunicazione", "90": "Moda",
        "91": "Economia e finanza", "92": "Economia immobiliare", "93": "Scienze motorie",
        "94": "Comunicazione e marketing", "95": "Manutenzione dei mezzi di trasporto", "96": "Informatica",
        "97": "Editoria e giornalismo", "98": "Architettura o Ingegneria", "99": "Costruzioni, ambiente e territorio",
    },
    "en_US": {
        "100": "Mechanical Engineering", "101": "Tourism Management", "102": "Hospitality Management",
        "103": "Business Administration", "104": "Electrical Engineering", "105": "Natural Sciences",
        "106": "Chemistry", "107": "Wood Technology", "108": "Energy Engineering", "109": "Social Work",
        "110": "Law or Accounting", "111": "Public Administration", "112": "Education",
        "113": "Logistics and Transportation", "79": "Agriculture", "80": "Environmental Science",
        "81": "Facility Maintenance", "82": "Cultural Heritage", "83": "Food Science",
        "84": "Industrial Engineering", "85": "Health Sciences", "86": "Cosmetology",
        "87": "Fine and Performing Arts", "88": "Retail Management", "89": "Graphic Communications",
        "90": "Fashion Design", "91": "Finance", "92": "Real Estate", "93": "Sports Science",
        "94": "Marketing and Communications", "95": "Automotive Technology", "96": "Computer Science",
        "97": "Journalism and Publishing", "98": "Architecture or Engineering", "99": "Construction Management",
    },
}
