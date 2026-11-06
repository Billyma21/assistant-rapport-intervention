# -*- coding: utf-8 -*-
"""Exports CSV / JSON et charge utile ERP (Odoo).

Aucun framework : csv et json de la bibliotheque standard.
"""

import csv
import io
import json
from datetime import date


# Colonnes CSV stables (ordre fixe pour Excel / import).
COLONNES_CSV = [
    "reference", "date", "site", "circuit", "systeme", "nature", "controle",
    "technicien", "courant_a", "isolement_mohm", "feux_hs", "duree_h",
    "travail_de_nuit", "consignation", "habilitation", "niveau",
    "travaux", "constat", "suite", "moteur",
]


def filtrer_rapports(rapports, site=None, circuit=None, debut=None, fin=None):
    """Filtre une liste de rapports selon site, circuit et periode (dates ISO)."""
    resultat = []
    for r in rapports:
        if site and (r.get("site") or "") != site:
            continue
        if circuit and (r.get("circuit") or "") != circuit:
            continue
        d = (r.get("date") or "")[:10]
        if debut and d < debut:
            continue
        if fin and d > fin:
            continue
        resultat.append(r)
    return resultat


def _cellule(valeur):
    if valeur is None:
        return ""
    if isinstance(valeur, bool) or valeur in (0, 1):
        # travail_de_nuit / consignation stockes en 0/1
        if valeur in (0, 1) and not isinstance(valeur, bool):
            return str(int(valeur))
    return str(valeur)


def vers_csv(rapports):
    """CSV point-virgule, UTF-8 avec BOM (Excel)."""
    tampon = io.StringIO()
    writer = csv.writer(tampon, delimiter=";", quoting=csv.QUOTE_MINIMAL,
                        lineterminator="\n")
    writer.writerow(COLONNES_CSV)
    for r in rapports:
        writer.writerow([_cellule(r.get(c)) for c in COLONNES_CSV])
    # BOM UTF-8 pour qu'Excel ouvre correctement les accents
    return "\ufeff" + tampon.getvalue()


def vers_json(rapports):
    """Liste JSON des rapports (champs utiles, motifs parses)."""
    sortie = []
    for r in rapports:
        motifs = r.get("motifs")
        if isinstance(motifs, str):
            try:
                motifs = json.loads(motifs)
            except json.JSONDecodeError:
                motifs = [motifs] if motifs else []
        sortie.append({
            "id": r.get("id"),
            "reference": r.get("reference"),
            "date": r.get("date"),
            "site": r.get("site"),
            "circuit": r.get("circuit"),
            "systeme": r.get("systeme"),
            "nature": r.get("nature"),
            "controle": r.get("controle"),
            "technicien": r.get("technicien"),
            "courant_a": r.get("courant_a"),
            "isolement_mohm": r.get("isolement_mohm"),
            "feux_hs": r.get("feux_hs"),
            "duree_h": r.get("duree_h"),
            "travail_de_nuit": bool(r.get("travail_de_nuit")),
            "consignation": bool(r.get("consignation")),
            "habilitation": r.get("habilitation"),
            "niveau": r.get("niveau"),
            "motifs": motifs,
            "travaux": r.get("travaux"),
            "constat": r.get("constat"),
            "suite": r.get("suite"),
            "moteur": r.get("moteur"),
        })
    return json.dumps(sortie, ensure_ascii=False, indent=2)


def charge_odoo(rapport):
    """Objet JSON exploitable comme charge utile de creation d'un releve ERP.

    Champs minimaux demandes : site, circuit, date, type de controle,
    courant mesure, isolement, feux hors service, conformite, observations.
    """
    motifs = rapport.get("motifs")
    if isinstance(motifs, str):
        try:
            motifs = json.loads(motifs)
        except json.JSONDecodeError:
            motifs = []
    niveau = rapport.get("niveau") or "info"
    observations = []
    if rapport.get("constat"):
        observations.append(rapport["constat"])
    if rapport.get("suite"):
        observations.append("Suite : " + rapport["suite"])
    if motifs:
        observations.append("Motifs : " + " | ".join(motifs))

    return {
        "site": rapport.get("site"),
        "circuit": rapport.get("circuit"),
        "date": rapport.get("date"),
        "type_controle": rapport.get("controle"),
        "systeme": rapport.get("systeme"),
        "nature": rapport.get("nature"),
        "courant_mesure_a": rapport.get("courant_a"),
        "isolement_mohm": rapport.get("isolement_mohm"),
        "feux_hors_service": rapport.get("feux_hs"),
        "conformite": niveau == "info",
        "niveau": niveau,
        "observations": "\n".join(observations).strip(),
        "reference_externe": rapport.get("reference"),
        "technicien": rapport.get("technicien"),
        "travaux": rapport.get("travaux") or "",
        "date_export": date.today().isoformat(),
    }
