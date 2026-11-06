# -*- coding: utf-8 -*-
"""Envoi des alertes.

Trois canaux, cumulables :
  - journal   : toujours actif, trace tout en base, meme hors ligne ;
  - push      : notification sur telephone via un service HTTP de type ntfy ;
  - courriel  : SMTP classique.

Chaque canal est independant : l'echec de l'un n'empeche pas les autres, et
le journal garde la trace de ce qui est parti et de ce qui a echoue.
"""

import json
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

TITRES = {
    "critique": "ALERTE CRITIQUE",
    "vigilance": "Point de vigilance",
    "info": "Information",
}


def composer(rapport, verdict):
    """Construit le titre et le corps du message d'alerte."""
    titre = "%s - %s" % (TITRES.get(verdict["niveau"], "Alerte"), rapport["site"])
    lignes = [
        "Site      : %s" % rapport["site"],
        "Circuit   : %s" % (rapport.get("circuit") or "non precise"),
        "Systeme   : %s" % (rapport.get("systeme") or "non precise"),
        "Technicien: %s" % (rapport.get("technicien") or "non precise"),
        "Date      : %s" % rapport["date"],
        "",
        "Motifs :",
    ]
    lignes += ["  - " + m for m in verdict["motifs"]]
    mesures = []
    if rapport.get("courant_a") is not None:
        mesures.append("courant %.2f A" % rapport["courant_a"])
    if rapport.get("isolement_mohm") is not None:
        mesures.append("isolement %.0f MOhm" % rapport["isolement_mohm"])
    if rapport.get("feux_hs") is not None:
        mesures.append("%d feux hors service" % rapport["feux_hs"])
    if mesures:
        lignes += ["", "Releves : " + ", ".join(mesures)]
    if rapport.get("suite"):
        lignes += ["", "Suite a donner : " + rapport["suite"]]
    return titre, "\n".join(lignes)


def envoyer_push(config, titre, corps, niveau):
    """Notification telephone via un service HTTP de type ntfy."""
    push = ((config or {}).get("notifications") or {}).get("push") or {}
    if not push.get("actif") or not push.get("topic"):
        return "inactif"
    url = push.get("serveur", "https://ntfy.sh").rstrip("/") + "/" + push["topic"]
    entetes = {
        "Title": titre.encode("utf-8"),
        "Priority": {"critique": "urgent", "vigilance": "high"}.get(niveau, "default"),
        "Tags": {"critique": "rotating_light", "vigilance": "warning"}.get(niveau, "information_source"),
    }
    try:
        requete = urllib.request.Request(url, data=corps.encode("utf-8"),
                                         headers=entetes, method="POST")
        with urllib.request.urlopen(requete, timeout=8) as rep:
            rep.read()
        return "envoye"
    except Exception as err:
        return "echec: %s" % err


def envoyer_courriel(config, titre, corps):
    """Envoi SMTP. Toute erreur est renvoyee en texte, jamais levee."""
    mail = ((config or {}).get("notifications") or {}).get("courriel") or {}
    if not mail.get("actif") or not mail.get("destinataires"):
        return "inactif"
    message = EmailMessage()
    message["Subject"] = titre
    message["From"] = mail.get("expediteur", "assistant@local")
    message["To"] = ", ".join(mail["destinataires"])
    message.set_content(corps)
    try:
        if mail.get("ssl"):
            serveur = smtplib.SMTP_SSL(mail["hote"], int(mail.get("port", 465)),
                                       context=ssl.create_default_context(), timeout=12)
        else:
            serveur = smtplib.SMTP(mail["hote"], int(mail.get("port", 587)), timeout=12)
            serveur.starttls(context=ssl.create_default_context())
        with serveur:
            if mail.get("utilisateur"):
                serveur.login(mail["utilisateur"], mail.get("mot_de_passe", ""))
            serveur.send_message(message)
        return "envoye"
    except Exception as err:
        return "echec: %s" % err


def alerter(config, rapport, verdict, journaliser):
    """Compose puis diffuse l'alerte sur les canaux actifs."""
    titre, corps = composer(rapport, verdict)
    etats = {
        "push": envoyer_push(config, titre, corps, verdict["niveau"]),
        "courriel": envoyer_courriel(config, titre, corps),
    }
    journaliser({
        "rapport_id": rapport.get("id"),
        "niveau": verdict["niveau"],
        "titre": titre,
        "corps": corps,
        "canaux": json.dumps(etats, ensure_ascii=False),
    })
    return titre, corps, etats
