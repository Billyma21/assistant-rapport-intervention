#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resume hebdomadaire des interventions et des risques.

    python3 resume.py

Produit un texte (interventions de la semaine, alertes emises, circuits
entres / sortis d'alerte, top 3 des risques) puis le diffuse via les canaux
configures. Le journal interne est toujours alimente, meme hors ligne.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)

from core import notify, risque, storage  # noqa: E402


def charger_config():
    for nom in ("config.json", "config.example.json"):
        chemin = os.path.join(RACINE, nom)
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8") as f:
                return json.load(f)
    return {}


def _en_alerte(niveau):
    return niveau in ("critique", "vigilance")


def _dernier_avant(rapports, avant_iso):
    """Dernier rapport strictement anterieur a avant_iso."""
    candidats = [r for r in rapports if (r.get("date") or "") < avant_iso]
    if not candidats:
        return None
    return max(candidats, key=lambda r: (r.get("date") or "", r.get("id") or 0))


def _dernier(rapports):
    if not rapports:
        return None
    return max(rapports, key=lambda r: (r.get("date") or "", r.get("id") or 0))


def construire_resume(config, aujourd_hui=None):
    """Assemble le texte du resume pour les 7 derniers jours."""
    auj = aujourd_hui or date.today()
    debut = auj - timedelta(days=6)
    debut_iso, fin_iso = debut.isoformat(), auj.isoformat()

    storage.initialiser()
    groupes = storage.grouper_par_circuit()
    interventions = []
    for circuit, rapports in groupes.items():
        for r in rapports:
            d = (r.get("date") or "")[:10]
            if debut_iso <= d <= fin_iso:
                interventions.append(r)
    interventions.sort(key=lambda r: (r.get("date") or "", r.get("id") or 0))

    # Alertes journalisees sur la periode (cree_le)
    depuis = datetime.combine(debut, datetime.min.time()).isoformat(timespec="seconds")
    alertes = [a for a in storage.lister_alertes(500)
               if (a.get("cree_le") or "") >= depuis]

    entres, sortis = [], []
    for circuit, rapports in groupes.items():
        avant = _dernier_avant(rapports, debut_iso)
        apres = _dernier(rapports)
        if not apres:
            continue
        # Ne considere un changement que si une intervention a eu lieu cette semaine
        dans_semaine = any(
            debut_iso <= (r.get("date") or "")[:10] <= fin_iso for r in rapports)
        if not dans_semaine:
            continue
        etat_avant = _en_alerte((avant or {}).get("niveau"))
        etat_apres = _en_alerte(apres.get("niveau"))
        if not etat_avant and etat_apres:
            entres.append(circuit)
        elif etat_avant and not etat_apres:
            sortis.append(circuit)

    scores = risque.classer_circuits(
        groupes, config, correctives_fn=storage.correctives_12m)
    top3 = scores[:3]

    lignes = [
        "Resume hebdomadaire - %s au %s" % (debut_iso, fin_iso),
        "=" * 56,
        "",
        "Interventions realisees : %d" % len(interventions),
    ]
    for r in interventions:
        lignes.append(
            "  - %s  %s  %s  %s  [%s]" % (
                r.get("date"), r.get("reference"), r.get("site"),
                r.get("circuit"), r.get("niveau")))

    lignes += ["", "Alertes emises : %d" % len(alertes)]
    for a in alertes[:20]:
        lignes.append("  - %s  %s" % (a.get("cree_le"), a.get("titre")))

    lignes += ["", "Circuits entres en alerte : %d" % len(entres)]
    for c in sorted(entres):
        lignes.append("  - %s" % c)
    lignes += ["", "Circuits sortis d'alerte : %d" % len(sortis)]
    for c in sorted(sortis):
        lignes.append("  - %s" % c)

    lignes += ["", "Top 3 des risques :"]
    if not top3:
        lignes.append("  (aucun circuit)")
    for s in top3:
        site = (s.get("dernier") or {}).get("site") or "?"
        lignes.append(
            "  - %s (score %d, %s) - %s" % (
                s["circuit"], s["score"], site, s["motif_dominant"]))

    lignes += ["", "Genere le %s." % datetime.now().isoformat(timespec="seconds")]
    texte = "\n".join(lignes)
    return {
        "debut": debut_iso,
        "fin": fin_iso,
        "texte": texte,
        "nb_interventions": len(interventions),
        "nb_alertes": len(alertes),
        "entres": entres,
        "sortis": sortis,
        "top3": top3,
    }


def diffuser(config, resume):
    """Envoie le resume sur les canaux actifs et journalise toujours."""
    titre = "Resume hebdomadaire %s → %s" % (resume["debut"], resume["fin"])
    corps = resume["texte"]
    etats = {
        "push": notify.envoyer_push(config, titre, corps, "info"),
        "courriel": notify.envoyer_courriel(config, titre, corps),
    }
    storage.journaliser_alerte({
        "rapport_id": None,
        "niveau": "info",
        "titre": titre,
        "corps": corps,
        "canaux": json.dumps(etats, ensure_ascii=False),
    })
    return etats


def main():
    config = charger_config()
    resume = construire_resume(config)
    print(resume["texte"])
    print()
    etats = diffuser(config, resume)
    print("Diffusion : push=%s, courriel=%s (journalise)." % (
        etats["push"], etats["courriel"]))


if __name__ == "__main__":
    main()
