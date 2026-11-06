# -*- coding: utf-8 -*-
"""Extraction structuree d'une note de terrain.

Deux moteurs :
  1. un moteur de regles, toujours disponible, sans reseau ni cle d'API ;
  2. un moteur LLM optionnel, active seulement si une cle est configuree.

Le moteur LLM ne remplace jamais le moteur de regles : il le complete, et
toute erreur retombe silencieusement sur les regles. Un processus
d'exploitation ne doit pas dependre de la disponibilite d'une API externe.
"""

import json
import re
import unicodedata
from datetime import date as _date

SYSTEMES = {
    "axe de piste": ["axe de piste", "axe piste", "centerline", "axe de la piste"],
    "bord de piste": ["bord de piste", "bord piste", "edge"],
    "seuil": ["seuil", "threshold"],
    "extremite de piste": ["extremite", "extremite de piste", "fin de piste"],
    "zone de toucher des roues (TDZ)": ["tdz", "toucher des roues", "touchdown"],
    "rampe d'approche": ["rampe d'approche", "approche", "als"],
    "PAPI": ["papi"],
    "axe de voie de circulation": ["axe de voie", "axe taxiway", "taxiway axe"],
    "bord de voie de circulation": ["bord de voie", "bord taxiway", "taxiway bord"],
    "barres d'arret": ["barre d'arret", "barres d'arret", "stop bar", "point d'attente"],
    "balisage d'obstacles": ["obstacle", "obstacles", "mat", "balisage obstacle"],
}

NATURES = {
    "corrective": ["depannage", "panne", "defaut", "hors service", "incident",
                   "urgence", "remplacement", "reparation", "court-circuit"],
    "preventive": ["visite", "periodique", "preventive", "controle", "inspection",
                   "campagne", "trimestrielle", "semestrielle", "annuelle"],
}

# L'ordre compte : un libelle explicite l'emporte sur la simple mention d'une
# mesure d'isolement, qui peut figurer dans n'importe quel compte rendu.
CONTROLES = [
    ("photometrie", ["photometrie", "photometrique", "intensite lumineuse", "candela"]),
    ("electrique", ["controle electrique", "verification electrique", "parafoudre",
                    "onduleur", "coffret de commande", "continuite des circuits"]),
    ("visuel", ["inspection visuelle", "controle visuel", "tournee d'inspection"]),
    ("isolement", ["mesure d'isolement", "isolement", "megohm", "mohm",
                   "megohmmetre", "mega ohm"]),
]

# Mots qui signalent clairement un depannage, independamment du reste.
CORRECTIF_FORT = ["depannage", "panne", "defaut", "incident", "urgence",
                  "reparation", "court-circuit", "hors service signale",
                  "appel de l'exploitant", "signale par la tour"]

# Tournures qui annulent un comptage de feux hors service.
NEGATIONS = ["aucun feu", "aucune lampe", "pas de feu", "aucun defaut",
             "zero feu", "aucun point", "rien a signaler"]

MOTS_SUITE = ["a commander", "a prevoir", "a planifier", "a remplacer", "a revoir",
              "retour", "repasser", "prochaine visite", "a surveiller", "commander",
              "devis", "a reprendre", "necessaire"]

MOTS_CONSTAT = ["constat", "anomalie", "defaut", "hors service", "baisse", "chute",
                "degradation", "corrosion", "infiltration", "oxydation", "fissure",
                "casse", "usure", "sous le seuil"]

CHIFFRES = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
    "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
    "quinze": 15, "vingt": 20,
}

MOIS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}

# Feux hors service : abréviations et tournures de terrain courantes.
MARQUEURS_HS = r"(?:hs\b|hors service|h\.s\.|eteints?|morts?)"


def sans_accents(texte):
    """Minuscule sans accents, pour comparer des mots-cles de facon robuste."""
    decompose = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def _nombre(fragment):
    """Convertit '6,52' ou 'sept' en float. Renvoie None si impossible."""
    fragment = fragment.strip().replace(",", ".")
    try:
        return float(fragment)
    except ValueError:
        return float(CHIFFRES[fragment]) if fragment in CHIFFRES else None


def _annee_complete(annee):
    """Normalise 26 -> 2026, 2026 -> 2026. None si absente."""
    if annee is None:
        return None
    annee = int(annee)
    if annee < 100:
        return 2000 + annee
    return annee


def _date_iso(jour, mois, annee=None):
    """Construit une date ISO. Annee absente : annee civile courante."""
    try:
        jour, mois = int(jour), int(mois)
        if annee is None:
            annee = _date.today().year
        else:
            annee = _annee_complete(annee)
        return _date(annee, mois, jour).isoformat()
    except (TypeError, ValueError):
        return None


def extraire_date(plat):
    """Extrait une date de terrain si elle est reconnaissable, sinon None."""
    # 04/11/2026, 04-11-2026, 4/11
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", plat)
    if m:
        return _date_iso(m.group(1), m.group(2), m.group(3))

    # 4 novembre, 4 novembre 2026
    mois_alt = "|".join(MOIS)
    m = re.search(r"\b(\d{1,2})\s+(" + mois_alt + r")(?:\s+(\d{4}))?\b", plat)
    if m:
        return _date_iso(m.group(1), MOIS[m.group(2)], m.group(3))

    # le 04-11-2026 deja couvert ; forme « en novembre 2026 » ignoree (pas de jour)
    return None


def _phrases(texte):
    """Decoupe la note en phrases exploitables.

    Une note de terrain est saisie au fil de l'eau : une phrase peut courir sur
    deux lignes. On recolle donc les lignes qui ne se terminent pas par une
    ponctuation forte avant de decouper, sinon une phrase coupee se retrouve
    repartie entre deux rubriques du rapport.
    """
    lignes = [l.strip(" -•\t") for l in texte.splitlines()]
    recolle = []
    for ligne in lignes:
        if not ligne:
            continue
        if recolle and not re.search(r"[.!?;:]$", recolle[-1]):
            # La ligne precedente n'etait pas terminee : on la prolonge,
            # sauf si cette ligne demarre une nouvelle rubrique explicite.
            if not re.match(r"(?i)^(constat|suite|a faire|travaux|releve|mesure)\b", ligne):
                recolle[-1] = recolle[-1] + " " + ligne
                continue
        recolle.append(ligne)

    brut = []
    for bloc in recolle:
        brut.extend(re.split(r"(?<=[.!?;])\s+", bloc))
    return [p.strip(" -•\t") for p in brut if len(p.strip()) > 3]


# --------------------------------------------------------------------------
# Moteur de regles
# --------------------------------------------------------------------------

def extraire_par_regles(note):
    """Analyse la note et renvoie un dictionnaire structure."""
    if note is None:
        note = ""
    note = str(note)
    plat = sans_accents(note)
    res = {
        "moteur": "regles",
        "nature": None,
        "systeme": None,
        "controle": None,
        "courant_a": None,
        "isolement_mohm": None,
        "feux_hs": None,
        "duree_h": None,
        "date": None,
        "travail_de_nuit": False,
        "consignation": False,
        "habilitation": None,
        "travaux": "",
        "constat": "",
        "suite": "",
    }

    for systeme, mots in SYSTEMES.items():
        if any(m in plat for m in mots):
            res["systeme"] = systeme
            break

    for controle, mots in CONTROLES:
        if any(m in plat for m in mots):
            res["controle"] = controle
            break

    # Courant : "6,52 A", "courant de 6.5 ampere"
    m = re.search(r"(\d+[.,]?\d*)\s*(?:a\b|amp)", plat)
    if m:
        res["courant_a"] = _nombre(m.group(1))

    # Isolement : "38 MOhm", "isolement de 38"
    # plat est en minuscules : Ω devient ω via str.lower().
    m = re.search(r"(\d+[.,]?\d*)\s*(?:mohm|m ohm|megohm|mega ?ohm|m[ωΩ])", plat)
    if not m:
        m = re.search(r"isolement[^\d]{0,15}(\d+[.,]?\d*)", plat)
    if m:
        res["isolement_mohm"] = _nombre(m.group(1))

    # Feux hors service : "7 feux hors service", "sept feux hs", "3 hs",
    # "feux eteins", "feux morts".
    # Les bornes de mots evitent de lire "un" dans "aucun".
    if any(n in plat for n in NEGATIONS):
        res["feux_hs"] = 0
    else:
        motif_nb = r"\b(\d+|" + "|".join(CHIFFRES) + r")\b"
        m = re.search(
            motif_nb + r"\s*(?:feux?|lampes?|optiques?|points?)?\s*" + MARQUEURS_HS,
            plat)
        if not m:
            m = re.search(MARQUEURS_HS + r"[^\d]{0,12}" + motif_nb, plat)
        if m:
            valeur = _nombre(m.group(1))
            if valeur is not None:
                res["feux_hs"] = int(valeur)

    res["date"] = extraire_date(plat)

    # Duree : "4h", "4 heures", "de 22h a 02h"
    m = re.search(r"(?:de\s*)?(\d{1,2})\s*h(?:\d{2})?\s*(?:a|jusqu'a)\s*(\d{1,2})\s*h", plat)
    if m:
        debut, fin = int(m.group(1)), int(m.group(2))
        res["duree_h"] = float((fin - debut) % 24)
    else:
        m = re.search(r"(\d+[.,]?\d*)\s*(?:h\b|heures?)", plat)
        if m:
            res["duree_h"] = _nombre(m.group(1))

    if any(m in plat for m in ["nuit", "nocturne", "hors trafic", "22h", "23h", "02h", "03h"]):
        res["travail_de_nuit"] = True
    if any(m in plat for m in ["consign", "mise hors tension", "hors tension"]):
        res["consignation"] = True

    m = re.search(r"\b(b[12]v|br|bc|h[012]v)\b", plat)
    if m:
        res["habilitation"] = m.group(1).upper()

    # Repartition des phrases dans les trois rubriques du rapport.
    travaux, constat, suite = [], [], []
    for phrase in _phrases(note):
        p = sans_accents(phrase)
        if any(mot in p for mot in MOTS_SUITE):
            suite.append(phrase)
        elif any(mot in p for mot in MOTS_CONSTAT):
            constat.append(phrase)
        else:
            travaux.append(phrase)

    # Nature : un mot de depannage l'emporte ; sinon un libelle de visite ;
    # sinon la presence de feux hors service tranche.
    preventif = any(m in plat for m in NATURES["preventive"])
    correctif = any(m in plat for m in CORRECTIF_FORT)
    if correctif:
        res["nature"] = "corrective"
    elif preventif:
        res["nature"] = "preventive"
    elif res["feux_hs"]:
        res["nature"] = "corrective"

    res["travaux"] = " ".join(travaux).strip()
    res["constat"] = " ".join(constat).strip()
    res["suite"] = " ".join(suite).strip()
    return res


# --------------------------------------------------------------------------
# Moteur LLM optionnel
# --------------------------------------------------------------------------

CLES_SCHEMA = (
    "nature", "systeme", "controle", "courant_a", "isolement_mohm", "feux_hs",
    "duree_h", "travail_de_nuit", "consignation", "habilitation",
    "travaux", "constat", "suite",
)

NATURES_OK = {None, "corrective", "preventive"}
CONTROLES_OK = {None, "isolement", "visuel", "electrique", "photometrie"}

GABARIT = """Tu analyses une note de terrain redigee par un technicien de
balisage lumineux aeronautique.

Regles STRICTES :
1. Reponds UNIQUEMENT par un objet JSON valide, sans texte autour, sans markdown.
2. Utilise EXACTEMENT ces cles (toutes obligatoires) :
   nature, systeme, controle, courant_a, isolement_mohm, feux_hs, duree_h,
   travail_de_nuit, consignation, habilitation, travaux, constat, suite.
3. Types autorises :
   - nature : "corrective" | "preventive" | null
   - controle : "isolement" | "visuel" | "electrique" | "photometrie" | null
   - systeme, habilitation : texte | null
   - courant_a, isolement_mohm, duree_h : nombre | null
   - feux_hs : entier | null
   - travail_de_nuit, consignation : booleen
   - travaux, constat, suite : texte (chaine vide si rien)
4. N'invente AUCUNE valeur absente de la note. Prefere null plutot que de
   deviner. Ne complete pas une mesure manquante.
5. travaux = ce qui a ete fait ; constat = anomalies ; suite = a faire.

NOTE :
"""


def llm_autorise(config):
    """True seulement si la config autorise explicitement l'envoi et fournit une cle."""
    llm = (config or {}).get("llm") or {}
    return bool(
        llm.get("autoriser_envoi")
        and llm.get("api_key")
        and llm.get("endpoint")
        and llm.get("model")
    )


def valider_schema_llm(donnees):
    """Verifie la conformite au schema. Renvoie (ok, liste_erreurs)."""
    erreurs = []
    if not isinstance(donnees, dict):
        return False, ["reponse non objet JSON"]
    for cle in CLES_SCHEMA:
        if cle not in donnees:
            erreurs.append("cle manquante : %s" % cle)
    for cle in donnees:
        if cle not in CLES_SCHEMA and cle != "moteur":
            erreurs.append("cle inconnue : %s" % cle)

    nature = donnees.get("nature")
    if nature not in NATURES_OK:
        erreurs.append("nature invalide : %r" % nature)

    controle = donnees.get("controle")
    if controle not in CONTROLES_OK:
        erreurs.append("controle invalide : %r" % controle)

    for cle in ("courant_a", "isolement_mohm", "duree_h"):
        v = donnees.get(cle)
        if v is not None and not isinstance(v, (int, float)):
            erreurs.append("%s doit etre nombre|null" % cle)

    feux = donnees.get("feux_hs")
    if feux is not None and not isinstance(feux, int):
        # Accepte 3.0 issu de JSON number
        if isinstance(feux, float) and feux == int(feux):
            donnees["feux_hs"] = int(feux)
        else:
            erreurs.append("feux_hs doit etre entier|null")

    for cle in ("travail_de_nuit", "consignation"):
        if not isinstance(donnees.get(cle), bool):
            erreurs.append("%s doit etre booleen" % cle)

    for cle in ("travaux", "constat", "suite"):
        if donnees.get(cle) is None:
            donnees[cle] = ""
        elif not isinstance(donnees.get(cle), str):
            erreurs.append("%s doit etre texte" % cle)

    for cle in ("systeme", "habilitation"):
        v = donnees.get(cle)
        if v is not None and not isinstance(v, str):
            erreurs.append("%s doit etre texte|null" % cle)

    return (len(erreurs) == 0), erreurs


def _journaliser_appel(config, duree_ms, succes, moteur, detail):
    """Ecrit dans le journal LLM si le stockage est disponible."""
    try:
        from core import storage
        storage.journaliser_llm({
            "duree_ms": int(duree_ms),
            "succes": bool(succes),
            "moteur": moteur,
            "detail": detail,
        })
    except Exception:
        pass


def extraire_par_llm(note, config):
    """Appelle un modele de langage si la configuration l'autorise explicitement.

    Renvoie (donnees|None, message). En cas d'echec ou d'ecart de schema,
    donnees est None et le moteur de regles doit faire foi.
    """
    import time
    import urllib.request

    llm = (config or {}).get("llm") or {}
    modele = llm.get("model") or "llm"

    if not llm_autorise(config):
        return None, "Envoi au modele non autorise (autoriser_envoi / cle absents)."

    debut = time.monotonic()
    try:
        corps = json.dumps({
            "model": modele,
            "max_tokens": 900,
            "messages": [{"role": "user", "content": GABARIT + (note or "")}],
        }).encode("utf-8")

        entetes = {"content-type": "application/json"}
        url = llm["endpoint"]
        if "anthropic" in url:
            entetes["x-api-key"] = llm["api_key"]
            entetes["anthropic-version"] = "2023-06-01"
        else:
            entetes["authorization"] = "Bearer " + llm["api_key"]

        requete = urllib.request.Request(url, data=corps, headers=entetes, method="POST")
        with urllib.request.urlopen(requete, timeout=float(llm.get("timeout", 20))) as rep:
            charge = json.loads(rep.read().decode("utf-8"))

        if "content" in charge:
            texte = charge["content"][0]["text"]
        else:
            texte = charge["choices"][0]["message"]["content"]
        i, j = texte.find("{"), texte.rfind("}")
        if i < 0 or j < 0:
            raise ValueError("pas d'objet JSON dans la reponse")
        donnees = json.loads(texte[i:j + 1])
        ok, erreurs = valider_schema_llm(donnees)
        duree = (time.monotonic() - debut) * 1000
        if not ok:
            _journaliser_appel(config, duree, False, modele,
                               "schema invalide : " + "; ".join(erreurs))
            return None, (
                "Reponse du modele non conforme au schema (%s). "
                "Retour au moteur de regles." % "; ".join(erreurs[:3]))
        donnees["moteur"] = "llm"
        _journaliser_appel(config, duree, True, modele, "extraction ok")
        return donnees, None
    except Exception as err:
        duree = (time.monotonic() - debut) * 1000
        _journaliser_appel(config, duree, False, modele, "echec : %s" % err)
        return None, (
            "Echec de l'appel au modele (%s). Retour au moteur de regles." % err)


def comparer_moteurs(note, config):
    """Execute regles + LLM et calcule les ecarts champ par champ.

    Le verdict metier doit toujours s'appuyer sur les regles, pas sur le LLM.
    """
    regles = extraire_par_regles(note)
    llm, message = extraire_par_llm(note, config)
    ecarts = []
    if llm:
        for cle in CLES_SCHEMA:
            a, b = regles.get(cle), llm.get(cle)
            if _valeurs_differentes(a, b):
                ecarts.append({"champ": cle, "regles": a, "llm": b})
    return {
        "regles": regles,
        "llm": llm,
        "ecarts": ecarts,
        "message": message,
    }


def _valeurs_differentes(a, b):
    if a == b:
        return False
    if (a is None or a == "") and (b is None or b == ""):
        return False
    try:
        if isinstance(a, (int, float)) or isinstance(b, (int, float)):
            if a is None or b is None:
                return True
            return abs(float(a) - float(b)) > 0.001
    except (TypeError, ValueError):
        pass
    return True


def analyser(note, config=None):
    """Point d'entree metier : moteur de regles uniquement (deterministe).

    Le LLM n'est jamais appele ici : la comparaison est une action explicite
    (voir comparer_moteurs), et aucune donnee ne part sans autoriser_envoi.
    """
    try:
        return extraire_par_regles(note if note is not None else "")
    except Exception:
        return extraire_par_regles(note if isinstance(note, str) else "")
