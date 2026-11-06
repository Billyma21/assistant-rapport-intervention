# -*- coding: utf-8 -*-
"""Rendu HTML. Pas de moteur de template externe, uniquement des f-strings."""

import html
import json
from datetime import date
from urllib.parse import quote

CSS = """
:root{--bg:#F1F4F7;--card:#FFF;--ink:#14212C;--soft:#5A6B79;--line:#D3DCE4;
--accent:#0E7C86;--amber:#C8791B;--ok:#2C8A62;--warn:#C8791B;--crit:#C0392F;
--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 "Segoe UI",system-ui,-apple-system,sans-serif}
a{color:var(--accent);text-decoration:none}
header.top{background:#14212C;color:#DCE5EC;padding:0 20px;display:flex;
align-items:center;gap:22px;flex-wrap:wrap;min-height:54px}
header.top b{font-size:16px;letter-spacing:.2px}
header.top nav{display:flex;gap:18px;flex-wrap:wrap}
header.top nav a{color:#B9C8D4;padding:16px 2px;display:inline-block;font-size:14px}
header.top nav a:hover,header.top nav a.on{color:#fff;box-shadow:inset 0 -3px 0 var(--amber)}
.wrap{max-width:1040px;margin:0 auto;padding:26px 18px 60px}
.wrap.dash{max-width:1240px;padding:14px 18px 12px;height:calc(100vh - 54px);
overflow:hidden;display:flex;flex-direction:column;gap:10px}
h1{font-size:23px;margin:0 0 4px}
h2{font-size:17px;margin:28px 0 10px}
.dash h1{font-size:18px;margin:0}
.dash h2{font-size:14px;margin:0 0 6px;text-transform:uppercase;letter-spacing:.04em;
color:var(--soft)}
.lede{color:var(--soft);margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:9px;
padding:20px;margin-bottom:18px}
.dash .card{padding:12px 14px;margin:0;flex:1;min-height:0;overflow:hidden}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.g4{grid-template-columns:repeat(4,1fr);gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:16px}
.dash .kpi{padding:10px 12px}
.kpi .v{font-size:27px;font-weight:700;font-family:var(--mono)}
.dash .kpi .v{font-size:22px}
.kpi .l{color:var(--soft);font-size:12.5px;text-transform:uppercase;letter-spacing:.06em}
.dash-main{display:grid;grid-template-columns:1.1fr 1fr;gap:10px;flex:1;min-height:0}
.dash-bas{flex:0 0 auto}
label{display:block;font-size:13px;color:var(--soft);margin:12px 0 4px;font-weight:600}
input,select,textarea{width:100%;padding:9px 11px;border:1px solid var(--line);
border-radius:6px;font:inherit;background:#fff;color:var(--ink)}
textarea{min-height:170px;font-family:var(--mono);font-size:13.5px;line-height:1.55}
button,.btn{background:var(--accent);color:#fff;border:0;border-radius:6px;
padding:11px 20px;font:inherit;font-weight:600;cursor:pointer;display:inline-block}
.btn.sec{background:#fff;color:var(--ink);border:1px solid var(--line)}
button:hover{filter:brightness(1.08)}
table{width:100%;border-collapse:collapse;font-size:14px}
.dash table{font-size:12.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
.dash th,.dash td{padding:5px 6px}
th{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--soft)}
.pill{display:inline-block;padding:2px 10px;border-radius:11px;font-size:12px;
font-weight:700;color:#fff}
.p-critique{background:var(--crit)}.p-vigilance{background:var(--warn)}
.p-info{background:var(--ok)}
.tag{display:inline-block;border:1px solid var(--line);border-radius:4px;
padding:2px 8px;font-family:var(--mono);font-size:12px;color:var(--soft);
background:#F7F9FB;margin:0 5px 5px 0}
.motifs{margin:0;padding-left:20px}
.motifs li{margin:5px 0}
.bandeau{border-radius:8px;padding:14px 18px;color:#fff;margin-bottom:18px}
.b-critique{background:var(--crit)}.b-vigilance{background:var(--warn)}
.b-info{background:var(--ok)}
.mono{font-family:var(--mono)}
pre{background:#14212C;color:#DCE5EC;padding:14px;border-radius:7px;
overflow-x:auto;font-size:13px;line-height:1.5}
.muted{color:var(--soft);font-size:13.5px}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.score{font-family:var(--mono);font-weight:700}
.score.haut{color:var(--crit)}.score.moyen{color:var(--warn)}.score.bas{color:var(--ok)}
svg.courbe{width:100%;height:auto;display:block;background:#FAFCFE;border-radius:6px}
@media (max-width:1100px){
  .wrap.dash{height:auto;overflow:auto}
  .dash-main{grid-template-columns:1fr}
  .g4{grid-template-columns:repeat(2,1fr)}
}
.impression-seulement{display:none}
.signatures{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:36px}
.signatures .case{border:1px solid #14212C;min-height:110px;padding:12px}
.signatures .case .titre{font-size:12px;text-transform:uppercase;letter-spacing:.06em;
color:var(--soft);margin-bottom:8px}
.pied-impression{margin-top:28px;padding-top:10px;border-top:1px solid var(--line);
font-size:12px;color:var(--soft)}
.ecart{background:#FFF4E5;outline:2px solid var(--amber)}
.comparaison{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.comparaison table{font-size:13px}
.comparaison th{width:38%}
@media print{
  header.top,.noprint{display:none!important}
  body{background:#fff!important;color:#000!important}
  a{color:#000!important;text-decoration:none}
  .wrap{max-width:none;padding:0;margin:0}
  .card{border:0;padding:0;margin:0 0 12px;background:#fff}
  .pill{background:transparent!important;color:#000!important;border:1px solid #000}
  .muted{color:#333!important}
  .impression-seulement{display:block!important}
  .signatures .case{border-color:#000}
  .pied-impression{color:#000;border-top-color:#000;
    position:fixed;bottom:0;left:0;right:0;padding:8px 0;background:#fff}
}
"""


def e(valeur):
    return html.escape(str(valeur)) if valeur not in (None, "") else ""


def page(titre, contenu, onglet="", wrap_class=""):
    liens = [("/", "Tableau de bord"), ("/nouveau", "Nouveau rapport"),
             ("/rapports", "Rapports"), ("/alertes", "Alertes"),
             ("/sites", "Sites"), ("/config", "Seuils")]
    nav = "".join(
        '<a href="%s" class="%s">%s</a>' % (url, "on" if url == onglet else "", nom)
        for url, nom in liens)
    classe = ("wrap " + wrap_class).strip()
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}</title><style>{CSS}</style></head><body>
<header class="top"><b>Assistant de rapport d'intervention</b><nav>{nav}</nav></header>
<div class="{classe}">{contenu}</div></body></html>"""


def pill(niveau):
    libelle = {"critique": "Critique", "vigilance": "Vigilance", "info": "Conforme"}
    return '<span class="pill p-%s">%s</span>' % (e(niveau), libelle.get(niveau, niveau))


def lien_circuit(circuit):
    if not circuit:
        return "—"
    return '<a href="/circuit/%s">%s</a>' % (quote(str(circuit), safe=""), e(circuit))


def lien_site(site):
    if not site:
        return "—"
    return '<a href="/site/%s">%s</a>' % (quote(str(site), safe=""), e(site))


def classe_score(score):
    if score >= 60:
        return "haut"
    if score >= 30:
        return "moyen"
    return "bas"


def courbe_isolement_svg(releves, seuil=None, largeur=560, hauteur=220):
    """Courbe d'isolement en SVG ecrite a la main (sans dependance).

    releves : [(date, valeur_mohm, niveau_optionnel), ...] chronologique.
    """
    if not releves:
        return ('<p class="muted">Pas assez de relevés d\'isolement pour tracer '
                'une courbe.</p>')

    valeurs = [float(v) for _, v, *_ in releves if v is not None]
    if not valeurs:
        return '<p class="muted">Aucune valeur d\'isolement exploitable.</p>'

    pad_g, pad_d, pad_h, pad_b = 44, 16, 16, 36
    xmin, xmax = pad_g, largeur - pad_d
    ymin, ymax = pad_h, hauteur - pad_b

    y_vals = list(valeurs)
    if seuil is not None:
        y_vals.append(float(seuil))
    y_min = min(y_vals) * 0.85
    y_max = max(y_vals) * 1.1
    if y_max <= y_min:
        y_max = y_min + 10

    n = len(releves)

    def x_at(i):
        if n == 1:
            return (xmin + xmax) / 2
        return xmin + (xmax - xmin) * i / (n - 1)

    def y_at(v):
        return ymax - (float(v) - y_min) / (y_max - y_min) * (ymax - ymin)

    # Grille et axes
    parts = [
        '<svg class="courbe" viewBox="0 0 %d %d" role="img" '
        'aria-label="Courbe d\'isolement">' % (largeur, hauteur),
        '<rect x="0" y="0" width="%d" height="%d" fill="#FAFCFE"/>' % (largeur, hauteur),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#D3DCE4" stroke-width="1"/>'
        % (xmin, ymax, xmax, ymax),
        '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#D3DCE4" stroke-width="1"/>'
        % (xmin, ymin, xmin, ymax),
    ]

    # Labels Y
    for frac in (0.0, 0.5, 1.0):
        val = y_min + (y_max - y_min) * frac
        y = y_at(val)
        parts.append(
            '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#E8EEF3" '
            'stroke-width="1"/>' % (xmin, y, xmax, y))
        parts.append(
            '<text x="%d" y="%.1f" fill="#5A6B79" font-size="11" '
            'text-anchor="end" dominant-baseline="middle">%.0f</text>'
            % (xmin - 6, y, val))

    if seuil is not None:
        ys = y_at(seuil)
        parts.append(
            '<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#C0392F" '
            'stroke-width="1.5" stroke-dasharray="5 4"/>' % (xmin, ys, xmax, ys))
        parts.append(
            '<text x="%d" y="%.1f" fill="#C0392F" font-size="11">seuil %.0f</text>'
            % (xmin + 4, ys - 4, seuil))

    # Ligne
    coords = []
    for i, item in enumerate(releves):
        v = item[1]
        if v is None:
            continue
        coords.append("%.1f,%.1f" % (x_at(i), y_at(v)))
    if len(coords) >= 2:
        parts.append(
            '<polyline fill="none" stroke="#0E7C86" stroke-width="2" points="%s"/>'
            % " ".join(coords))

    couleurs = {"critique": "#C0392F", "vigilance": "#C8791B", "info": "#2C8A62"}
    for i, item in enumerate(releves):
        d, v = item[0], item[1]
        niveau = item[2] if len(item) > 2 else "info"
        if v is None:
            continue
        cx, cy = x_at(i), y_at(v)
        dernier = i == n - 1
        coul = couleurs.get(niveau or "info", "#0E7C86")
        r = 5 if dernier else 3.5
        parts.append(
            '<circle cx="%.1f" cy="%.1f" r="%s" fill="%s" stroke="#fff" '
            'stroke-width="1.5"/>' % (cx, cy, r, coul if dernier else "#0E7C86"))
        label = str(d)[5:] if d else ""  # MM-JJ
        parts.append(
            '<text x="%.1f" y="%d" fill="#5A6B79" font-size="10" '
            'text-anchor="middle">%s</text>' % (cx, hauteur - 10, e(label)))

    parts.append(
        '<text x="%d" y="14" fill="#5A6B79" font-size="11">Isolement (MΩ)</text>'
        % (xmin + 4))
    parts.append("</svg>")
    return "".join(parts)


# --------------------------------------------------------------------------

def accueil(kpis, priorites, courbe_html, derniers):
    """Tableau de bord compact (vise 1280 x 800 sans defilement)."""
    cartes = "".join(
        '<div class="kpi"><div class="v">%s</div><div class="l">%s</div></div>'
        % (e(v), e(l)) for v, l in kpis)

    lignes_prio = "".join(
        '<tr><td class="mono"><a href="/circuit/%s">%s</a></td>'
        '<td><span class="score %s">%d</span></td>'
        '<td>%s</td><td class="muted">%s</td></tr>' % (
            quote(str(p["circuit"]), safe=""), e(p["circuit"]),
            classe_score(p["score"]), p["score"],
            e(p.get("site") or ""),
            e(p["motif_dominant"]),
        ) for p in priorites
    ) or '<tr><td colspan="4" class="muted">Aucun circuit à prioriser.</td></tr>'

    lignes_der = "".join(
        '<tr><td class="mono">%s</td><td>%s</td><td>%s</td>'
        '<td>%s</td><td>%s</td>'
        '<td><a href="/rapport/%s">ouvrir</a></td></tr>' % (
            e(r["reference"]), e(r["date"]), e(r["site"]),
            lien_circuit(r["circuit"]), pill(r["niveau"]), r["id"],
        ) for r in derniers
    ) or '<tr><td colspan="6" class="muted">Aucun rapport.</td></tr>'

    return page("Tableau de bord", f"""
<div class="row" style="justify-content:space-between;align-items:baseline">
  <h1>Tableau de bord</h1>
  <a class="btn" href="/nouveau" style="padding:8px 14px;font-size:13px">Nouveau rapport</a>
</div>
<div class="grid g4">{cartes}</div>
<div class="dash-main">
  <div class="card">
    <h2>À traiter en priorité</h2>
    <table><tr><th>Circuit</th><th>Score</th><th>Site</th><th>Motif dominant</th></tr>
    {lignes_prio}</table>
  </div>
  <div class="card">
    <h2>Isolement — circuit le plus dégradé</h2>
    {courbe_html}
  </div>
</div>
<div class="card dash-bas">
  <h2>Cinq derniers rapports</h2>
  <table><tr><th>Réf.</th><th>Date</th><th>Site</th><th>Circuit</th>
  <th>Niveau</th><th></th></tr>{lignes_der}</table>
</div>""", "/", wrap_class="dash")


def formulaire(exemples, erreur=""):
    options = "".join('<option value="%s">%s</option>' % (e(nom), e(nom)) for nom in exemples)
    bandeau = f'<div class="bandeau b-critique">{e(erreur)}</div>' if erreur else ""
    return page("Nouveau rapport", f"""
<h1>Nouveau rapport</h1>
<p class="lede">Collez la note du technicien telle qu'elle a été écrite sur site.
L'analyse en extrait les valeurs et les range dans les rubriques du rapport.</p>
{bandeau}
<form method="post" action="/analyser" class="card">
  <div class="grid g2">
    <div><label for="site">Site</label>
      <input id="site" name="site" required placeholder="Bruxelles" value="Bruxelles"></div>
    <div><label for="circuit">Circuit</label>
      <input id="circuit" name="circuit" placeholder="CIR-0003" value="CIR-0003"></div>
    <div><label for="technicien">Technicien</label>
      <input id="technicien" name="technicien" placeholder="Equipe terrain"></div>
    <div><label for="date">Date</label>
      <input id="date" name="date" type="date"></div>
  </div>
  <label for="note">Note de terrain</label>
  <textarea id="note" name="note" required placeholder="Intervention de nuit de 22h à 02h, circuit consigné, habilitation B2V. Mesure d'isolement : 38 MOhm. Courant relevé 6,52 A. Sept feux hors service sur le TDZ. Baisse d'isolement constatée depuis deux campagnes. Optiques à commander pour la prochaine visite."></textarea>
  <div class="row" style="margin-top:16px">
    <button type="submit">Analyser la note</button>
    <span class="muted">ou charger un exemple :</span>
    <select name="exemple" onchange="if(this.value) location.href='/nouveau?exemple='+encodeURIComponent(this.value)">
      <option value="">—</option>{options}</select>
  </div>
</form>""", "/nouveau")


def _champ(libelle, nom, valeur, extra=""):
    return f"""<div><label for="{nom}">{libelle}</label>
<input id="{nom}" name="{nom}" value="{e(valeur)}" {extra}></div>"""


def _champs_caches_contexte(contexte, donnees, verdict):
    return f"""
  <input type="hidden" name="note" value="{e(contexte['note'])}">
  <input type="hidden" name="note_brute" value="{e(contexte['note'])}">
  <input type="hidden" name="moteur" value="{e(donnees.get('moteur'))}">
  <input type="hidden" name="niveau" value="{e(verdict['niveau'])}">
  <input type="hidden" name="motifs" value="{e(json.dumps(verdict['motifs'], ensure_ascii=False))}">
  <input type="hidden" name="site" value="{e(contexte['site'])}">
  <input type="hidden" name="circuit" value="{e(contexte['circuit'])}">
  <input type="hidden" name="technicien" value="{e(contexte['technicien'])}">
  <input type="hidden" name="date" value="{e(contexte['date'])}">
"""


def _formulaire_validation(donnees, verdict, contexte):
    return f"""
<form method="post" action="/valider" class="card">
  <input type="hidden" name="note_brute" value="{e(contexte['note'])}">
  <input type="hidden" name="moteur" value="{e(donnees.get('moteur'))}">
  <input type="hidden" name="niveau" value="{e(verdict['niveau'])}">
  <input type="hidden" name="motifs" value="{e(json.dumps(verdict['motifs'], ensure_ascii=False))}">
  <h2 style="margin-top:0">Identification</h2>
  <div class="grid g2">
    {_champ("Site", "site", contexte["site"])}
    {_champ("Circuit", "circuit", contexte["circuit"])}
    {_champ("Technicien", "technicien", contexte["technicien"])}
    {_champ("Date", "date", contexte["date"], 'type="date"')}
    {_champ("Système", "systeme", donnees.get("systeme"))}
    {_champ("Nature", "nature", donnees.get("nature"))}
    {_champ("Contrôle", "controle", donnees.get("controle"))}
    {_champ("Habilitation", "habilitation", donnees.get("habilitation"))}
  </div>
  <h2>Valeurs relevées</h2>
  <div class="grid g2">
    {_champ("Courant mesuré (A)", "courant_a", donnees.get("courant_a"))}
    {_champ("Isolement (MΩ)", "isolement_mohm", donnees.get("isolement_mohm"))}
    {_champ("Feux hors service", "feux_hs", donnees.get("feux_hs"))}
    {_champ("Durée (h)", "duree_h", donnees.get("duree_h"))}
  </div>
  <h2>Rapport</h2>
  <label for="travaux">Travaux réalisés</label>
  <textarea id="travaux" name="travaux" style="min-height:90px">{e(donnees.get("travaux"))}</textarea>
  <label for="constat">Constat et anomalies</label>
  <textarea id="constat" name="constat" style="min-height:70px">{e(donnees.get("constat"))}</textarea>
  <label for="suite">Suite à donner</label>
  <textarea id="suite" name="suite" style="min-height:70px">{e(donnees.get("suite"))}</textarea>
  <div class="row" style="margin-top:18px">
    <button type="submit">Valider et enregistrer</button>
    <a class="btn sec" href="/nouveau">Recommencer</a>
  </div>
</form>"""


def analyse(donnees, verdict, contexte, notifie, llm_disponible=False):
    motifs = "".join("<li>%s</li>" % e(m) for m in verdict["motifs"])
    bandeau = f"""<div class="bandeau b-{e(verdict['niveau'])}">
<strong>{ {'critique':'Alerte critique','vigilance':'Point de vigilance','info':'Aucun écart détecté'}[verdict['niveau']] }</strong>
 — {'une notification sera envoyée à la validation' if notifie else 'pas de notification à ce niveau'}.
</div>"""
    etiquettes = "".join('<span class="tag">%s</span>' % e(t) for t in [
        "moteur : " + (donnees.get("moteur") or "regles"),
        "nuit" if donnees.get("travail_de_nuit") else "jour",
        "consigné" if donnees.get("consignation") else "consignation non mentionnée",
        "correctives 12 mois : %d" % contexte["correctives"],
    ])
    bouton_llm = ""
    if llm_disponible:
        bouton_llm = f"""
<form method="post" action="/comparer" class="noprint" style="display:inline">
  {_champs_caches_contexte(contexte, donnees, verdict)}
  <button type="submit" class="btn sec">Comparer avec l'extraction distante</button>
</form>"""
    return page("Analyse", f"""
<h1>Analyse de la note</h1>
<p class="lede">Vérifiez, corrigez si nécessaire, puis validez. Rien n'est
enregistré tant que vous n'avez pas validé. Le verdict vient toujours du
moteur de règles.</p>
{bandeau}
<div class="card"><h2 style="margin-top:0">Pourquoi ce niveau</h2>
<ul class="motifs">{motifs}</ul><div style="margin-top:12px">{etiquettes}</div>
<div class="row" style="margin-top:14px">{bouton_llm}</div></div>
{_formulaire_validation(donnees, verdict, contexte)}""", "/nouveau")


def _tableau_extraction(donnees, ecarts_champs, titre):
    """Tableau d'une extraction ; surligne les champs en ecart."""
    lignes = []
    for cle in (
        "nature", "systeme", "controle", "courant_a", "isolement_mohm",
        "feux_hs", "duree_h", "travail_de_nuit", "consignation", "habilitation",
        "travaux", "constat", "suite",
    ):
        css = ' class="ecart"' if cle in ecarts_champs else ""
        val = donnees.get(cle) if donnees else "—"
        if isinstance(val, bool):
            val = "oui" if val else "non"
        elif val is None:
            val = "—"
        lignes.append("<tr%s><th>%s</th><td>%s</td></tr>" % (css, e(cle), e(val)))
    return (
        '<div class="card" style="margin:0"><h2 style="margin-top:0">%s</h2>'
        '<table>%s</table></div>' % (e(titre), "".join(lignes))
    )


def comparaison(regles, llm, ecarts, verdict, contexte, notifie, message=None):
    """Vue cote a cote regles / extraction distante ; validation = regles."""
    champs_ecart = {x["champ"] for x in ecarts}
    bandeau_msg = ""
    if message:
        bandeau_msg = (
            '<div class="bandeau b-vigilance">%s</div>' % e(message))
    elif llm:
        bandeau_msg = (
            '<div class="bandeau b-info">Comparaison effectuée — '
            '%d écart(s) surligné(s). Le verdict et le formulaire restent '
            'ceux du moteur de règles.</div>' % len(ecarts))
    liste_ecarts = "".join(
        "<li><strong>%s</strong> : règles = <span class='mono'>%s</span> · "
        "distant = <span class='mono'>%s</span></li>" % (
            e(x["champ"]), e(x["regles"]), e(x["llm"]))
        for x in ecarts
    ) or "<li class='muted'>Aucun écart détecté.</li>"

    return page("Comparaison des moteurs", f"""
<h1>Comparaison des moteurs</h1>
<p class="lede">Les écarts sont surlignés. Seul le moteur de règles décide du
verdict et alimente le formulaire de validation.</p>
{bandeau_msg}
<div class="comparaison">
  {_tableau_extraction(regles, champs_ecart, "Moteur de règles (décision)")}
  {_tableau_extraction(llm, champs_ecart, "Extraction distante" if llm else "Extraction distante (indisponible)")}
</div>
<div class="card">
  <h2 style="margin-top:0">Écarts</h2>
  <ul class="motifs">{liste_ecarts}</ul>
  <p class="muted">Verdict règles : {pill(verdict['niveau'])}</p>
</div>
{_formulaire_validation(regles, verdict, contexte)}
""", "/nouveau")


def rapport_page(r, alerte=None, date_edition=None):
    motifs = json.loads(r["motifs"]) if r.get("motifs") else []
    lignes = "".join("<li>%s</li>" % e(m) for m in motifs)
    mesures = "".join(f"<tr><th>{l}</th><td class='mono'>{e(v)}</td></tr>" for l, v in [
        ("Courant mesuré", "%s A" % r["courant_a"] if r["courant_a"] is not None else "—"),
        ("Isolement", "%s MΩ" % r["isolement_mohm"] if r["isolement_mohm"] is not None else "—"),
        ("Feux hors service", r["feux_hs"] if r["feux_hs"] is not None else "—"),
        ("Durée", "%s h" % r["duree_h"] if r["duree_h"] is not None else "—"),
        ("Travail de nuit", "oui" if r["travail_de_nuit"] else "non"),
        ("Consignation", "oui" if r["consignation"] else "non mentionnée"),
        ("Habilitation", r["habilitation"] or "—"),
    ])
    edition = date_edition or date.today().isoformat()
    bloc_alerte = ""
    if alerte:
        canaux = json.loads(alerte.get("canaux") or "{}")
        etat = " · ".join("%s : %s" % (k, v) for k, v in canaux.items())
        bloc_alerte = f"""<div class="card noprint"><h2 style="margin-top:0">Alerte émise</h2>
<p class="muted">{e(etat)}</p><pre>{e(alerte['corps'])}</pre></div>"""
    return page("Rapport %s" % r["reference"], f"""
<div class="row noprint" style="justify-content:space-between">
  <h1 style="margin:0">Rapport {e(r['reference'])}</h1>
  <div class="row"><span>{pill(r['niveau'])}</span>
  <button onclick="window.print()">Imprimer</button>
  <a class="btn sec" href="/rapport/{r['id']}/odoo.json">Export Odoo</a>
  <a class="btn sec" href="/rapports">Retour</a></div>
</div>
<h1 class="impression-seulement">Rapport {e(r['reference'])} — {pill(r['niveau'])}</h1>
<div class="card">
  <table>
    <tr><th>Site</th><td>{lien_site(r['site'])}</td>
        <th>Circuit</th><td>{lien_circuit(r['circuit'])}</td></tr>
    <tr><th>Date</th><td>{e(r['date'])}</td><th>Technicien</th><td>{e(r['technicien'])}</td></tr>
    <tr><th>Système</th><td>{e(r['systeme'])}</td><th>Nature</th><td>{e(r['nature'])}</td></tr>
  </table>
  <h2>Valeurs relevées</h2><table>{mesures}</table>
  <h2>Travaux réalisés</h2><p>{e(r['travaux']) or '—'}</p>
  <h2>Constat et anomalies</h2><p>{e(r['constat']) or '—'}</p>
  <h2>Suite à donner</h2><p>{e(r['suite']) or '—'}</p>
  <h2>Évaluation</h2><ul class="motifs">{lignes}</ul>
  <p class="muted" style="margin-top:22px">Extraction : {e(r['moteur'])}.
  Les seuils appliqués sont ceux paramétrés dans la configuration.</p>
  <div class="signatures impression-seulement">
    <div class="case"><div class="titre">Signature intervenant</div>
      <p class="muted">Nom / date</p></div>
    <div class="case"><div class="titre">Visa client</div>
      <p class="muted">Nom / date</p></div>
  </div>
  <div class="pied-impression impression-seulement">
    Référence {e(r['reference'])} — Édité le {e(edition)}
  </div>
</div>
{bloc_alerte}
<div class="card noprint"><h2 style="margin-top:0">Note d'origine</h2>
<pre>{e(r['note_brute'])}</pre></div>""", "/rapports")


def liste_rapports(rapports):
    lignes = "".join(f"""<tr><td class="mono">{e(r['reference'])}</td><td>{e(r['date'])}</td>
<td>{lien_site(r['site'])}</td><td>{lien_circuit(r['circuit'])}</td><td>{e(r['systeme'])}</td>
<td>{e(r['nature'])}</td><td class="mono">{e(r['isolement_mohm'])}</td>
<td class="mono">{e(r['feux_hs'])}</td><td>{pill(r['niveau'])}</td>
<td><a href="/rapport/{r['id']}">ouvrir</a></td></tr>""" for r in rapports) or \
        '<tr><td colspan="10" class="muted">Aucun rapport.</td></tr>'
    return page("Rapports", f"""
<h1>Rapports</h1>
<p class="lede">Historique complet des interventions saisies.
  <a href="/export.csv">Export CSV</a> ·
  <a href="/export.json">Export JSON</a>
  — filtrable via <span class="mono">?site=&amp;circuit=&amp;debut=&amp;fin=</span></p>
<div class="card"><table><tr><th>Réf.</th><th>Date</th><th>Site</th><th>Circuit</th>
<th>Système</th><th>Nature</th><th>MΩ</th><th>Feux HS</th><th>Niveau</th><th></th></tr>
{lignes}</table></div>""", "/rapports")


def liste_alertes(alertes):
    blocs = "".join(f"""<div class="card"><div class="row" style="justify-content:space-between">
<strong>{e(a['titre'])}</strong><span>{pill(a['niveau'])}</span></div>
<p class="muted">{e(a['cree_le'])} — canaux : {e(a['canaux'])}</p>
<pre>{e(a['corps'])}</pre></div>""" for a in alertes) or \
        '<div class="card muted">Aucune alerte émise pour le moment.</div>'
    return page("Alertes", f"""
<h1>Alertes</h1><p class="lede">Journal de tout ce qui a été envoyé. Le journal
est tenu même quand aucun canal externe n'est configuré, pour qu'il reste une
trace hors ligne.</p>{blocs}""", "/alertes")


def config_page(config, journal_llm=None):
    journal_llm = journal_llm or []
    lignes_j = "".join(
        "<tr><td class='mono'>%s</td><td class='mono'>%s ms</td>"
        "<td>%s</td><td class='mono'>%s</td><td>%s</td></tr>" % (
            e(j.get("cree_le")), e(j.get("duree_ms")),
            "ok" if j.get("succes") else "échec",
            e(j.get("moteur")), e(j.get("detail")),
        ) for j in journal_llm
    ) or "<tr><td colspan='5' class='muted'>Aucun appel distant journalisé.</td></tr>"
    return page("Seuils", f"""
<h1>Seuils et notifications</h1>
<p class="lede">Aucun seuil n'est codé en dur dans l'application. Ils sont
définis ici, par système de balisage, parce qu'une valeur réglementaire dépend
du contrat et de l'exploitant.</p>
<div class="card"><pre>{e(json.dumps(config, indent=2, ensure_ascii=False))}</pre>
<p class="muted">Fichier <span class="mono">config.json</span> à la racine du
projet. Redémarrer l'application après modification. Pour activer l'extraction
distante : renseigner <span class="mono">api_key</span> et
<span class="mono">autoriser_envoi: true</span>.</p></div>
<div class="card">
  <h2 style="margin-top:0">Journal des appels distants</h2>
  <p class="muted">Horodatage, durée, succès/échec, moteur. Aucune note n'est
  envoyée sans autorisation explicite.</p>
  <table><tr><th>Horodatage</th><th>Durée</th><th>Résultat</th><th>Moteur</th>
  <th>Détail</th></tr>{lignes_j}</table>
</div>""", "/config")


def bloc_projection(projection):
    """Affiche la projection uniquement si elle est active (avec sa reserve)."""
    if not projection or not projection.get("active") or not projection.get("phrase"):
        return ""
    return (
        '<div class="bandeau b-vigilance" style="margin-top:12px;margin-bottom:0">'
        '<strong>Tendance</strong> — %s</div>' % e(projection["phrase"])
    )


def circuit_page(meta, score, rapports, courbe_html, seuil_iso):
    """Fiche circuit : identification, etat, correctives, historique, courbe."""
    dernier = score.get("dernier") or (rapports[0] if rapports else None)
    designation = (meta or {}).get("designation") or (dernier or {}).get("systeme") or "—"
    site = (meta or {}).get("site") or (dernier or {}).get("site") or "—"
    regulateur = (meta or {}).get("regulateur") or "—"
    puissance = (meta or {}).get("puissance_kva")
    feux = (meta or {}).get("feux")
    circuit = score.get("circuit") or (dernier or {}).get("circuit") or "—"
    projection = score.get("projection") or {}

    etat = "—"
    if dernier:
        parts = []
        if dernier.get("isolement_mohm") is not None:
            parts.append("%s MΩ" % dernier["isolement_mohm"])
        if dernier.get("courant_a") is not None:
            parts.append("%s A" % dernier["courant_a"])
        if dernier.get("feux_hs") is not None:
            parts.append("%s feux HS" % dernier["feux_hs"])
        etat = " · ".join(parts) if parts else "—"

    detail = "".join(
        "<li><strong>+%.1f</strong> — %s</li>" % (d["points"], e(d["texte"]))
        for d in score.get("detail") or []
    )

    lignes = "".join(
        '<tr><td>%s</td><td class="mono">%s</td><td>%s</td><td>%s</td>'
        '<td class="mono">%s</td><td class="mono">%s</td><td>%s</td>'
        '<td><a href="/rapport/%s">ouvrir</a></td></tr>' % (
            e(r["date"]), e(r["reference"]), e(r["nature"]), e(r["controle"]),
            e(r["isolement_mohm"] if r["isolement_mohm"] is not None else "—"),
            e(r["feux_hs"] if r["feux_hs"] is not None else "—"),
            pill(r["niveau"]), r["id"],
        ) for r in rapports
    ) or '<tr><td colspan="8" class="muted">Aucun rapport pour ce circuit.</td></tr>'

    return page("Circuit %s" % circuit, f"""
<div class="row" style="justify-content:space-between;align-items:baseline">
  <div>
    <h1>Circuit {e(circuit)}</h1>
    <p class="lede" style="margin:0">{e(designation)} — {lien_site(site)}</p>
  </div>
  <div class="row">
    <span class="score {classe_score(score.get('score', 0))}" style="font-size:28px">
      {score.get('score', 0)}</span>
    <span class="muted">score de risque</span>
  </div>
</div>
<div class="grid g3">
  <div class="kpi"><div class="l">État courant</div>
    <div class="v" style="font-size:18px">{e(etat)}</div>
    <div class="muted">{pill((dernier or {}).get('niveau') or 'info')}
      — {e((dernier or {}).get('date') or '')}</div></div>
  <div class="kpi"><div class="l">Correctives 12 mois</div>
    <div class="v">{score.get('correctives_12m', 0)}</div></div>
  <div class="kpi"><div class="l">Identification</div>
    <div class="muted">Régulateur <span class="mono">{e(regulateur)}</span>
    · {e(puissance) + ' kVA' if puissance is not None else '—'}
    · {e(feux) + ' feux' if feux is not None else '—'}</div>
    <div class="muted">Seuil isolement paramétré : {e(seuil_iso)} MΩ</div></div>
</div>
<div class="card">
  <h2 style="margin-top:0">Courbe d'isolement</h2>
  {courbe_html}
  {bloc_projection(projection)}
  <h2>Détail du score</h2>
  <ul class="motifs">{detail or '<li class="muted">Aucun détail.</li>'}</ul>
</div>
<div class="card">
  <h2 style="margin-top:0">Historique du circuit</h2>
  <table><tr><th>Date</th><th>Réf.</th><th>Nature</th><th>Contrôle</th>
  <th>MΩ</th><th>Feux HS</th><th>Niveau</th><th></th></tr>
  {lignes}</table>
</div>""", "/sites")


def sites_page(lignes_sites):
    lignes = "".join(
        '<tr><td>%s</td><td class="mono">%d</td><td class="mono">%d</td>'
        '<td class="mono">%d</td><td>%s</td></tr>' % (
            lien_site(s["site"]), s["nb_circuits"], s["feux_hs"], s["en_alerte"],
            e(s["derniere"] or "—"),
        ) for s in lignes_sites
    ) or '<tr><td colspan="5" class="muted">Aucun site.</td></tr>'
    return page("Sites", f"""
<h1>Sites</h1>
<p class="lede">Vue par plateforme : circuits suivis, feux hors service cumulés
(dernier relevé), circuits en alerte et dernière intervention.</p>
<div class="card"><table>
<tr><th>Site</th><th>Circuits</th><th>Feux HS</th><th>En alerte</th>
<th>Dernière intervention</th></tr>
{lignes}</table></div>""", "/sites")


def site_page(nom, circuits_scores, rapports):
    lignes_c = "".join(
        '<tr><td>%s</td><td class="mono">%s</td><td><span class="score %s">%d</span></td>'
        '<td>%s</td><td class="muted">%s</td></tr>' % (
            lien_circuit(c["circuit"]),
            e((c.get("dernier") or {}).get("systeme") or "—"),
            classe_score(c["score"]), c["score"],
            pill((c.get("dernier") or {}).get("niveau") or "info"),
            e(c["motif_dominant"]),
        ) for c in circuits_scores
    ) or '<tr><td colspan="5" class="muted">Aucun circuit.</td></tr>'

    lignes_r = "".join(
        '<tr><td>%s</td><td class="mono">%s</td><td>%s</td><td>%s</td>'
        '<td><a href="/rapport/%s">ouvrir</a></td></tr>' % (
            e(r["date"]), e(r["reference"]), lien_circuit(r["circuit"]),
            pill(r["niveau"]), r["id"],
        ) for r in rapports[:30]
    ) or '<tr><td colspan="5" class="muted">Aucun rapport.</td></tr>'

    return page("Site %s" % nom, f"""
<h1>Site {e(nom)}</h1>
<p class="lede"><a href="/sites">← Tous les sites</a></p>
<div class="card">
  <h2 style="margin-top:0">Circuits</h2>
  <table><tr><th>Circuit</th><th>Système</th><th>Score</th><th>Niveau</th>
  <th>Motif</th></tr>{lignes_c}</table>
</div>
<div class="card">
  <h2 style="margin-top:0">Dernières interventions</h2>
  <table><tr><th>Date</th><th>Réf.</th><th>Circuit</th><th>Niveau</th><th></th></tr>
  {lignes_r}</table>
</div>""", "/sites")
