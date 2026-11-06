#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assistant de rapport d'intervention — serveur HTTP.

Bibliotheque standard uniquement : aucune installation, aucune dependance,
aucun acces reseau necessaire pour fonctionner.

    python3 app.py            puis http://localhost:8000
"""

import json
import os
import sys
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

RACINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)

from core import export, extraction, notify, risque, seuils, storage  # noqa: E402
from web import views                                                 # noqa: E402
import historique as parc                                             # noqa: E402

PORT = int(os.environ.get("PORT", "8000"))
CONFIG = {}


def charger_config():
    """config.json s'il existe, sinon config.example.json."""
    global CONFIG
    for nom in ("config.json", "config.example.json"):
        chemin = os.path.join(RACINE, nom)
        if os.path.exists(chemin):
            with open(chemin, encoding="utf-8") as f:
                CONFIG = json.load(f)
            return nom
    CONFIG = {}
    return None


def charger_exemples():
    dossier = os.path.join(RACINE, "exemples")
    if not os.path.isdir(dossier):
        return {}
    exemples = {}
    for nom in sorted(os.listdir(dossier)):
        if nom.endswith(".txt"):
            with open(os.path.join(dossier, nom), encoding="utf-8") as f:
                exemples[nom[:-4].replace("_", " ")] = f.read().strip()
    return exemples


EXEMPLES = {}


def _premier(formulaire, cle, defaut=""):
    return (formulaire.get(cle) or [defaut])[0]


def _nombre(valeur):
    if valeur in (None, "", "None"):
        return None
    try:
        return float(str(valeur).replace(",", "."))
    except ValueError:
        return None


def _meta_circuit(circuit):
    return (parc.CIRCUITS_PAR_ID or {}).get(circuit)


def _points_courbe(rapports, releves):
    """Associe a chaque releve d'isolement le niveau du rapport le plus proche."""
    points = []
    for d, v in releves:
        niveau = "info"
        for r in rapports:
            if r.get("date") != d.isoformat():
                continue
            iso = r.get("isolement_mohm")
            if iso is None:
                continue
            if abs(float(iso) - float(v)) < 0.05:
                niveau = r.get("niveau") or "info"
                break
        points.append((d.isoformat(), v, niveau))
    return points


def _tableau_de_bord():
    """Assemble les donnees du tableau de bord P1."""
    groupes = storage.grouper_par_circuit()
    scores = risque.classer_circuits(
        groupes, CONFIG, correctives_fn=storage.correctives_12m)

    circuits_alerte = 0
    feux_courants = 0
    for s in scores:
        d = s.get("dernier") or {}
        feux_courants += int(d.get("feux_hs") or 0)
        if d.get("niveau") in ("critique", "vigilance"):
            circuits_alerte += 1

    kpis = [
        (len(scores), "Circuits suivis"),
        (feux_courants, "Feux HS cumulés"),
        (circuits_alerte, "Circuits en alerte"),
        (storage.alertes_depuis(30), "Alertes 30 jours"),
    ]

    priorites = []
    for s in scores[:5]:
        d = s.get("dernier") or {}
        priorites.append({
            "circuit": s["circuit"],
            "score": s["score"],
            "site": d.get("site"),
            "motif_dominant": s["motif_dominant"],
        })

    courbe_html = '<p class="muted">Aucun circuit dégradé à afficher.</p>'
    if scores:
        pire = scores[0]
        seuil = None
        if pire.get("dernier"):
            seuil = seuils.seuils_du_systeme(
                CONFIG, pire["dernier"].get("systeme")).get("isolement_mohm")
        points = _points_courbe(groupes.get(pire["circuit"], []), pire.get("releves") or [])
        if not points and pire.get("dernier"):
            der = pire["dernier"]
            if der.get("isolement_mohm") is not None:
                points = [(der.get("date"), der["isolement_mohm"], der.get("niveau"))]
        courbe_html = (
            '<p class="muted" style="margin:0 0 6px">%s — score %d</p>%s%s' % (
                views.e(pire["circuit"]), pire["score"],
                views.courbe_isolement_svg(points, seuil=seuil, largeur=520, hauteur=180),
                views.bloc_projection(pire.get("projection") or {}))
        )

    return kpis, priorites, courbe_html, storage.lister(5)


class Handler(BaseHTTPRequestHandler):
    server_version = "AssistantIntervention/1.0"

    # ---------------------------------------------------------------- utils
    def repondre(self, corps, code=200, type_mime="text/html; charset=utf-8",
                 fichier=None):
        if isinstance(corps, bytes):
            donnees = corps
        else:
            donnees = corps.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", type_mime)
        self.send_header("Content-Length", str(len(donnees)))
        if fichier:
            self.send_header(
                "Content-Disposition", 'attachment; filename="%s"' % fichier)
        self.end_headers()
        self.wfile.write(donnees)

    def rediriger(self, vers):
        self.send_response(303)
        self.send_header("Location", vers)
        self.end_headers()

    def lire_formulaire(self):
        taille = int(self.headers.get("Content-Length") or 0)
        brut = self.rfile.read(taille).decode("utf-8")
        return parse_qs(brut, keep_blank_values=True)

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    # ------------------------------------------------------------------ GET
    def do_GET(self):
        url = urlparse(self.path)
        chemin, params = url.path, parse_qs(url.query)

        if chemin == "/":
            kpis, priorites, courbe, derniers = _tableau_de_bord()
            return self.repondre(views.accueil(kpis, priorites, courbe, derniers))

        if chemin == "/nouveau":
            page = views.formulaire(sorted(EXEMPLES))
            choisi = _premier(params, "exemple")
            if choisi in EXEMPLES:
                page = page.replace(
                    'placeholder="Intervention de nuit', 'data-ph="x"').replace(
                    "</textarea>", views.e(EXEMPLES[choisi]) + "</textarea>")
            return self.repondre(page)

        if chemin == "/rapports":
            return self.repondre(views.liste_rapports(storage.lister(200)))

        if chemin == "/alertes":
            return self.repondre(views.liste_alertes(storage.lister_alertes(100)))

        if chemin == "/config":
            return self.repondre(views.config_page(
                CONFIG, storage.lister_journal_llm(30)))

        if chemin == "/sites":
            return self.repondre(views.sites_page(storage.sites_synthese()))

        if chemin.startswith("/site/"):
            nom = unquote(chemin[len("/site/"):]).strip()
            if not nom:
                return self.repondre("Site invalide", 400, "text/plain; charset=utf-8")
            rapports = storage.lister_site(nom)
            if not rapports:
                return self.repondre("Site introuvable", 404, "text/plain; charset=utf-8")
            groupes = {}
            for r in rapports:
                groupes.setdefault(r.get("circuit") or "(sans circuit)", []).append(r)
            scores = risque.classer_circuits(
                groupes, CONFIG, correctives_fn=storage.correctives_12m)
            return self.repondre(views.site_page(nom, scores, rapports))

        if chemin.startswith("/circuit/"):
            ref = unquote(chemin[len("/circuit/"):]).strip()
            if not ref:
                return self.repondre("Circuit invalide", 400, "text/plain; charset=utf-8")
            rapports = storage.lister_circuit(ref)
            if not rapports:
                return self.repondre("Circuit introuvable", 404, "text/plain; charset=utf-8")
            # lister_circuit est DESC : le score attend une liste quelconque
            score = risque.scorer_circuit(
                ref, list(reversed(rapports)), CONFIG,
                storage.correctives_12m(ref))
            seuil = None
            if score.get("dernier"):
                seuil = seuils.seuils_du_systeme(
                    CONFIG, score["dernier"].get("systeme")).get("isolement_mohm")
            points = _points_courbe(rapports, score.get("releves") or [])
            courbe = views.courbe_isolement_svg(points, seuil=seuil)
            return self.repondre(views.circuit_page(
                _meta_circuit(ref), score, rapports, courbe, seuil))

        if chemin in ("/export.csv", "/export.json"):
            site = _premier(params, "site") or None
            circuit = _premier(params, "circuit") or None
            debut = _premier(params, "debut") or None
            fin = _premier(params, "fin") or None
            rapports = export.filtrer_rapports(
                storage.lister(5000), site=site, circuit=circuit,
                debut=debut, fin=fin)
            # Ordre chronologique pour les exports
            rapports = sorted(
                rapports, key=lambda r: (r.get("date") or "", r.get("id") or 0))
            if chemin.endswith(".csv"):
                return self.repondre(
                    export.vers_csv(rapports),
                    type_mime="text/csv; charset=utf-8",
                    fichier="rapports.csv")
            return self.repondre(
                export.vers_json(rapports),
                type_mime="application/json; charset=utf-8",
                fichier="rapports.json")

        if chemin.startswith("/rapport/") and chemin.endswith("/odoo.json"):
            try:
                rapport_id = int(chemin.split("/")[2])
            except (ValueError, IndexError):
                return self.repondre("Référence invalide", 400, "text/plain; charset=utf-8")
            rapport = storage.lire(rapport_id)
            if not rapport:
                return self.repondre("Rapport introuvable", 404, "text/plain; charset=utf-8")
            charge = export.charge_odoo(rapport)
            return self.repondre(
                json.dumps(charge, ensure_ascii=False, indent=2),
                type_mime="application/json; charset=utf-8")

        if chemin.startswith("/rapport/"):
            try:
                rapport_id = int(chemin.rsplit("/", 1)[1])
            except ValueError:
                return self.repondre("Référence invalide", 400, "text/plain; charset=utf-8")
            rapport = storage.lire(rapport_id)
            if not rapport:
                return self.repondre("Rapport introuvable", 404, "text/plain; charset=utf-8")
            alertes = [a for a in storage.lister_alertes(200) if a["rapport_id"] == rapport_id]
            return self.repondre(views.rapport_page(rapport, alertes[0] if alertes else None))

        if chemin == "/sante":
            return self.repondre(json.dumps({"etat": "ok"}), 200, "application/json")

        return self.repondre("Page introuvable", 404, "text/plain; charset=utf-8")

    # ----------------------------------------------------------------- POST
    def do_POST(self):
        chemin = urlparse(self.path).path
        formulaire = self.lire_formulaire()

        if chemin == "/analyser":
            note = _premier(formulaire, "note").strip()
            if not note:
                return self.repondre(views.formulaire(sorted(EXEMPLES),
                                                      "La note est vide."))
            contexte = {
                "note": note,
                "site": _premier(formulaire, "site"),
                "circuit": _premier(formulaire, "circuit"),
                "technicien": _premier(formulaire, "technicien"),
                "date": _premier(formulaire, "date") or date.today().isoformat(),
            }
            # Verdict et formulaire : moteur de regles uniquement (deterministe).
            donnees = extraction.analyser(note, CONFIG)
            correctives = storage.correctives_12m(contexte["circuit"])
            verdict = seuils.evaluer(donnees, CONFIG, correctives)
            contexte["correctives"] = correctives
            return self.repondre(views.analyse(
                donnees, verdict, contexte, seuils.doit_notifier(verdict, CONFIG),
                llm_disponible=extraction.llm_autorise(CONFIG)))

        if chemin == "/comparer":
            note = _premier(formulaire, "note").strip() or _premier(
                formulaire, "note_brute").strip()
            if not note:
                return self.repondre(views.formulaire(sorted(EXEMPLES),
                                                      "La note est vide."))
            contexte = {
                "note": note,
                "site": _premier(formulaire, "site"),
                "circuit": _premier(formulaire, "circuit"),
                "technicien": _premier(formulaire, "technicien"),
                "date": _premier(formulaire, "date") or date.today().isoformat(),
            }
            correctives = storage.correctives_12m(contexte["circuit"])
            contexte["correctives"] = correctives
            comp = extraction.comparer_moteurs(note, CONFIG)
            # Le verdict reste celui des regles, meme si le LLM diverge.
            verdict = seuils.evaluer(comp["regles"], CONFIG, correctives)
            return self.repondre(views.comparaison(
                comp["regles"], comp["llm"], comp["ecarts"], verdict, contexte,
                seuils.doit_notifier(verdict, CONFIG), message=comp["message"]))

        if chemin == "/valider":
            rapport = {
                "reference": None,
                "date": _premier(formulaire, "date") or date.today().isoformat(),
                "site": _premier(formulaire, "site"),
                "circuit": _premier(formulaire, "circuit"),
                "systeme": _premier(formulaire, "systeme"),
                "nature": _premier(formulaire, "nature"),
                "controle": _premier(formulaire, "controle"),
                "technicien": _premier(formulaire, "technicien"),
                "courant_a": _nombre(_premier(formulaire, "courant_a")),
                "isolement_mohm": _nombre(_premier(formulaire, "isolement_mohm")),
                "feux_hs": int(_nombre(_premier(formulaire, "feux_hs")) or 0)
                           if _premier(formulaire, "feux_hs") else None,
                "duree_h": _nombre(_premier(formulaire, "duree_h")),
                "travail_de_nuit": "nuit" in _premier(formulaire, "note_brute").lower(),
                "consignation": "consign" in _premier(formulaire, "note_brute").lower(),
                "habilitation": _premier(formulaire, "habilitation"),
                "travaux": _premier(formulaire, "travaux"),
                "constat": _premier(formulaire, "constat"),
                "suite": _premier(formulaire, "suite"),
                "note_brute": _premier(formulaire, "note_brute"),
                "moteur": _premier(formulaire, "moteur"),
                "niveau": _premier(formulaire, "niveau") or "info",
            }
            try:
                motifs = json.loads(_premier(formulaire, "motifs") or "[]")
            except json.JSONDecodeError:
                motifs = []
            rapport["motifs"] = motifs

            rapport_id, reference = storage.enregistrer(rapport)
            rapport["id"], rapport["reference"] = rapport_id, reference

            verdict = {"niveau": rapport["niveau"], "motifs": motifs}
            if seuils.doit_notifier(verdict, CONFIG):
                notify.alerter(CONFIG, rapport, verdict, storage.journaliser_alerte)
            return self.rediriger("/rapport/%d" % rapport_id)

        return self.repondre("Action inconnue", 404, "text/plain; charset=utf-8")


def main():
    global EXEMPLES
    storage.initialiser()
    source = charger_config()
    EXEMPLES = charger_exemples()

    push = ((CONFIG.get("notifications") or {}).get("push") or {})
    mail = ((CONFIG.get("notifications") or {}).get("courriel") or {})
    llm = CONFIG.get("llm") or {}

    print("=" * 62)
    print("  Assistant de rapport d'intervention")
    print("=" * 62)
    print("  Configuration : %s" % (source or "aucune, valeurs par defaut"))
    print("  Extraction    : regles%s" % (
        " + LLM autorise" if extraction.llm_autorise(CONFIG)
        else " (LLM inactif — cle ou autoriser_envoi)"))
    print("  Notification  : push %s, courriel %s" % (
        "actif" if push.get("actif") else "inactif",
        "actif" if mail.get("actif") else "inactif"))
    print("  Exemples      : %d note(s) de terrain" % len(EXEMPLES))
    print("-" * 62)
    print("  Ouvrir http://localhost:%d" % PORT)
    print("  Ctrl+C pour arreter")
    print("=" * 62)

    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nArret.")
