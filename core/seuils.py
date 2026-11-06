# -*- coding: utf-8 -*-
"""Evaluation de la criticite d'une intervention au regard des seuils.

Les seuils ne sont JAMAIS codes en dur : ils viennent de la configuration,
par systeme de balisage. Une valeur reglementaire depend du contrat et de
l'exploitant, et un chiffre fige dans le code devient faux sans prevenir.
"""

NIVEAUX = {"info": 0, "vigilance": 1, "critique": 2}


def seuils_du_systeme(config, systeme):
    """Renvoie les seuils applicables, avec repli sur les valeurs par defaut."""
    seuils = (config or {}).get("seuils") or {}
    defaut = dict(seuils.get("defaut") or {})
    if systeme:
        for cle, valeurs in (seuils.get("par_systeme") or {}).items():
            if cle.lower() in systeme.lower():
                defaut.update(valeurs)
                break
    return defaut


def evaluer(donnees, config, historique_correctives=0):
    """Compare les valeurs relevees aux seuils et renvoie un verdict.

    donnees : dictionnaire issu de l'extraction.
    historique_correctives : nombre de correctives sur ce circuit en 12 mois.
    """
    seuils = seuils_du_systeme(config, donnees.get("systeme"))
    motifs = []
    niveau = "info"

    def monter(vers, motif):
        nonlocal niveau
        motifs.append(motif)
        if NIVEAUX[vers] > NIVEAUX[niveau]:
            niveau = vers

    isolement = donnees.get("isolement_mohm")
    seuil_iso = seuils.get("isolement_mohm")
    if isolement is not None and seuil_iso:
        if isolement < seuil_iso:
            monter("critique", "Isolement %.0f MOhm sous le seuil de %.0f MOhm."
                   % (isolement, seuil_iso))
        elif isolement < seuil_iso * 1.5:
            monter("vigilance", "Isolement %.0f MOhm proche du seuil de %.0f MOhm."
                   % (isolement, seuil_iso))

    courant = donnees.get("courant_a")
    nominal = seuils.get("courant_nominal_a")
    tolerance = seuils.get("courant_tolerance_a")
    if courant is not None and nominal and tolerance:
        ecart = abs(courant - nominal)
        if ecart > tolerance:
            monter("critique", "Courant %.2f A hors tolerance (%.2f A +/- %.2f A)."
                   % (courant, nominal, tolerance))

    feux_hs = donnees.get("feux_hs")
    seuil_hs = seuils.get("feux_hs_alerte")
    if feux_hs:
        if seuil_hs and feux_hs >= seuil_hs:
            monter("critique", "%d feu%s hors service, seuil d'alerte a %d."
                   % (feux_hs, "x" if feux_hs > 1 else "", seuil_hs))
        else:
            monter("vigilance", "%d feu%s hors service."
                   % (feux_hs, "x" if feux_hs > 1 else ""))

    seuil_recurrence = seuils.get("recurrence_12m", 3)
    if historique_correctives >= seuil_recurrence:
        monter("critique", "%d interventions correctives sur ce circuit en 12 mois : "
               "la cause n'a pas ete traitee." % historique_correctives)

    if donnees.get("nature") == "corrective" and not donnees.get("consignation"):
        monter("vigilance", "Consignation du circuit non mentionnee dans la note.")

    if not motifs:
        motifs.append("Aucun ecart detecte par rapport aux seuils parametres.")

    return {"niveau": niveau, "motifs": motifs, "seuils_appliques": seuils}


def doit_notifier(verdict, config):
    """Le niveau justifie-t-il une alerte ?"""
    minimum = ((config or {}).get("notifications") or {}).get("niveau_minimum", "critique")
    return NIVEAUX[verdict["niveau"]] >= NIVEAUX.get(minimum, 2)
