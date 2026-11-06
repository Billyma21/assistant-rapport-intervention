# -*- coding: utf-8 -*-
"""Persistance SQLite. Aucune dependance externe."""

import json
import os
import sqlite3
from datetime import datetime, timedelta

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RACINE, "data", "assistant.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS rapport (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT UNIQUE,
    date TEXT NOT NULL,
    site TEXT NOT NULL,
    circuit TEXT,
    systeme TEXT,
    nature TEXT,
    controle TEXT,
    technicien TEXT,
    courant_a REAL,
    isolement_mohm REAL,
    feux_hs INTEGER,
    duree_h REAL,
    travail_de_nuit INTEGER DEFAULT 0,
    consignation INTEGER DEFAULT 0,
    habilitation TEXT,
    travaux TEXT,
    constat TEXT,
    suite TEXT,
    note_brute TEXT,
    moteur TEXT,
    niveau TEXT,
    motifs TEXT,
    cree_le TEXT
);
CREATE TABLE IF NOT EXISTS alerte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rapport_id INTEGER,
    niveau TEXT,
    titre TEXT,
    corps TEXT,
    canaux TEXT,
    cree_le TEXT
);
CREATE TABLE IF NOT EXISTS journal_llm (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cree_le TEXT,
    duree_ms INTEGER,
    succes INTEGER,
    moteur TEXT,
    detail TEXT
);
"""


def connexion():
    os.makedirs(os.path.dirname(BASE), exist_ok=True)
    cnx = sqlite3.connect(BASE)
    cnx.row_factory = sqlite3.Row
    return cnx


def initialiser():
    with connexion() as cnx:
        cnx.executescript(SCHEMA)


def journaliser_llm(entree):
    """Trace un appel externe d'extraction distante."""
    entree = dict(entree)
    entree.setdefault("cree_le", datetime.now().isoformat(timespec="seconds"))
    with connexion() as cnx:
        cnx.execute(
            "INSERT INTO journal_llm (cree_le, duree_ms, succes, moteur, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (entree.get("cree_le"), entree.get("duree_ms"),
             1 if entree.get("succes") else 0,
             entree.get("moteur"), entree.get("detail")))


def lister_journal_llm(limite=50):
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM journal_llm ORDER BY id DESC LIMIT ?",
            (limite,)).fetchall()
    return [dict(l) for l in lignes]


def prochaine_reference():
    with connexion() as cnx:
        n = cnx.execute("SELECT COUNT(*) FROM rapport").fetchone()[0]
    return "RAP-%04d" % (n + 1)


CHAMPS = ["reference", "date", "site", "circuit", "systeme", "nature", "controle",
          "technicien", "courant_a", "isolement_mohm", "feux_hs", "duree_h",
          "travail_de_nuit", "consignation", "habilitation", "travaux", "constat",
          "suite", "note_brute", "moteur", "niveau", "motifs", "cree_le"]


def enregistrer(rapport):
    donnees = {c: rapport.get(c) for c in CHAMPS}
    donnees["reference"] = donnees["reference"] or prochaine_reference()
    donnees["cree_le"] = datetime.now().isoformat(timespec="seconds")
    donnees["travail_de_nuit"] = 1 if rapport.get("travail_de_nuit") else 0
    donnees["consignation"] = 1 if rapport.get("consignation") else 0
    if isinstance(donnees.get("motifs"), (list, tuple)):
        donnees["motifs"] = json.dumps(list(donnees["motifs"]), ensure_ascii=False)
    colonnes = ", ".join(CHAMPS)
    marques = ", ".join("?" for _ in CHAMPS)
    with connexion() as cnx:
        cur = cnx.execute("INSERT INTO rapport (%s) VALUES (%s)" % (colonnes, marques),
                          [donnees[c] for c in CHAMPS])
        return cur.lastrowid, donnees["reference"]


def lire(rapport_id):
    with connexion() as cnx:
        ligne = cnx.execute("SELECT * FROM rapport WHERE id = ?", (rapport_id,)).fetchone()
    return dict(ligne) if ligne else None


def lister(limite=50):
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM rapport ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(l) for l in lignes]


def correctives_12m(circuit):
    """Nombre d'interventions correctives sur ce circuit depuis 12 mois."""
    if not circuit:
        return 0
    depuis = (datetime.now() - timedelta(days=365)).date().isoformat()
    with connexion() as cnx:
        return cnx.execute(
            "SELECT COUNT(*) FROM rapport WHERE circuit = ? AND nature = 'corrective' "
            "AND date >= ?", (circuit, depuis)).fetchone()[0]


def journaliser_alerte(alerte):
    alerte = dict(alerte)
    alerte["cree_le"] = datetime.now().isoformat(timespec="seconds")
    with connexion() as cnx:
        cnx.execute(
            "INSERT INTO alerte (rapport_id, niveau, titre, corps, canaux, cree_le) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (alerte.get("rapport_id"), alerte.get("niveau"), alerte.get("titre"),
             alerte.get("corps"), alerte.get("canaux"), alerte["cree_le"]))


def lister_alertes(limite=50):
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM alerte ORDER BY id DESC LIMIT ?", (limite,)).fetchall()
    return [dict(l) for l in lignes]


def statistiques():
    with connexion() as cnx:
        total = cnx.execute("SELECT COUNT(*) FROM rapport").fetchone()[0]
        critiques = cnx.execute(
            "SELECT COUNT(*) FROM rapport WHERE niveau = 'critique'").fetchone()[0]
        vigilance = cnx.execute(
            "SELECT COUNT(*) FROM rapport WHERE niveau = 'vigilance'").fetchone()[0]
        heures = cnx.execute("SELECT COALESCE(SUM(duree_h), 0) FROM rapport").fetchone()[0]
        feux = cnx.execute("SELECT COALESCE(SUM(feux_hs), 0) FROM rapport").fetchone()[0]
        alertes = cnx.execute("SELECT COUNT(*) FROM alerte").fetchone()[0]
    return {"rapports": total, "critiques": critiques, "vigilance": vigilance,
            "heures": heures, "feux_hs": feux, "alertes": alertes}


def lister_circuit(circuit, limite=200):
    """Rapports d'un circuit, du plus recent au plus ancien."""
    if not circuit:
        return []
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM rapport WHERE circuit = ? ORDER BY date DESC, id DESC LIMIT ?",
            (circuit, limite)).fetchall()
    return [dict(l) for l in lignes]


def lister_site(site, limite=200):
    if not site:
        return []
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM rapport WHERE site = ? ORDER BY date DESC, id DESC LIMIT ?",
            (site, limite)).fetchall()
    return [dict(l) for l in lignes]


def grouper_par_circuit(limite=2000):
    """Dict circuit -> liste chronologique de rapports."""
    with connexion() as cnx:
        lignes = cnx.execute(
            "SELECT * FROM rapport ORDER BY date ASC, id ASC LIMIT ?",
            (limite,)).fetchall()
    groupes = {}
    for ligne in lignes:
        r = dict(ligne)
        cle = r.get("circuit") or "(sans circuit)"
        groupes.setdefault(cle, []).append(r)
    return groupes


def alertes_depuis(jours=30):
    """Nombre d'alertes journalisees sur la periode."""
    depuis = (datetime.now() - timedelta(days=jours)).isoformat(timespec="seconds")
    with connexion() as cnx:
        return cnx.execute(
            "SELECT COUNT(*) FROM alerte WHERE cree_le >= ?", (depuis,)).fetchone()[0]


def sites_synthese():
    """Une ligne par site : circuits, feux HS (dernier releve), alertes, derniere date."""
    groupes = grouper_par_circuit()
    par_site = {}
    for circuit, rapports in groupes.items():
        if not rapports:
            continue
        dernier = max(rapports, key=lambda r: (r.get("date") or "", r.get("id") or 0))
        site = dernier.get("site") or "(sans site)"
        slot = par_site.setdefault(site, {
            "site": site,
            "circuits": set(),
            "feux_hs": 0,
            "en_alerte": 0,
            "derniere": None,
        })
        slot["circuits"].add(circuit)
        slot["feux_hs"] += int(dernier.get("feux_hs") or 0)
        if dernier.get("niveau") in ("critique", "vigilance"):
            slot["en_alerte"] += 1
        d = dernier.get("date")
        if d and (slot["derniere"] is None or d > slot["derniere"]):
            slot["derniere"] = d
    resultat = []
    for site, slot in par_site.items():
        resultat.append({
            "site": site,
            "nb_circuits": len(slot["circuits"]),
            "feux_hs": slot["feux_hs"],
            "en_alerte": slot["en_alerte"],
            "derniere": slot["derniere"],
        })
    resultat.sort(key=lambda s: s["site"])
    return resultat
