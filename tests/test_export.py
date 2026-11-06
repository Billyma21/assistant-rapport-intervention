# -*- coding: utf-8 -*-
"""Tests des exports CSV/JSON et de la charge Odoo."""

import json
import unittest

from core import export


RAPPORTS = [
    {
        "id": 1, "reference": "RAP-0001", "date": "2026-01-10",
        "site": "Liège", "circuit": "CIR-0009", "systeme": "barres d'arrêt",
        "nature": "corrective", "controle": "visuel", "technicien": "Equipe",
        "courant_a": 6.5, "isolement_mohm": 80.0, "feux_hs": 3, "duree_h": 2.0,
        "travail_de_nuit": 1, "consignation": 1, "habilitation": "BR",
        "niveau": "vigilance", "motifs": '["3 feux HS"]',
        "travaux": "Remplacement", "constat": "Portion ouest", "suite": "Suivi",
        "moteur": "regles",
    },
    {
        "id": 2, "reference": "RAP-0002", "date": "2026-06-01",
        "site": "Bruxelles", "circuit": "CIR-0003", "systeme": "TDZ",
        "nature": "preventive", "controle": "isolement", "technicien": "Equipe",
        "courant_a": 6.6, "isolement_mohm": 200.0, "feux_hs": 0, "duree_h": 4.0,
        "travail_de_nuit": 0, "consignation": 1, "habilitation": "B2V",
        "niveau": "info", "motifs": "[]",
        "travaux": "Campagne", "constat": "OK", "suite": "",
        "moteur": "regles",
    },
]


class TestFiltre(unittest.TestCase):

    def test_filtre_site(self):
        r = export.filtrer_rapports(RAPPORTS, site="Liège")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["circuit"], "CIR-0009")

    def test_filtre_periode(self):
        r = export.filtrer_rapports(RAPPORTS, debut="2026-05-01", fin="2026-12-31")
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["reference"], "RAP-0002")


class TestCsvJson(unittest.TestCase):

    def test_csv_bom_et_separateur(self):
        texte = export.vers_csv(RAPPORTS)
        self.assertTrue(texte.startswith("\ufeff"))
        self.assertIn("reference;date;site", texte)
        self.assertIn("RAP-0001", texte)

    def test_json_valide(self):
        data = json.loads(export.vers_json(RAPPORTS))
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["motifs"], ["3 feux HS"])


class TestOdoo(unittest.TestCase):

    def test_charge_conforme(self):
        charge = export.charge_odoo(RAPPORTS[1])
        self.assertTrue(charge["conformite"])
        self.assertEqual(charge["type_controle"], "isolement")
        self.assertEqual(charge["feux_hors_service"], 0)
        self.assertEqual(charge["reference_externe"], "RAP-0002")

    def test_charge_non_conforme(self):
        charge = export.charge_odoo(RAPPORTS[0])
        self.assertFalse(charge["conformite"])
        self.assertIn("site", charge)
        self.assertIn("observations", charge)


if __name__ == "__main__":
    unittest.main()
