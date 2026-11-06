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
- experience_none / experience_range: texts for 0 years and for a range.
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
            "high": ["Bac+5 (Master, école d'ingénieur ou de commerce)", "Bac+3 (Licence, BUT)"],
            "mid": ["Bac+2 (BTS, DUT)", "Bac+3 (Licence, BUT)"],
            "low": ["CAP / BEP", "Bac pro", "Bac"],
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
            "high": ["Master", "Diplom", "Bachelor"],
            "mid": ["Bachelor", "Techniker / Meister", "Abgeschlossene Berufsausbildung"],
            "low": ["Abgeschlossene Berufsausbildung", "Hauptschulabschluss", "Realschulabschluss"],
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
            "high": ["Grado universitario", "Máster", "Ingeniería superior"],
            "mid": ["Ciclo Formativo de Grado Superior", "Grado universitario"],
            "low": ["ESO", "Ciclo Formativo de Grado Medio", "Bachillerato"],
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
            "high": ["Laurea magistrale", "Laurea triennale"],
            "mid": ["Laurea triennale", "Diploma ITS", "Diploma di scuola superiore"],
            "low": ["Licenza media", "Qualifica professionale", "Diploma di scuola superiore"],
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
        "country": "USA",
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
            "high": ["Bachelor's degree", "Master's degree"],
            "mid": ["Associate degree", "Bachelor's degree", "Professional certification"],
            "low": ["High school diploma or GED", "Vocational training"],
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
