#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Charge un historique de demonstration dans la base.

IMPORTANT — Ces donnees sont plausibles et construites pour la demonstration.
Il ne s'agit PAS de donnees d'exploitation. Aucun nom d'entreprise, aucun
identifiant personnel : les techniciens sont des roles generiques, les sites
sont des noms de villes.

Sans historique, la detection de recurrence ne peut rien montrer. Ce script
construit un parc coherent sur dix-huit mois pour que les regles se
declenchent de facon lisible pendant une demonstration.

    python3 historique.py              ajoute l'historique (si base vide)
    python3 historique.py --vider      repart d'une base vide
    python3 historique.py --resume     charge si besoin et affiche un recapitulatif

Determinisme : random.seed fixe, dates calculees relativement a aujourd'hui.
Deux executions consecutives produisent exactement la meme base.
"""

import json
import os
import random
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import storage  # noqa: E402

# Graine fixe : toute evolution du generateur doit conserver le meme resultat
# pour une meme date de reference, ou documenter la rupture.
GRAINE = 20261105
HORIZON_JOURS = 548  # ~18 mois

TECHNICIENS = ("Equipe terrain", "Equipe nuit", "Equipe controle")


# --------------------------------------------------------------------------
# Parc : 6 plateformes, ~20 circuits
# --------------------------------------------------------------------------

# Trois sites en Belgique, deux en France, un aux Pays-Bas.
# designation : libelle d'exploitation credible.
# regulateur / puissance_kva / feux : metadonnees de demonstration.
CIRCUITS = [
    # --- Bruxelles (BE) ---------------------------------------------------
    dict(id="CIR-0001", site="Bruxelles", pays="BE",
         designation="07L/25R — axe de piste", systeme="axe de piste",
         regulateur="CCR-B1", puissance_kva=15, feux=280),
    dict(id="CIR-0002", site="Bruxelles", pays="BE",
         designation="07L/25R — bord de piste", systeme="bord de piste",
         regulateur="CCR-B2", puissance_kva=10, feux=160),
    dict(id="CIR-0003", site="Bruxelles", pays="BE",
         designation="25R — zone de toucher des roues (TDZ)",
         systeme="zone de toucher des roues (TDZ)",
         regulateur="CCR-B3", puissance_kva=10, feux=90),
    dict(id="CIR-0004", site="Bruxelles", pays="BE",
         designation="Rampe d'approche 25R", systeme="rampe d'approche",
         regulateur="CCR-B4", puissance_kva=20, feux=48),
    # --- Liege (BE) -------------------------------------------------------
    dict(id="CIR-0005", site="Liège", pays="BE",
         designation="05/23 — axe de piste", systeme="axe de piste",
         regulateur="CCR-L1", puissance_kva=15, feux=220),
    dict(id="CIR-0006", site="Liège", pays="BE",
         designation="05/23 — bord de piste", systeme="bord de piste",
         regulateur="CCR-L2", puissance_kva=10, feux=140),
    dict(id="CIR-0007", site="Liège", pays="BE",
         designation="PAPI 23 — cote gauche", systeme="PAPI",
         regulateur="CCR-L3", puissance_kva=4, feux=4),
    dict(id="CIR-0008", site="Liège", pays="BE",
         designation="PAPI 23 — cote droit", systeme="PAPI",
         regulateur="CCR-L4", puissance_kva=4, feux=4),
    dict(id="CIR-0009", site="Liège", pays="BE",
         designation="Barres d'arrêt — points d'attente",
         systeme="barres d'arrêt",
         regulateur="CCR-L5", puissance_kva=5, feux=24),
    # --- Anvers (BE) ------------------------------------------------------
    dict(id="CIR-0010", site="Anvers", pays="BE",
         designation="11/29 — seuil et extrémité", systeme="seuil",
         regulateur="CCR-A1", puissance_kva=7.5, feux=36),
    dict(id="CIR-0011", site="Anvers", pays="BE",
         designation="11/29 — bord de piste", systeme="bord de piste",
         regulateur="CCR-A2", puissance_kva=10, feux=120),
    dict(id="CIR-0012", site="Anvers", pays="BE",
         designation="Balisage d'obstacles — mats",
         systeme="balisage d'obstacles",
         regulateur="CCR-A3", puissance_kva=2.5, feux=12),
    # --- Paris (FR) -------------------------------------------------------
    dict(id="CIR-0013", site="Paris", pays="FR",
         designation="Bretelle W — axe de voie de circulation",
         systeme="axe de voie de circulation",
         regulateur="CCR-P1", puissance_kva=10, feux=85),
    dict(id="CIR-0014", site="Paris", pays="FR",
         designation="Bretelle W — bord de voie de circulation",
         systeme="bord de voie de circulation",
         regulateur="CCR-P2", puissance_kva=7.5, feux=60),
    dict(id="CIR-0015", site="Paris", pays="FR",
         designation="08R/26L — axe de piste", systeme="axe de piste",
         regulateur="CCR-P3", puissance_kva=20, feux=320),
    dict(id="CIR-0016", site="Paris", pays="FR",
         designation="Rampe d'approche 26L", systeme="rampe d'approche",
         regulateur="CCR-P4", puissance_kva=25, feux=54),
    # --- Lyon (FR) --------------------------------------------------------
    dict(id="CIR-0017", site="Lyon", pays="FR",
         designation="18/36 — bord de piste", systeme="bord de piste",
         regulateur="CCR-Y1", puissance_kva=10, feux=150),
    dict(id="CIR-0018", site="Lyon", pays="FR",
         designation="PAPI 36 — cote gauche", systeme="PAPI",
         regulateur="CCR-Y2", puissance_kva=4, feux=4),
    # --- Eindhoven (NL) ---------------------------------------------------
    dict(id="CIR-0019", site="Eindhoven", pays="NL",
         designation="03/21 — axe de piste", systeme="axe de piste",
         regulateur="CCR-E1", puissance_kva=15, feux=240),
    dict(id="CIR-0020", site="Eindhoven", pays="NL",
         designation="Barres d'arrêt — points d'attente A/B",
         systeme="barres d'arrêt",
         regulateur="CCR-E2", puissance_kva=5, feux=20),
]

CIRCUITS_PAR_ID = {c["id"]: c for c in CIRCUITS}


def il_y_a(jours):
    return (date.today() - timedelta(days=int(jours))).isoformat()


def _courant(rng):
    """Courant autour de 6,6 A, dans la tolerance habituelle."""
    return round(6.6 + rng.uniform(-0.08, 0.08), 2)


def _rapport(circuit, jours, nature, controle, **kwargs):
    """Fabrique un dict pret pour storage.enregistrer."""
    meta = CIRCUITS_PAR_ID[circuit]
    niveau = kwargs.pop("niveau", "info")
    motifs = kwargs.pop("motifs", ["Aucun ecart detecte par rapport aux seuils parametres."])
    base = dict(
        jours=jours,
        site=meta["site"],
        circuit=circuit,
        systeme=meta["systeme"],
        nature=nature,
        controle=controle,
        technicien=kwargs.pop("technicien", "Equipe terrain"),
        courant_a=kwargs.pop("courant_a", 6.60),
        isolement_mohm=kwargs.pop("isolement_mohm", 180.0),
        feux_hs=kwargs.pop("feux_hs", 0),
        duree_h=kwargs.pop("duree_h", 3.0),
        travail_de_nuit=kwargs.pop("travail_de_nuit", 1),
        consignation=kwargs.pop("consignation", 1),
        habilitation=kwargs.pop("habilitation", "B2V"),
        travaux=kwargs.pop("travaux", "Intervention de demonstration."),
        constat=kwargs.pop("constat", "Valeurs nominales."),
        suite=kwargs.pop("suite", "Rien a signaler."),
        niveau=niveau,
        motifs=motifs,
    )
    base.update(kwargs)
    return base


# --------------------------------------------------------------------------
# Trois trajectoires lisibles (hardcodees, hors alea)
# --------------------------------------------------------------------------

def trajectoire_isolement_decroissant():
    """CIR-0003 (TDZ Bruxelles) : trois campagnes, derniere sous le seuil."""
    return [
        _rapport("CIR-0003", 520, "preventive", "isolement",
                 courant_a=6.60, isolement_mohm=148.0, feux_hs=1, duree_h=5.5,
                 travaux="Campagne semestrielle d'isolement sur la boucle TDZ.",
                 constat="Valeurs confortables.",
                 suite="Prochaine campagne dans six mois.",
                 niveau="info"),
        _rapport("CIR-0003", 340, "preventive", "isolement",
                 courant_a=6.58, isolement_mohm=96.0, feux_hs=2, duree_h=5.5,
                 travaux="Campagne semestrielle d'isolement sur la boucle TDZ.",
                 constat="Isolement en baisse par rapport a la campagne precedente.",
                 suite="A surveiller de pres a la prochaine campagne.",
                 niveau="vigilance",
                 motifs=["Isolement 96 MOhm proche du seuil de 50 MOhm."]),
        _rapport("CIR-0003", 160, "preventive", "isolement",
                 courant_a=6.55, isolement_mohm=42.0, feux_hs=3, duree_h=6.0,
                 travaux="Campagne semestrielle d'isolement sur la boucle TDZ.",
                 constat="Isolement sous le seuil, suspicion d'infiltration portion est.",
                 suite="Recherche de defaut a programmer avant la prochaine visite.",
                 niveau="critique",
                 motifs=["Isolement 42 MOhm sous le seuil de 50 MOhm.",
                         "3 feux hors service, seuil d'alerte a 3."]),
        # Visites visuelles intercalaires, parcelle saine a cote de la trajectoire
        _rapport("CIR-0003", 430, "preventive", "visuel",
                 courant_a=6.60, isolement_mohm=148.0, feux_hs=0, duree_h=3.0,
                 travaux="Inspection visuelle mensuelle de la TDZ.",
                 constat="Aucun feu hors service.",
                 niveau="info"),
        _rapport("CIR-0003", 250, "preventive", "visuel",
                 courant_a=6.59, isolement_mohm=96.0, feux_hs=1, duree_h=3.0,
                 travaux="Inspection visuelle mensuelle de la TDZ.",
                 constat="Un feu hors service remplace sur place.",
                 niveau="vigilance",
                 motifs=["1 feu hors service."]),
        _rapport("CIR-0003", 40, "preventive", "visuel",
                 courant_a=6.54, isolement_mohm=42.0, feux_hs=2, duree_h=3.5,
                 travaux="Inspection visuelle mensuelle de la TDZ.",
                 constat="Deux feux hors service, isolement toujours sous le seuil.",
                 suite="Maintenir la surveillance jusqu'a la recherche de defaut.",
                 niveau="critique",
                 motifs=["Isolement 42 MOhm sous le seuil de 50 MOhm.",
                         "2 feux hors service."]),
    ]


def trajectoire_recurrence_corrective():
    """CIR-0009 (barres Liege) : quatre correctives / 12 mois, dont trois
    sur la meme portion (point d'attente ouest).

    Trois campagnes d'isolement (120 → 85 → 68) alimentent aussi la
    projection de tendance, encore au-dessus du seuil.
    """
    return [
        _rapport("CIR-0009", 300, "corrective", "visuel",
                 technicien="Equipe nuit", courant_a=6.58, isolement_mohm=118.0,
                 feux_hs=3, duree_h=2.5, habilitation="BR",
                 travaux="Remplacement de deux optiques au point d'attente ouest.",
                 constat="Trois feux hors service, meme portion ouest.",
                 suite="Surveiller la portion ouest a la prochaine visite.",
                 niveau="vigilance",
                 motifs=["3 feux hors service, seuil d'alerte a 2."]),
        _rapport("CIR-0009", 210, "corrective", "visuel",
                 technicien="Equipe nuit", courant_a=6.55, isolement_mohm=95.0,
                 feux_hs=4, duree_h=3.0, habilitation="BR",
                 travaux="Reprise d'un raccordement en defaut, portion ouest.",
                 constat="Meme portion de circuit que l'intervention precedente.",
                 suite="Surveiller la portion concernee.",
                 niveau="vigilance",
                 motifs=["4 feux hors service, seuil d'alerte a 2."]),
        _rapport("CIR-0009", 110, "corrective", "visuel",
                 technicien="Equipe nuit", courant_a=6.52, isolement_mohm=74.0,
                 feux_hs=5, duree_h=3.5, habilitation="BR",
                 travaux="Depannage d'urgence, remise en service barre d'arret ouest.",
                 constat="Isolement en baisse continue sur la boucle ouest.",
                 suite="Recherche de defaut a programmer.",
                 niveau="critique",
                 motifs=["5 feux hors service, seuil d'alerte a 2.",
                         "Isolement 74 MOhm proche du seuil de 50 MOhm."]),
        _rapport("CIR-0009", 35, "corrective", "visuel",
                 technicien="Equipe nuit", courant_a=6.50, isolement_mohm=68.0,
                 feux_hs=4, duree_h=3.0, habilitation="BR",
                 travaux="Remplacement d'optiques, portion centrale (autre troncon).",
                 constat="Quatrieme corrective en douze mois sur ce circuit.",
                 suite="Analyse de cause profonde a engager avec l'exploitant.",
                 niveau="critique",
                 motifs=["4 feux hors service, seuil d'alerte a 2.",
                         "Isolement 68 MOhm proche du seuil de 50 MOhm."]),
        # Campagnes d'isolement pour la projection de tendance
        _rapport("CIR-0009", 400, "preventive", "isolement",
                 courant_a=6.60, isolement_mohm=120.0, feux_hs=0, duree_h=3.0,
                 travaux="Mesure d'isolement semestrielle des barres d'arret.",
                 constat="Valeur de reference de campagne.",
                 niveau="info"),
        _rapport("CIR-0009", 220, "preventive", "isolement",
                 courant_a=6.55, isolement_mohm=85.0, feux_hs=1, duree_h=3.0,
                 travaux="Mesure d'isolement semestrielle des barres d'arret.",
                 constat="Isolement en baisse, coherent avec les correctives.",
                 niveau="vigilance",
                 motifs=["Isolement 85 MOhm proche du seuil de 50 MOhm.",
                         "1 feu hors service."]),
        _rapport("CIR-0009", 55, "preventive", "isolement",
                 courant_a=6.52, isolement_mohm=68.0, feux_hs=2, duree_h=3.5,
                 travaux="Mesure d'isolement semestrielle des barres d'arret.",
                 constat="Baisse continue, projection de franchissement a surveiller.",
                 suite="Confirmer a la prochaine campagne.",
                 niveau="vigilance",
                 motifs=["Isolement 68 MOhm proche du seuil de 50 MOhm.",
                         "2 feux hors service."]),
    ]


def trajectoire_parc_sain(rng):
    """Circuits globalement sains : contraste avec les deux trajectoires critiques."""
    sains = ["CIR-0001", "CIR-0002", "CIR-0005", "CIR-0011",
             "CIR-0015", "CIR-0017", "CIR-0019"]
    rapports = []
    for cid in sains:
        # Controle electrique annuel
        rapports.append(_rapport(
            cid, rng.randint(20, 350), "preventive", "electrique",
            courant_a=_courant(rng), isolement_mohm=round(rng.uniform(160, 280), 1),
            feux_hs=0, duree_h=round(rng.uniform(4.0, 7.0), 1),
            travaux="Controle electrique annuel : alimentations, parafoudres, coffrets.",
            constat="Valeurs nominales.",
            suite="Prochain controle au contrat.",
            niveau="info",
        ))
        # Une mesure d'isolement semestrielle
        rapports.append(_rapport(
            cid, rng.randint(30, HORIZON_JOURS - 10), "preventive", "isolement",
            courant_a=_courant(rng), isolement_mohm=round(rng.uniform(140, 260), 1),
            feux_hs=0, duree_h=round(rng.uniform(3.0, 6.0), 1),
            travaux="Campagne semestrielle de mesure d'isolement.",
            constat="Isolement confortable.",
            niveau="info",
        ))
        # Une inspection visuelle
        hs = rng.choice([0, 0, 0, 1])
        niveau = "info" if hs == 0 else "vigilance"
        motifs = (["Aucun ecart detecte par rapport aux seuils parametres."]
                  if hs == 0 else ["1 feu hors service."])
        rapports.append(_rapport(
            cid, rng.randint(5, HORIZON_JOURS - 5), "preventive", "visuel",
            courant_a=_courant(rng),
            isolement_mohm=round(rng.uniform(140, 250), 1),
            feux_hs=hs, duree_h=round(rng.uniform(2.0, 4.0), 1),
            travail_de_nuit=rng.choice([0, 1]),
            travaux="Inspection visuelle mensuelle du balisage.",
            constat=("Aucun feu hors service." if hs == 0
                     else "Un feu hors service remplace sur place."),
            niveau=niveau, motifs=motifs,
        ))
    return rapports


def rapports_complementaires(rng):
    """Remplit le reste du parc : periodicites + quelques correctives dispersees."""
    autres = [c["id"] for c in CIRCUITS
              if c["id"] not in (
                  "CIR-0003", "CIR-0009",
                  "CIR-0001", "CIR-0002", "CIR-0005", "CIR-0011",
                  "CIR-0015", "CIR-0017", "CIR-0019")]
    rapports = []
    for cid in autres:
        meta = CIRCUITS_PAR_ID[cid]
        # Deux visites espacees sur 18 mois
        for mois in (2, 11):
            jours = 20 + mois * 30 + rng.randint(0, 6)
            if jours > HORIZON_JOURS:
                continue
            hs = 1 if meta["systeme"] == "PAPI" and rng.random() < 0.2 else 0
            niveau = "info"
            motifs = ["Aucun ecart detecte par rapport aux seuils parametres."]
            if hs:
                niveau = "critique"
                motifs = ["1 feu hors service, seuil d'alerte a 1."]
            rapports.append(_rapport(
                cid, jours, "preventive", "visuel",
                technicien=rng.choice(TECHNICIENS),
                courant_a=_courant(rng),
                isolement_mohm=round(rng.uniform(110, 240), 1),
                feux_hs=hs, duree_h=round(rng.uniform(1.5, 4.0), 1),
                travail_de_nuit=rng.choice([0, 1]),
                travaux="Inspection visuelle du circuit %s." % meta["designation"],
                constat="Releve de routine.",
                niveau=niveau, motifs=motifs,
            ))
        # Une mesure d'isolement
        rapports.append(_rapport(
            cid, rng.randint(40, 400), "preventive", "isolement",
            courant_a=_courant(rng),
            isolement_mohm=round(rng.uniform(100, 220), 1),
            feux_hs=0, duree_h=4.0,
            travaux="Mesure d'isolement semestrielle.",
            constat="Conforme aux attentes contractuelles.",
            niveau="info",
        ))

    # Correctives dispersees (hors trajectoires 1 et 2)
    correctifs = [
        ("CIR-0013", 90, 11, 44.0, "critique",
         ["Isolement 44 MOhm sous le seuil de 50 MOhm."],
         "Recherche de defaut d'isolement sur la bretelle W."),
        ("CIR-0013", 280, 4, 96.0, "vigilance",
         ["4 feux hors service."],
         "Remplacement groupe d'optiques sur bretelle W."),
        ("CIR-0007", 55, 1, 170.0, "critique",
         ["1 feu hors service, seuil d'alerte a 1."],
         "Remplacement lampe PAPI cote gauche, verification alignement."),
        ("CIR-0016", 130, 2, 155.0, "vigilance",
         ["2 feux hors service."],
         "Depannage ponctuel sur rampe d'approche."),
        ("CIR-0020", 75, 3, 88.0, "vigilance",
         ["3 feux hors service, seuil d'alerte a 2."],
         "Reprise connexions barres d'arret points A/B."),
        ("CIR-0010", 200, 2, 130.0, "vigilance",
         ["2 feux hors service."],
         "Remplacement feux de seuil."),
    ]
    for cid, jours, hs, iso, niveau, motifs, travaux in correctifs:
        rapports.append(_rapport(
            cid, jours, "corrective", "visuel" if iso >= 50 else "isolement",
            technicien="Equipe nuit", courant_a=_courant(rng),
            isolement_mohm=iso, feux_hs=hs, duree_h=round(rng.uniform(2.0, 5.0), 1),
            habilitation="BR", travail_de_nuit=1, consignation=1,
            travaux=travaux,
            constat="Intervention corrective de demonstration.",
            suite="Suivi a la prochaine visite.",
            niveau=niveau, motifs=motifs,
        ))
    return rapports


def construire_historique():
    """Assemble le jeu complet, deterministe."""
    rng = random.Random(GRAINE)
    rapports = []
    rapports.extend(trajectoire_isolement_decroissant())
    rapports.extend(trajectoire_recurrence_corrective())
    rapports.extend(trajectoire_parc_sain(rng))
    rapports.extend(rapports_complementaires(rng))
    # Tri chronologique (plus ancien d'abord) pour des references stables
    rapports.sort(key=lambda r: -r["jours"])
    return rapports


# --------------------------------------------------------------------------
# Commandes
# --------------------------------------------------------------------------

def vider():
    cible = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "assistant.db")
    if os.path.exists(cible):
        os.remove(cible)
        print("Base supprimee :", cible)
    storage.initialiser()
    print("Base vide recreee.")


def charger():
    storage.initialiser()
    deja = len(storage.lister(limite=500))
    if deja:
        print("La base contient deja %d rapport(s). Utiliser --vider pour repartir a zero." % deja)
        return 0
    historique = construire_historique()
    for ligne in historique:
        rapport = dict(ligne)
        rapport["date"] = il_y_a(rapport.pop("jours"))
        rapport["note_brute"] = "Historique de demonstration."
        rapport["moteur"] = "regles"
        if isinstance(rapport.get("motifs"), list):
            rapport["motifs"] = json.dumps(rapport["motifs"], ensure_ascii=False)
        storage.enregistrer(rapport)
    print("%d rapports d'historique charges." % len(historique))
    print("Trajectoires :")
    print("  - CIR-0003 (TDZ Bruxelles) : isolement 148 -> 96 -> 42 MOhm (sous seuil).")
    print("  - CIR-0009 (barres Liege) : 4 correctives / 12 mois, dont 3 portion ouest.")
    print("  - Parc sain (7 circuits) : contraste pour la demonstration.")
    return len(historique)


def afficher_resume():
    storage.initialiser()
    rapports = storage.lister(limite=500)
    if not rapports:
        print("Aucun rapport en base.")
        return

    sites = {}
    circuits = set()
    natures = {"preventive": 0, "corrective": 0}
    controles = {}
    niveaux = {}
    for r in rapports:
        sites[r["site"]] = sites.get(r["site"], 0) + 1
        if r.get("circuit"):
            circuits.add(r["circuit"])
        natures[r.get("nature") or "?"] = natures.get(r.get("nature") or "?", 0) + 1
        controles[r.get("controle") or "?"] = controles.get(r.get("controle") or "?", 0) + 1
        niveaux[r.get("niveau") or "?"] = niveaux.get(r.get("niveau") or "?", 0) + 1

    corr_0009 = storage.correctives_12m("CIR-0009")
    iso_0003 = sorted(
        [r for r in rapports
         if r.get("circuit") == "CIR-0003" and r.get("controle") == "isolement"],
        key=lambda r: r["date"])

    print("=" * 62)
    print("  Recapitulatif de l'historique de demonstration")
    print("=" * 62)
    print("  Circuits catalogues : %d" % len(CIRCUITS))
    print("  Circuits touches    : %d" % len(circuits))
    print("  Rapports            : %d" % len(rapports))
    print("  Sites               : %d" % len(sites))
    for site in sorted(sites):
        print("    - %-12s %3d rapport(s)" % (site, sites[site]))
    print("  Natures             : preventive=%d  corrective=%d" % (
        natures.get("preventive", 0), natures.get("corrective", 0)))
    print("  Controles           : %s" % ", ".join(
        "%s=%d" % (k, controles[k]) for k in sorted(controles)))
    print("  Niveaux             : %s" % ", ".join(
        "%s=%d" % (k, niveaux[k]) for k in sorted(niveaux)))
    print("-" * 62)
    print("  Trajectoire isolement CIR-0003 :")
    for r in iso_0003:
        print("    %s  %s MOhm  (%s)" % (r["date"], r["isolement_mohm"], r["niveau"]))
    print("  Trajectoire recurrence CIR-0009 : %d correctives / 12 mois" % corr_0009)
    print("=" * 62)


if __name__ == "__main__":
    if "--vider" in sys.argv:
        vider()
    else:
        charger()
    if "--resume" in sys.argv:
        afficher_resume()
