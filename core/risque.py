# -*- coding: utf-8 -*-
"""Score de risque par circuit (0 a 100) avec explication lisible.

Les ponderations viennent de config.json (cle « risque »). Aucun poids n'est
code en dur : un score sans explication est inutilisable dans ce metier.

La projection de tendance (franchissement du seuil d'isolement) applique trois
garde-fous : au moins trois releves, horizon max 24 mois, reserve explicite.
"""

from datetime import date, timedelta

from core import seuils

MOIS_FR = (
    "", "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
)


def _ponderations(config):
    risque = (config or {}).get("risque") or {}
    p = dict(risque.get("ponderations") or {})
    # Replis documentes : a confirmer avec l'exploitant si absents de la config.
    return {
        "isolement": float(p.get("isolement", 30)),
        "feux_hs": float(p.get("feux_hs", 20)),
        "correctives": float(p.get("correctives", 20)),
        "anciennete": float(p.get("anciennete", 15)),
        "pente": float(p.get("pente", 15)),
    }


def _projection_cfg(config):
    """Parametres de tendance ; valeurs de repli a confirmer avec l'exploitant."""
    bloc = ((config or {}).get("risque") or {}).get("projection") or {}
    return {
        "pente_significative": float(bloc.get("pente_significative_mohm_j", -0.02)),
        "horizon_mois": int(bloc.get("horizon_max_mois", 24)),
    }


def _periodicite(config, controle):
    per = ((config or {}).get("risque") or {}).get("periodicite_jours") or {}
    if controle and controle in per:
        return float(per[controle])
    return float(per.get("defaut", 90))


def _parse_date(valeur):
    if not valeur:
        return None
    try:
        return date.fromisoformat(str(valeur)[:10])
    except ValueError:
        return None


def points_isolement(releves, seuil_iso, poids):
    """Marge d'isolement par rapport au seuil (dernier releve connu)."""
    if not releves or not seuil_iso or poids <= 0:
        return 0.0, "Pas de releve d'isolement exploitable."
    dernier = releves[-1][1]
    if dernier is None:
        return 0.0, "Dernier releve d'isolement absent."
    if dernier < seuil_iso:
        return poids, "Isolement %.0f MΩ sous le seuil de %.0f MΩ (+%.0f pts)." % (
            dernier, seuil_iso, poids)
    # Zone de vigilance : entre seuil et 1,5 x seuil
    plafond = seuil_iso * 1.5
    if dernier < plafond:
        ratio = (plafond - dernier) / (plafond - seuil_iso)
        pts = round(poids * max(0.0, min(1.0, ratio)), 1)
        return pts, "Isolement %.0f MΩ proche du seuil (+%.1f pts)." % (dernier, pts)
    return 0.0, "Isolement %.0f MΩ confortable (0 pt)." % dernier


def points_feux(feux_hs, seuil_hs, poids):
    if feux_hs is None or not seuil_hs or poids <= 0:
        return 0.0, "Pas de comptage de feux hors service."
    ratio = min(1.0, float(feux_hs) / float(seuil_hs))
    pts = round(poids * ratio, 1)
    return pts, "%s feu(x) HS / seuil %s (+%.1f pts)." % (feux_hs, seuil_hs, pts)


def points_correctives(nb, seuil_rec, poids):
    if poids <= 0:
        return 0.0, "Composante correctives desactivee."
    seuil = float(seuil_rec or 3)
    ratio = min(1.0, float(nb) / seuil)
    pts = round(poids * ratio, 1)
    return pts, "%d corrective(s) / 12 mois (seuil %g) (+%.1f pts)." % (nb, seuil, pts)


def points_anciennete(derniere_date, controle, config, poids):
    if poids <= 0:
        return 0.0, "Composante anciennete desactivee."
    d = _parse_date(derniere_date)
    if not d:
        return poids, "Aucune intervention connue (+%.0f pts)." % poids
    attendu = _periodicite(config, controle)
    ecart = (date.today() - d).days
    ratio = min(1.0, max(0.0, ecart / attendu))
    pts = round(poids * ratio, 1)
    return pts, "Derniere intervention il y a %d j (periodicite %.0f j) (+%.1f pts)." % (
        ecart, attendu, pts)


def regression_lineaire(points):
    """Moindres carres sur [(x, y), ...]. Renvoie (pente, ordonnee) ou None."""
    n = len(points)
    if n < 2:
        return None
    sx = sum(p[0] for p in points)
    sy = sum(p[1] for p in points)
    sxx = sum(p[0] * p[0] for p in points)
    sxy = sum(p[0] * p[1] for p in points)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None
    pente = (n * sxy - sx * sy) / denom
    ordonnee = (sy - pente * sx) / n
    return pente, ordonnee


def _trois_derniers(releves):
    """Les trois derniers points exploitables, ou None."""
    if len(releves) < 3:
        return None
    derniers = releves[-3:]
    points = []
    for d, v in derniers:
        if d is None or v is None:
            return None
        points.append((float(d.toordinal()), float(v)))
    return derniers, points


def pente_isolement(releves):
    """Pente en MΩ / jour sur les trois derniers releves (x = jours epoch)."""
    paquet = _trois_derniers(releves)
    if not paquet:
        return None
    _, points = paquet
    reg = regression_lineaire(points)
    if not reg:
        return None
    return reg[0]


def points_pente(releves, poids, config=None):
    if poids <= 0:
        return 0.0, "Composante pente desactivee."
    if len(releves) < 3:
        return 0.0, "Moins de trois releves : pente non calculee."
    pente = pente_isolement(releves)
    if pente is None:
        return 0.0, "Pente non calculable."
    seuil_pente = _projection_cfg(config)["pente_significative"]
    if pente >= seuil_pente:
        return 0.0, "Pente d'isolement non degradante (%.3f MΩ/j)." % pente
    # Intensite relative a |seuil| .. 10 x |seuil|
    ref = max(abs(seuil_pente) * 10.0, 0.20)
    intensite = min(1.0, abs(pente) / ref)
    pts = round(poids * intensite, 1)
    return pts, "Pente d'isolement %.3f MΩ/j (+%.1f pts)." % (pente, pts)


def releves_isolement(rapports):
    """Liste chronologique [(date, isolement), ...] pour tendance et score.

    Privilegie les campagnes de mesure d'isolement lorsqu'il y en a au moins
    trois : les inspections visuelles qui recopient la derniere valeur
    aplatissent artificiellement la pente.
    """
    tries = sorted(rapports, key=lambda x: x.get("date") or "")
    campagnes = []
    tous = []
    for r in tries:
        iso = r.get("isolement_mohm")
        d = _parse_date(r.get("date"))
        if iso is None or d is None:
            continue
        point = (d, float(iso))
        tous.append(point)
        if (r.get("controle") or "") == "isolement":
            campagnes.append(point)
    if len(campagnes) >= 3:
        return campagnes
    return tous


def libelle_mois(jour):
    return "%s %d" % (MOIS_FR[jour.month], jour.year)


def projeter_franchissement(releves, seuil_iso, config=None):
    """Estime la date de franchissement du seuil d'isolement.

    Garde-fous non negociables :
      1. jamais avec moins de trois releves ;
      2. jamais au-dela de l'horizon configure (24 mois par defaut) ;
      3. la phrase contient toujours une reserve explicite.
    """
    resultat = {
        "active": False,
        "phrase": None,
        "date_estimee": None,
        "pente": None,
        "nb_releves": len(releves),
    }
    if seuil_iso is None:
        return resultat
    paquet = _trois_derniers(releves)
    if not paquet:
        return resultat
    derniers, points = paquet
    reg = regression_lineaire(points)
    if not reg:
        return resultat
    pente, ordonnee = reg
    resultat["pente"] = pente

    cfg = _projection_cfg(config)
    if pente >= cfg["pente_significative"]:
        # Pente non degradante (ou insuffisamment significative).
        return resultat

    dernier_val = derniers[-1][1]
    if dernier_val is not None and dernier_val < float(seuil_iso):
        # Seuil deja franchi : pas de projection future.
        return resultat

    # y = pente * x + ordonnee  =>  x = (seuil - ordonnee) / pente
    x_seuil = (float(seuil_iso) - ordonnee) / pente
    try:
        date_est = date.fromordinal(int(round(x_seuil)))
    except (ValueError, OverflowError):
        return resultat

    aujourdhui = date.today()
    if date_est <= aujourdhui:
        return resultat

    horizon = aujourdhui + timedelta(days=int(cfg["horizon_mois"]) * 30 + 5)
    if date_est > horizon:
        return resultat

    nb = 3
    phrase = (
        "À ce rythme, le seuil de %.0f MΩ serait atteint vers %s. "
        "Estimation à partir de %d relevés, à confirmer par la prochaine campagne."
        % (float(seuil_iso), libelle_mois(date_est), nb)
    )
    resultat.update({
        "active": True,
        "phrase": phrase,
        "date_estimee": date_est.isoformat(),
        "nb_releves": nb,
    })
    return resultat


def scorer_circuit(circuit, rapports, config, correctives_12m=None):
    """Calcule le score 0-100, le detail des composantes et la projection."""
    pond = _ponderations(config)
    vide = {
        "circuit": circuit,
        "score": 0,
        "motif_dominant": "Aucun historique.",
        "detail": [],
        "dernier": None,
        "releves": [],
        "correctives_12m": 0,
        "projection": {
            "active": False, "phrase": None, "date_estimee": None,
            "pente": None, "nb_releves": 0,
        },
    }
    if not rapports:
        return vide

    tri = sorted(rapports, key=lambda r: r.get("date") or "")
    dernier = tri[-1]
    s = seuils.seuils_du_systeme(config, dernier.get("systeme"))
    releves = releves_isolement(tri)
    nb_corr = correctives_12m
    if nb_corr is None:
        limite = date.fromordinal(date.today().toordinal() - 365).isoformat()
        nb_corr = sum(
            1 for r in tri
            if r.get("nature") == "corrective" and (r.get("date") or "") >= limite)

    detail = []
    total = 0.0

    pts, txt = points_isolement(releves, s.get("isolement_mohm"), pond["isolement"])
    detail.append({"cle": "isolement", "points": pts, "texte": txt})
    total += pts

    pts, txt = points_feux(dernier.get("feux_hs"), s.get("feux_hs_alerte"), pond["feux_hs"])
    detail.append({"cle": "feux_hs", "points": pts, "texte": txt})
    total += pts

    pts, txt = points_correctives(nb_corr, s.get("recurrence_12m"), pond["correctives"])
    detail.append({"cle": "correctives", "points": pts, "texte": txt})
    total += pts

    pts, txt = points_anciennete(
        dernier.get("date"), dernier.get("controle"), config, pond["anciennete"])
    detail.append({"cle": "anciennete", "points": pts, "texte": txt})
    total += pts

    pts, txt = points_pente(releves, pond["pente"], config)
    detail.append({"cle": "pente", "points": pts, "texte": txt})
    total += pts

    score = int(round(min(100.0, max(0.0, total))))
    dominant = max(detail, key=lambda d: d["points"])
    motif = dominant["texte"] if dominant["points"] > 0 else "Risque faible."
    projection = projeter_franchissement(
        releves, s.get("isolement_mohm"), config)

    return {
        "circuit": circuit,
        "score": score,
        "motif_dominant": motif,
        "detail": detail,
        "dernier": dernier,
        "releves": releves,
        "correctives_12m": nb_corr,
        "projection": projection,
    }


def classer_circuits(par_circuit, config, correctives_fn=None):
    """Renvoie la liste des scores, du plus eleve au plus bas."""
    scores = []
    for circuit, rapports in par_circuit.items():
        corr = correctives_fn(circuit) if correctives_fn else None
        scores.append(scorer_circuit(circuit, rapports, config, corr))
    scores.sort(key=lambda s: (-s["score"], s["circuit"] or ""))
    return scores
