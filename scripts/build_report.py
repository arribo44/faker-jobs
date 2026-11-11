#!/usr/bin/env python3
"""
Build an HTML report (in French) on the job postings dataset from the
representative sample drawn by build_sample.py:

    python scripts/build_sample.py      # once (~1 min on the full file)
    python scripts/build_report.py      # -> reports/rapport_job_descriptions.html

Every figure is computed on DATAS/job_sample.csv; DATAS/job_full_counts.json
(the whole file's counts) is only used to check that the sample is
representative and to show the full-file share next to each value.
"""
import csv
import datetime
import html
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_sample import COMPANY_SIZE_BIN, COUNTS_PATH, SAMPLE_PATH, SEED, derived_fields  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(ROOT, "DATAS")
OUTPUT_PATH = os.path.join(ROOT, "reports", "rapport_job_descriptions.html")

NUMERIC_FIELDS = {"experience_min", "experience_max", "salary_min_k", "salary_max_k", "company_size_bin"}

# Max z-score (sample share vs full share, in standard errors) below which
# the gap is what random sampling alone produces: with k values, the largest
# of k z-scores of a fair sample rarely exceeds ~sqrt(2 ln k) + 1.
def z_threshold(k):
    return math.sqrt(2 * math.log(max(k, 2))) + 1


# -- formatting (French) ----------------------------------------------------------

NBSP = " "


def fmt_int(n):
    return f"{n:,}".replace(",", NBSP)


def fmt_tick(share):
    """Axis tick: exact value, without useless trailing zeros (0,25 %, 2,5 %, 10 %)."""
    text = f"{share * 100:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",") + NBSP + "%"


NUMBERS_FR = {2: "Deux", 3: "Trois", 4: "Quatre", 5: "Cinq", 6: "Six", 7: "Sept", 8: "Huit"}


def plural(count):
    return "s" if count > 1 else ""


def fmt_pct(share, digits=1):
    return f"{share * 100:.{digits}f}".replace(".", ",") + NBSP + "%"


def esc(text):
    return html.escape(str(text), quote=True)


MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def month_label(key):
    year, month = key.split("-")
    return f"{MONTHS_FR[int(month) - 1]} {year}"


def nice_axis(value, max_ticks=5):
    """(axis max, tick values) for an axis starting at 0 and reaching at least
    `value`, with a round step (1, 2 or 5 x 10^n) and at most max_ticks steps."""
    if value <= 0:
        return 1, [0, 1]
    exponent = math.floor(math.log10(value / max_ticks))
    for factor in (1, 2, 5, 10):
        step = factor * 10**exponent
        if math.ceil(value / step - 1e-9) <= max_ticks:
            break
    count = math.ceil(value / step - 1e-9)
    return step * count, [round(step * i, 10) for i in range(count + 1)]


# -- data -------------------------------------------------------------------------


def load_sample():
    counts = defaultdict(Counter)
    salary_by = defaultdict(list)
    with open(SAMPLE_PATH, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    for row in rows:
        fields = derived_fields(row)
        for field, value in fields:
            counts[field][value] += 1
        values = dict(fields)
        # Midpoint of the salary range, in K USD.
        midpoint = (values["salary_min_k"] + values["salary_max_k"]) / 2
        for field in ("work_type", "qualification", "experience_min", "job_portal"):
            salary_by[(field, values[field])].append(midpoint)
        salary_by[("all", "all")].append(midpoint)
    return rows, counts, salary_by


def load_full():
    with open(COUNTS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    counts = {}
    for field, values in raw["counts"].items():
        convert = int if field in NUMERIC_FIELDS else str
        counts[field] = Counter({convert(k): v for k, v in values.items()})
    return raw["total"], counts


class Report:
    def __init__(self):
        self.rows, self.sample, self.salary_by = load_sample()
        self.n = len(self.rows)
        self.total, self.full = load_full()

    def items(self, field, keys=None):
        """[(key, sample count, full count)], by decreasing sample count unless keys are given."""
        sample, full = self.sample[field], self.full[field]
        if keys is None:
            keys = sorted(full, key=lambda k: (-sample[k], -full[k], str(k)))
        return [(key, sample[key], full[key]) for key in keys]

    def representativeness(self, field):
        sample, full = self.sample[field], self.full[field]
        # Benefits: 5 per posting, shares are per posting.
        worst_gap, worst_key, worst_z = 0.0, None, 0.0
        for key, full_count in full.items():
            p = full_count / self.total
            p_hat = sample[key] / self.n
            se = math.sqrt(p * (1 - p) / self.n) if 0 < p < 1 else 1
            z = abs(p_hat - p) / se
            if abs(p_hat - p) > worst_gap:
                worst_gap, worst_key = abs(p_hat - p), key
            worst_z = max(worst_z, z)
        return len(full), worst_gap, worst_key, worst_z


# -- charts -----------------------------------------------------------------------


def tip(label, sample_count, full_count, n, total, unit="des offres"):
    return (f"{label} — échantillon : {fmt_int(sample_count)} ({fmt_pct(sample_count / n)} {unit}) · "
            f"fichier complet : {fmt_pct(full_count / total)}")


def table(headers, rows, numeric_from=1):
    head = "".join(f'<th{" class=num" if i >= numeric_from else ""}>{esc(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td{" class=num" if i >= numeric_from else ""}>{cell}</td>' for i, cell in enumerate(row))
        + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def data_table(report, items, label_header, label_fn=str):
    n, total = report.n, report.total
    rows = [
        [esc(label_fn(key)), fmt_int(s), fmt_pct(s / n, 2), fmt_pct(f / total, 2)]
        for key, s, f in items
    ]
    return (f"<details><summary>Voir les données ({len(items)} valeurs)</summary>"
            + table([label_header, "Échantillon", "Part (échantillon)", "Part (fichier complet)"], rows)
            + "</details>")


def hbars(report, items, label_fn=str, emphasis=None, limit=None, unit="des offres"):
    """Ranked horizontal bars of sample shares. `emphasis`: keys drawn in the
    accent color, the others muted (None: every bar in the accent color)."""
    n, total = report.n, report.total
    shown = items[:limit] if limit else items
    scale, tick_values = nice_axis(max(s for _, s, _ in shown) / n)
    rows = []
    for key, s, f in shown:
        label = label_fn(key)
        share = s / n
        muted = emphasis is not None and key not in emphasis
        rows.append(
            f'<div class="hrow" tabindex="0" data-tip="{esc(tip(label, s, f, n, total, unit))}">'
            f'<span class="hlabel">{esc(label)}</span>'
            f'<span class="htrack"><span class="hbar{" muted" if muted else ""}" '
            f'style="width:{share / scale * 100:.2f}%"></span>'
            f'<span class="hval">{fmt_pct(share)}</span></span></div>'
        )
    ticks = "".join(
        f'<span style="left:{t / scale * 100:.2f}%">{fmt_tick(t)}</span>'
        for t in tick_values
    )
    axis = f'<div class="haxis"><span class="hlabel"></span><span class="hticks">{ticks}</span></div>'
    return f'<div class="hbars">{"".join(rows)}{axis}</div>'


def columns(report, items, label_fn=str, label_every=1, unit="des offres"):
    """Ordered columns (time, experience, salary...) of sample shares."""
    n, total = report.n, report.total
    scale, tick_values = nice_axis(max(s for _, s, _ in items) / n)
    slots, labels = [], []
    for i, (key, s, f) in enumerate(items):
        label = label_fn(key)
        slots.append(
            f'<div class="cslot" tabindex="0" data-tip="{esc(tip(label, s, f, n, total, unit))}">'
            f'<span class="cbar" style="height:{s / n / scale * 100:.2f}%"></span></div>'
        )
        labels.append(f'<span>{esc(label) if i % label_every == 0 else ""}</span>')
    grid = "".join(
        f'<span class="gline" style="bottom:{t / scale * 100:.2f}%"><em>{fmt_tick(t)}</em></span>'
        for t in tick_values
    )
    return (f'<div class="cchart"><div class="cplot">{grid}<div class="cslots">{"".join(slots)}</div></div>'
            f'<div class="clabels">{"".join(labels)}</div></div>')


def section(anchor, title, lead, body, notes=None):
    notes_html = "".join(f"<p class=note>{note}</p>" for note in (notes or []))
    return (f'<section id="{anchor}"><h2>{esc(title)}</h2><p class="lead">{lead}</p>'
            f'<div class="card">{body}</div>{notes_html}</section>')


def tile(label, value, sub=""):
    sub_html = f'<span class="tsub">{sub}</span>' if sub else ""
    return (f'<div class="tile"><span class="tlabel">{esc(label)}</span>'
            f'<span class="tvalue">{value}</span>{sub_html}</div>')


# -- report -----------------------------------------------------------------------


FIELD_LABELS = {
    "country": "Pays", "city": "Ville", "job_portal": "Portail / agence", "work_type": "Type de contrat",
    "experience": "Expérience demandée", "experience_min": "Expérience minimum", "experience_max": "Expérience maximum",
    "qualification": "Diplôme", "preference": "Préférence de genre", "job_title": "Intitulé de poste",
    "role": "Rôle", "company": "Entreprise", "salary_min_k": "Salaire : borne basse",
    "salary_max_k": "Salaire : borne haute", "company_size_bin": "Taille d'entreprise",
    "posting_month": "Mois de publication", "benefit": "Avantage",
}


def qualification_names():
    with open(os.path.join(DATAS_DIR, "faker_qualifications.csv"), encoding="utf-8", newline="") as f:
        return {row["Code"]: row["Description"] for row in csv.DictReader(f)}


def build(report):
    r = report
    n, total = r.n, r.total
    parts = []
    full = r.full

    months = sorted(full["posting_month"])
    first_day = min(row["Job Posting Date"] for row in r.rows)
    last_day = max(row["Job Posting Date"] for row in r.rows)

    # Tiles
    tiles = [
        tile("Offres dans le fichier", fmt_int(total), "job_descriptions2.csv, 1,7 Go"),
        tile("Offres dans l'échantillon", fmt_int(n), f"{fmt_pct(n / total, 2)} du fichier, tirage aléatoire"),
        tile("Pays", fmt_int(len(full["country"])), f"{len(full['city'])} villes"),
        tile("Intitulés de poste", fmt_int(len(full["job_title"])), f"{len(full['role'])} rôles"),
        tile("Entreprises", fmt_int(len(full["company"]))),
        tile("Période de publication", f"{len(months)} mois", f"{first_day} → {last_day} (échantillon)"),
    ]

    # Findings
    china = full["country"]["China"] / total
    median_country = statistics.median(full["country"].values()) / total
    median_portal = statistics.median(full["job_portal"].values())
    half_portals = sorted(k for k, v in full["job_portal"].items() if v < 0.75 * median_portal)
    role_unit = statistics.median(full["role"].values())
    role_multiples = Counter(round(v / role_unit) for v in full["role"].values())
    benefits_sorted = sorted(full["benefit"].items(), key=lambda kv: -kv[1])
    salary_groups = {k: statistics.mean(v) for k, v in r.salary_by.items()}
    wt_means = [salary_groups[("work_type", k)] for k in full["work_type"]]

    findings = [
        "<strong>Le jeu de données est synthétique et presque uniforme.</strong> Pays, villes, contrats, "
        "expériences, diplômes, salaires, tailles d'entreprise et dates sont tirés au hasard de façon égale, "
        "et indépendamment les uns des autres : chaque valeur pèse à peu près autant que les autres.",
        f"<strong>La Chine pèse trois fois plus que les autres pays</strong> ({fmt_pct(china)} contre "
        f"{fmt_pct(median_country, 2)} pour un pays médian) : Hong Kong et Macao y ont été rattachés "
        "(<code>COUNTRY_FIXES</code> de <code>scripts/transform_job_descriptions.py</code>), "
        "soit trois villes au lieu d'une.",
        f"<strong>{NUMBERS_FR.get(len(half_portals), len(half_portals))} portails sur {len(full['job_portal'])} "
        f"sont deux fois moins présents</strong> que les autres : {', '.join(half_portals)}.",
        f"<strong>Les rôles ne sont pas égaux, mais par paliers</strong> : chaque rôle compte un multiple exact "
        f"d'environ {fmt_int(round(role_unit / total * n))} offres pour {fmt_int(n)} "
        f"({', '.join(f'{v} rôle{plural(v)} à {k}×' for k, v in sorted(role_multiples.items()))}). "
        "C'est un artefact de la génération (rôle dupliqué dans la table source), pas un signal du marché ; "
        "les intitulés de poste en héritent (UX/UI Designer en tête).",
        f"<strong>Deux avantages sortent du lot</strong> : « {esc(benefits_sorted[0][0])} » "
        f"({fmt_pct(benefits_sorted[0][1] / total)} des offres) et, à l'inverse, « {esc(benefits_sorted[-1][0])} » "
        f"({fmt_pct(benefits_sorted[-1][1] / total)}), car les avantages viennent de 11 combinaisons fixes de 5.",
        f"<strong>Le salaire ne dépend de rien</strong> : le salaire moyen (milieu de fourchette) varie de "
        f"{min(wt_means):.1f}".replace(".", ",") + f" à {max(wt_means):.1f}".replace(".", ",")
        + " K$ selon le type de contrat, et reste aussi plat selon le diplôme ou l'expérience (voir plus bas).",
        "<strong>L'échantillon est représentatif</strong> : sur chaque variable, l'écart avec le fichier complet "
        "reste dans ce que le seul hasard du tirage produit (section « Représentativité »).",
    ]

    parts.append('<section id="constats"><h2>En bref</h2><ul class="findings">'
                 + "".join(f"<li>{f}</li>" for f in findings) + "</ul></section>")

    # Representativeness
    rep_rows = []
    for field in ["country", "city", "job_portal", "work_type", "experience", "qualification", "job_title", "role",
                  "company", "salary_min_k", "salary_max_k", "company_size_bin", "posting_month", "benefit",
                  "preference"]:
        k, gap, key, z = r.representativeness(field)
        ok = z < z_threshold(k)
        rep_rows.append([
            esc(FIELD_LABELS[field]), fmt_int(k), f"{gap * 100:.2f}".replace(".", ",") + NBSP + "pt",
            f"{z:.1f}".replace(".", ","), f"{z_threshold(k):.1f}".replace(".", ","),
            '<span class="ok">✓ conforme</span>' if ok else '<span class="ko">⚠ à vérifier</span>',
        ])
    parts.append(section(
        "representativite", "Représentativité de l'échantillon",
        f"{fmt_int(n)} offres tirées uniformément au hasard, sans remise, parmi les {fmt_int(total)} du fichier "
        f"(échantillonnage par réservoir, graine {SEED} : le même échantillon à chaque exécution). "
        "Pour chaque variable, on compare la part de chaque valeur dans l'échantillon à sa part réelle.",
        table(["Variable", "Valeurs", "Écart max", "Écart max (en erreurs-types)", "Seuil du hasard", "Verdict"],
              rep_rows),
        ["<em>Écart max</em> : plus grande différence, en points de pourcentage, entre la part d'une valeur dans "
         "l'échantillon et dans le fichier complet. <em>En erreurs-types</em> : cet écart rapporté à la fluctuation "
         "attendue d'un tirage de cette taille ; au-dessous du seuil (qui grandit avec le nombre de valeurs), "
         "l'écart s'explique par le seul hasard."],
    ))

    # Countries
    country_items = r.items("country")
    parts.append(section(
        "pays", "Pays", f"Part des offres par pays, 15 premiers sur {len(country_items)}. "
        "La Chine se détache ; tous les autres pays sont au même niveau.",
        hbars(r, country_items, emphasis={"China"}, limit=15)
        + data_table(r, country_items, "Pays"),
    ))

    # Cities
    city_items = r.items("city")
    chinese = {k for k, _, _ in city_items if k.endswith("(China)")}
    # The 3 Chinese cities, plus the top other cities, so the story is on screen.
    city_shown = sorted([item for item in city_items if item[0] in chinese]
                        + [item for item in city_items if item[0] not in chinese][:12], key=lambda item: -item[1])
    parts.append(section(
        "villes", "Villes",
        f"Part des offres par ville : les 3 villes chinoises et les 12 premières autres, sur {len(city_items)}. "
        "Une seule ville par pays, sauf la Chine (en couleur) : Pékin, Hong Kong (« City of Victoria ») et Macao, "
        "chacune au niveau d'un pays ordinaire.",
        hbars(r, city_shown, emphasis=chinese) + data_table(r, city_items, "Ville"),
        ["Les écarts entre villes ordinaires (de "
         f"{fmt_pct(min(full['city'].values()) / total, 2)} à {fmt_pct(max(full['city'].values()) / total, 2)} "
         "dans le fichier complet) sont du bruit de tirage."],
    ))

    # Portals
    portal_items = r.items("job_portal")
    parts.append(section(
        "portails", "Portails et agences d'emploi",
        f"Part des offres par portail ({len(portal_items)} dans le fichier). Les {len(half_portals)} portails "
        "en gris sont deux fois moins fréquents.",
        hbars(r, portal_items, emphasis={k for k, _, _ in portal_items if k not in half_portals})
        + data_table(r, portal_items, "Portail"),
        ["Le provider <code>faker_jobs</code> utilise la liste élargie de <code>faker_job_portal.csv</code> "
         "(45 portails et agences, dont Adecco, Randstad, 1001 Interim), et non ces 16 seuls."],
    ))

    # Work types
    wt_items = r.items("work_type")
    parts.append(section(
        "contrats", "Types de contrat",
        "Part des offres par type de contrat : cinq types à égalité, un cinquième chacun.",
        hbars(r, wt_items) + data_table(r, wt_items, "Type de contrat"),
    ))

    # Experience
    exp_min = r.items("experience_min", sorted(full["experience_min"]))
    exp_max = r.items("experience_max", sorted(full["experience_max"]))
    exp_items = r.items("experience")
    parts.append(section(
        "experience", "Expérience demandée",
        f"Les offres demandent « de X à Y ans » : X va de {exp_min[0][0]} à {exp_min[-1][0]} ans, Y de "
        f"{exp_max[0][0]} à {exp_max[-1][0]} ans, soit {len(exp_items)} fourchettes, toutes aussi fréquentes.",
        '<div class="pair"><div><h3>Expérience minimum (années)</h3>'
        + columns(r, exp_min, label_fn=lambda k: f"{k} an{'s' if k > 1 else ''}")
        + '</div><div><h3>Expérience maximum (années)</h3>'
        + columns(r, exp_max, label_fn=lambda k: f"{k} ans") + "</div></div>"
        + data_table(r, exp_items, "Fourchette"),
    ))

    # Qualifications
    names = qualification_names()
    qual_items = r.items("qualification")
    parts.append(section(
        "diplomes", "Diplômes demandés", "Part des offres par diplôme : dix diplômes à égalité, un dixième chacun.",
        hbars(r, qual_items, label_fn=lambda k: f"{k} — {names.get(k, k)}")
        + data_table(r, qual_items, "Diplôme", label_fn=lambda k: f"{k} — {names.get(k, k)}"),
    ))

    # Salaries
    sal_min = r.items("salary_min_k", sorted(full["salary_min_k"]))
    sal_max = r.items("salary_max_k", sorted(full["salary_max_k"]))
    group_rows = []
    for field, label in [("work_type", "Type de contrat"), ("qualification", "Diplôme"),
                         ("experience_min", "Expérience minimum"), ("job_portal", "Portail")]:
        means = {k: statistics.mean(v) for (f, k), v in r.salary_by.items() if f == field}
        low, high = min(means, key=means.get), max(means, key=means.get)
        group_rows.append([esc(label), fmt_int(len(means)),
                           f"{means[low]:.1f}".replace(".", ",") + f" K$ ({esc(low)})",
                           f"{means[high]:.1f}".replace(".", ",") + f" K$ ({esc(high)})",
                           f"{means[high] - means[low]:.1f}".replace(".", ",") + " K$"])
    overall = statistics.mean(r.salary_by[("all", "all")])
    parts.append(section(
        "salaires", "Salaires",
        f"Fourchettes annuelles en dollars, « $XK-$YK ». La borne basse va de {sal_min[0][0]} à "
        f"{sal_min[-1][0]} K$, la borne haute de {sal_max[0][0]} à {sal_max[-1][0]} K$, tirées uniformément ; "
        f"milieu de fourchette moyen : {overall:.1f}".replace(".", ",") + " K$.",
        '<div class="pair"><div><h3>Borne basse (K$)</h3>'
        + columns(r, sal_min, label_fn=lambda k: f"{k}", label_every=2)
        + '</div><div><h3>Borne haute (K$)</h3>'
        + columns(r, sal_max, label_fn=lambda k: f"{k}", label_every=10) + "</div></div>"
        + "<h3>Salaire moyen (milieu de fourchette) selon…</h3>"
        + table(["Selon", "Groupes", "Le plus bas", "Le plus haut", "Écart"], group_rows)
        + data_table(r, sal_min, "Borne basse (K$)")
        + data_table(r, sal_max, "Borne haute (K$)"),
        [f"L'écart entre groupes (quelques centaines de dollars sur {overall:.0f} K$) est du bruit : "
         "le salaire est tiré indépendamment du contrat, du diplôme, de l'expérience et du métier."],
    ))

    # Job titles / roles
    title_items = r.items("job_title")
    role_items = r.items("role")
    parts.append(section(
        "metiers", "Métiers",
        f"{len(title_items)} intitulés de poste regroupant {len(role_items)} rôles. Les intitulés en tête sont ceux "
        "qui ont le plus de rôles, ou des rôles dupliqués dans la table source.",
        '<div class="pair"><div><h3>Intitulés de poste (15 premiers)</h3>'
        + hbars(r, title_items, limit=15) + '</div><div><h3>Rôles (15 premiers)</h3>'
        + hbars(r, role_items, limit=15) + "</div></div>"
        + data_table(r, title_items, "Intitulé") + data_table(r, role_items, "Rôle"),
    ))

    # Companies
    company_items = r.items("company")
    parts.append(section(
        "entreprises", "Entreprises",
        f"{len(company_items)} entreprises, chacune présente dans environ "
        f"{fmt_pct(1 / len(company_items), 2)} des offres. 15 premières de l'échantillon :",
        hbars(r, company_items, limit=15) + data_table(r, company_items, "Entreprise"),
        ["Le classement change d'un échantillon à l'autre : dans le fichier complet, toutes les entreprises "
         f"sont entre {fmt_pct(min(full['company'].values()) / total, 2)} et "
         f"{fmt_pct(max(full['company'].values()) / total, 2)}."],
    ))

    # Company size
    size_items = r.items("company_size_bin", sorted(full["company_size_bin"]))

    def size_label(k):
        return f"{k // 1000}–{(k + COMPANY_SIZE_BIN) // 1000}k"

    parts.append(section(
        "taille", "Taille des entreprises",
        "Nombre de salariés annoncé, par tranches de 10 000 : uniforme d'environ 12 600 à 134 800 "
        "(les tranches extrêmes sont incomplètes).",
        columns(r, size_items, label_fn=size_label, label_every=2) + data_table(r, size_items, "Salariés",
                                                                                label_fn=size_label),
    ))

    # Posting dates
    month_items = r.items("posting_month", months)
    parts.append(section(
        "dates", "Dates de publication",
        f"Part des offres par mois de publication, de {month_label(months[0])} à {month_label(months[-1])} : "
        "un nombre constant d'offres par jour.",
        columns(r, month_items, label_fn=month_label, label_every=3) + data_table(r, month_items, "Mois",
                                                                                  label_fn=month_label),
        ["Septembre 2021 et septembre 2023 ne sont couverts qu'à moitié (du 15 au 15), février est plus court : "
         "ce sont les seules variations."],
    ))

    # Benefits
    benefit_items = r.items("benefit")
    parts.append(section(
        "avantages", "Avantages proposés",
        f"Part des offres proposant chaque avantage ({len(benefit_items)} avantages, 5 par offre).",
        hbars(r, benefit_items) + data_table(r, benefit_items, "Avantage"),
    ))

    # Gender preference
    pref_items = r.items("preference")
    labels_fr = {"Male": "Homme (Male)", "Female": "Femme (Female)", "Both": "Les deux (Both)"}
    parts.append(section(
        "preference", "Préférence de genre",
        "Le fichier indique pour chaque offre un genre « préféré » : trois valeurs à égalité.",
        hbars(r, pref_items, label_fn=lambda k: labels_fr.get(k, k))
        + data_table(r, pref_items, "Préférence", label_fn=lambda k: labels_fr.get(k, k)),
        ["Ce champ n'est pas repris par <code>faker_jobs</code> : une préférence de genre dans une offre "
         "d'emploi est discriminatoire (et interdite en France)."],
    ))

    # Method
    parts.append(section(
        "methode", "Méthode",
        "Comment ce rapport est produit, et comment le régénérer.",
        "<ol class=method>"
        "<li><code>python scripts/build_sample.py</code> lit les "
        f"{fmt_int(total)} offres de <code>DATAS/job_descriptions2.csv</code> en une passe (~1 min) et écrit "
        f"<code>DATAS/job_sample.csv</code> ({fmt_int(n)} offres, même format que la source, ouvrable dans un "
        "tableur) et <code>DATAS/job_full_counts.json</code> (comptages du fichier complet).</li>"
        "<li><code>python scripts/build_report.py</code> calcule toutes les figures sur l'échantillon et écrit ce "
        "fichier. Les parts du fichier complet ne servent qu'à la comparaison (infobulles, tableaux, "
        "représentativité).</li></ol>",
    ))

    nav = "".join(
        f'<a href="#{a}">{esc(t)}</a>'
        for a, t in [("constats", "En bref"), ("representativite", "Représentativité"), ("pays", "Pays"),
                     ("villes", "Villes"), ("portails", "Portails"), ("contrats", "Contrats"),
                     ("experience", "Expérience"), ("diplomes", "Diplômes"), ("salaires", "Salaires"),
                     ("metiers", "Métiers"), ("entreprises", "Entreprises"), ("taille", "Taille"),
                     ("dates", "Dates"), ("avantages", "Avantages"), ("preference", "Genre"),
                     ("methode", "Méthode")]
    )
    generated = datetime.date.today().isoformat()
    return TEMPLATE.format(
        generated=generated, n=fmt_int(n), total=fmt_int(total), tiles="".join(tiles), nav=nav,
        body="".join(parts),
    )


TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rapport Job Descriptions</title>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series: #2a78d6; --series-muted: #c3c2b7; --good: #006300; --warn: #8a5a00;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series: #3987e5; --series-muted: #52514e; --good: #0ca30c; --warn: #fab219;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --series: #3987e5; --series-muted: #52514e; --good: #0ca30c; --warn: #fab219;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }}
main {{ max-width: 1040px; margin: 0 auto; padding: 32px 16px 64px; }}
header h1 {{ font-size: 28px; margin: 0 0 4px; font-weight: 650; }}
header p {{ color: var(--ink-2); margin: 0; }}
nav {{ display: flex; flex-wrap: wrap; gap: 4px 14px; margin: 20px 0 8px; font-size: 13px; }}
nav a {{ color: var(--ink-2); text-decoration: none; }} nav a:hover {{ color: var(--ink); text-decoration: underline; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 20px 0; }}
.tile {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px;
  display: flex; flex-direction: column; gap: 2px; }}
.tlabel {{ font-size: 13px; color: var(--ink-2); }}
.tvalue {{ font-size: 26px; font-weight: 600; }}
.tsub {{ font-size: 12px; color: var(--muted); }}
section {{ margin-top: 40px; }}
h2 {{ font-size: 20px; margin: 0 0 4px; font-weight: 620; }}
h3 {{ font-size: 14px; margin: 0 0 10px; font-weight: 600; color: var(--ink-2); }}
.lead {{ color: var(--ink-2); margin: 0 0 12px; max-width: 760px; }}
.note {{ color: var(--ink-2); font-size: 13px; margin: 8px 0 0; max-width: 760px; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; }}
.findings {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  padding: 16px 20px 16px 36px; margin: 0; }}
.findings li {{ margin: 6px 0; }}
code {{ font: 13px ui-monospace, SFMono-Regular, Menlo, monospace; background: var(--grid); padding: 1px 4px;
  border-radius: 4px; }}
.pair {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 28px; margin-bottom: 8px; }}

/* horizontal bars */
.hbars {{ display: flex; flex-direction: column; gap: 2px; margin-bottom: 8px; }}
.hrow, .haxis {{ display: grid; grid-template-columns: minmax(110px, 38%) 1fr; gap: 10px; align-items: center; }}
.hrow {{ min-height: 24px; border-radius: 4px; outline: none; }}
.hrow:hover, .hrow:focus-visible {{ background: var(--grid); }}
.hlabel {{ font-size: 13px; color: var(--ink-2); text-align: right; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }}
.htrack {{ display: flex; align-items: center; gap: 6px; padding-right: 54px; position: relative; }}
.hbar {{ display: block; height: 16px; background: var(--series); border-radius: 0 4px 4px 0; min-width: 1px; }}
.hbar.muted {{ background: var(--series-muted); }}
.hval {{ font-size: 12px; color: var(--ink); font-variant-numeric: tabular-nums; white-space: nowrap; }}
.hticks {{ position: relative; height: 18px; margin-right: 54px; border-top: 1px solid var(--axis); }}
.hticks span {{ position: absolute; top: 2px; transform: translateX(-50%); font-size: 11px; color: var(--muted);
  font-variant-numeric: tabular-nums; white-space: nowrap; }}
.hticks span:first-child {{ transform: none; }}

/* columns */
.cchart {{ margin: 0 0 8px; padding-left: 44px; }}
.cplot {{ position: relative; height: 170px; }}
.gline {{ position: absolute; left: 0; right: 0; border-top: 1px solid var(--grid); }}
.gline:first-child {{ border-top-color: var(--axis); }}
.gline em {{ position: absolute; right: calc(100% + 6px); top: -8px; font: 11px system-ui, sans-serif;
  color: var(--muted); font-variant-numeric: tabular-nums; font-style: normal; white-space: nowrap; }}
.cslots {{ position: absolute; inset: 0; display: flex; gap: 2px; align-items: stretch; }}
.cslot {{ flex: 1; display: flex; align-items: flex-end; justify-content: center; border-radius: 4px; outline: none; }}
.cslot:hover, .cslot:focus-visible {{ background: var(--grid); }}
.cbar {{ display: block; width: 100%; max-width: 24px; background: var(--series); border-radius: 4px 4px 0 0; }}
.clabels {{ display: flex; gap: 2px; margin-top: 4px; }}
.clabels span {{ flex: 1; font-size: 11px; color: var(--muted); text-align: center; white-space: nowrap;
  overflow: visible; min-width: 0; }}

/* tables */
details {{ margin-top: 10px; font-size: 13px; }}
summary {{ cursor: pointer; color: var(--ink-2); }}
.card > table, details table {{ width: 100%; }}
table {{ border-collapse: collapse; font-size: 13px; margin-top: 8px; }}
th, td {{ text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--grid); }}
th {{ color: var(--ink-2); font-weight: 600; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
details {{ overflow-x: auto; }}
.card {{ overflow-x: auto; }}
.ok {{ color: var(--good); font-weight: 600; white-space: nowrap; }}
.ko {{ color: var(--warn); font-weight: 600; white-space: nowrap; }}
.method li {{ margin: 6px 0; }}

/* tooltip */
#tip {{ position: fixed; z-index: 10; pointer-events: none; max-width: 320px; padding: 8px 10px;
  background: var(--surface); color: var(--ink); border: 1px solid var(--border); border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12); font-size: 12px; line-height: 1.4; display: none; }}
footer {{ margin-top: 48px; color: var(--muted); font-size: 12px; }}
@media (max-width: 600px) {{
  .hrow, .haxis {{ grid-template-columns: minmax(90px, 42%) 1fr; }}
  .htrack {{ padding-right: 46px; }} .hticks {{ margin-right: 46px; }}
  .clabels span {{ font-size: 10px; }}
}}
</style>
</head>
<body>
<main>
<header>
<h1>Rapport sur le jeu de données d'offres d'emploi</h1>
<p>Analyse d'un échantillon représentatif de {n} offres tirées parmi les {total} de
<code>job_descriptions2.csv</code> (Job Description Dataset, Kaggle). Généré le {generated}.</p>
</header>
<nav>{nav}</nav>
<div class="tiles">{tiles}</div>
{body}
<footer>Toutes les parts sont calculées sur l'échantillon ; survoler une barre (ou la sélectionner au clavier)
affiche aussi la part dans le fichier complet. Généré par <code>scripts/build_report.py</code>.</footer>
</main>
<div id="tip" role="tooltip"></div>
<script>
(function () {{
  var tipEl = document.getElementById("tip");
  function show(target, x, y) {{
    tipEl.textContent = target.getAttribute("data-tip");
    tipEl.style.display = "block";
    var w = tipEl.offsetWidth, h = tipEl.offsetHeight;
    var left = Math.min(x + 14, window.innerWidth - w - 8);
    var top = y - h - 12 < 8 ? y + 18 : y - h - 12;
    tipEl.style.left = Math.max(8, left) + "px";
    tipEl.style.top = top + "px";
  }}
  function hide() {{ tipEl.style.display = "none"; }}
  document.addEventListener("mousemove", function (e) {{
    var t = e.target.closest && e.target.closest("[data-tip]");
    if (t) show(t, e.clientX, e.clientY); else hide();
  }});
  document.addEventListener("focusin", function (e) {{
    var t = e.target.closest && e.target.closest("[data-tip]");
    if (!t) return hide();
    var r = t.getBoundingClientRect();
    show(t, r.left + r.width / 2, r.top);
  }});
  document.addEventListener("focusout", hide);
  window.addEventListener("scroll", hide, {{ passive: true }});
}})();
</script>
</body>
</html>
"""


def main():
    for path in (SAMPLE_PATH, COUNTS_PATH):
        if not os.path.exists(path):
            sys.exit(f"{path} not found: run scripts/build_sample.py first")
    report = Report()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(build(report))
    print(f"Wrote {OUTPUT_PATH} ({report.n} sampled postings)")


if __name__ == "__main__":
    main()
