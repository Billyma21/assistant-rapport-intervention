# -*- coding: utf-8 -*-
"""Tests du moteur de seuils : verdicts, motifs, ordre stable."""

import json
import os
import unittest

from core import seuils

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config():
    with open(os.path.join(RACINE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


CONFIG = _config()


def _donnees(**kwargs):
    base = {
        "systeme": "bord de piste",
        "nature": "preventive",
        "consignation": True,
        "isolement_mohm": None,
        "courant_a": None,
        "feux_hs": None,
    }
    base.update(kwargs)
    return base


class TestIsolement(unittest.TestCase):

    def test_sous_le_seuil_critique(self):
        v = seuils.evaluer(_donnees(isolement_mohm=38), CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")
        self.assertTrue(any("sous le seuil" in m for m in v["motifs"]))

    def test_proche_du_seuil_vigilance(self):
        # seuil 50, proche = < 75
        v = seuils.evaluer(_donnees(isolement_mohm=61), CONFIG, 0)
        self.assertEqual(v["niveau"], "vigilance")
        self.assertTrue(any("proche du seuil" in m for m in v["motifs"]))

    def test_au_dessus_info(self):
        v = seuils.evaluer(_donnees(isolement_mohm=240), CONFIG, 0)
        self.assertEqual(v["niveau"], "info")
        self.assertEqual(
            v["motifs"],
            ["Aucun ecart detecte par rapport aux seuils parametres."])

    def test_egal_seuil_proche(self):
        # 50 n'est pas < 50 : pas critique ; 50 < 75 : vigilance
        v = seuils.evaluer(_donnees(isolement_mohm=50), CONFIG, 0)
        self.assertEqual(v["niveau"], "vigilance")


class TestFeuxHsParSysteme(unittest.TestCase):

    def test_tdz_seuil_3(self):
        v = seuils.evaluer(
            _donnees(systeme="zone de toucher des roues (TDZ)", feux_hs=3),
            CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")

    def test_tdz_sous_seuil_vigilance(self):
        v = seuils.evaluer(
            _donnees(systeme="zone de toucher des roues (TDZ)", feux_hs=2),
            CONFIG, 0)
        self.assertEqual(v["niveau"], "vigilance")

    def test_barres_seuil_2(self):
        v = seuils.evaluer(
            _donnees(systeme="barres d'arret", feux_hs=2), CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")

    def test_papi_seuil_1(self):
        v = seuils.evaluer(
            _donnees(systeme="PAPI", feux_hs=1), CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")

    def test_axe_piste_seuil_4(self):
        v = seuils.evaluer(
            _donnees(systeme="axe de piste", feux_hs=4), CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")

    def test_defaut_seuil_5_vigilance(self):
        v = seuils.evaluer(
            _donnees(systeme="bord de piste", feux_hs=4), CONFIG, 0)
        self.assertEqual(v["niveau"], "vigilance")


class TestRecurrence(unittest.TestCase):

    def test_recurrence_atteinte(self):
        v = seuils.evaluer(_donnees(isolement_mohm=200), CONFIG, 3)
        self.assertEqual(v["niveau"], "critique")
        self.assertTrue(any("12 mois" in m for m in v["motifs"]))

    def test_recurrence_non_atteinte(self):
        v = seuils.evaluer(_donnees(isolement_mohm=200), CONFIG, 2)
        self.assertEqual(v["niveau"], "info")


class TestOrdreMotifs(unittest.TestCase):

    def test_ordre_stable(self):
        # isolement critique, feux HS, recurrence, consignation manquante
        donnees = _donnees(
            systeme="barres d'arret",
            nature="corrective",
            consignation=False,
            isolement_mohm=38,
            feux_hs=6,
        )
        v1 = seuils.evaluer(donnees, CONFIG, 3)
        v2 = seuils.evaluer(donnees, CONFIG, 3)
        self.assertEqual(v1["motifs"], v2["motifs"])
        self.assertEqual(v1["motifs"][0], "Isolement 38 MOhm sous le seuil de 50 MOhm.")
        self.assertTrue(v1["motifs"][1].startswith("6 feux hors service"))
        self.assertTrue("12 mois" in v1["motifs"][2])
        self.assertTrue("Consignation" in v1["motifs"][3])

    def test_courant_hors_tolerance_avant_feux(self):
        donnees = _donnees(
            isolement_mohm=200,
            courant_a=7.0,
            feux_hs=1,
        )
        v = seuils.evaluer(donnees, CONFIG, 0)
        self.assertEqual(v["motifs"][0][:7], "Courant")
        self.assertTrue(v["motifs"][1].startswith("1 feu"))


class TestNotification(unittest.TestCase):

    def test_doit_notifier_vigilance(self):
        self.assertTrue(seuils.doit_notifier({"niveau": "vigilance"}, CONFIG))

    def test_ne_notifie_pas_info(self):
        self.assertFalse(seuils.doit_notifier({"niveau": "info"}, CONFIG))


if __name__ == "__main__":
    unittest.main()
