# -*- coding: utf-8 -*-
"""Suite de tests du moteur d'extraction (regles).

Couvre les notes d'exemple, les variantes d'ecriture terrain, et les cas
degrades. Le moteur ne doit jamais lever d'exception.
"""

import json
import os
import unittest
from datetime import date

from core import extraction, seuils

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config():
    with open(os.path.join(RACINE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def _note_exemple(nom):
    with open(os.path.join(RACINE, "exemples", nom), encoding="utf-8") as f:
        return f.read().strip()


CONFIG = _config()


class TestExemples(unittest.TestCase):
    """Les cinq notes d'exemple restent stables (valeurs + verdict)."""

    def test_01_isolement_critique(self):
        note = _note_exemple("1_isolement_critique.txt")
        d = extraction.analyser(note, CONFIG)
        self.assertEqual(d["systeme"], "zone de toucher des roues (TDZ)")
        self.assertEqual(d["nature"], "corrective")
        self.assertEqual(d["controle"], "isolement")
        self.assertEqual(d["courant_a"], 6.52)
        self.assertEqual(d["isolement_mohm"], 38.0)
        self.assertEqual(d["feux_hs"], 7)
        self.assertTrue(d["travail_de_nuit"])
        self.assertTrue(d["consignation"])
        self.assertEqual(d["habilitation"], "B2V")
        v = seuils.evaluer(d, CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")

    def test_02_visite_preventive_conforme(self):
        note = _note_exemple("2_visite_preventive_conforme.txt")
        d = extraction.analyser(note, CONFIG)
        self.assertEqual(d["systeme"], "bord de piste")
        self.assertEqual(d["nature"], "preventive")
        self.assertEqual(d["controle"], "visuel")
        self.assertEqual(d["courant_a"], 6.6)
        self.assertEqual(d["isolement_mohm"], 240.0)
        self.assertEqual(d["feux_hs"], 0)
        v = seuils.evaluer(d, CONFIG, 0)
        self.assertEqual(v["niveau"], "info")

    def test_03_depannage_barres_arret(self):
        note = _note_exemple("3_depannage_barres_arret.txt")
        d = extraction.analyser(note, CONFIG)
        self.assertEqual(d["systeme"], "barres d'arret")
        self.assertEqual(d["nature"], "corrective")
        self.assertEqual(d["isolement_mohm"], 61.0)
        self.assertEqual(d["feux_hs"], 6)
        self.assertTrue(d["consignation"])
        self.assertEqual(d["habilitation"], "BR")
        v = seuils.evaluer(d, CONFIG, 3)
        self.assertEqual(v["niveau"], "critique")

    def test_04_controle_electrique_annuel(self):
        note = _note_exemple("4_controle_electrique_annuel.txt")
        d = extraction.analyser(note, CONFIG)
        self.assertEqual(d["systeme"], "axe de piste")
        self.assertEqual(d["nature"], "preventive")
        self.assertEqual(d["controle"], "electrique")
        self.assertEqual(d["courant_a"], 6.61)
        self.assertEqual(d["isolement_mohm"], 180.0)
        self.assertEqual(d["feux_hs"], 2)
        v = seuils.evaluer(d, CONFIG, 0)
        self.assertEqual(v["niveau"], "vigilance")

    def test_05_papi_hors_service(self):
        note = _note_exemple("5_papi_hors_service.txt")
        d = extraction.analyser(note, CONFIG)
        self.assertEqual(d["systeme"], "PAPI")
        self.assertEqual(d["nature"], "corrective")
        self.assertEqual(d["feux_hs"], 1)
        self.assertEqual(d["courant_a"], 6.58)
        self.assertTrue(d["travail_de_nuit"])
        self.assertTrue(d["consignation"])
        self.assertEqual(d["habilitation"], "BR")
        v = seuils.evaluer(d, CONFIG, 0)
        self.assertEqual(v["niveau"], "critique")


class TestUnitesIsolement(unittest.TestCase):
    """Variantes d'ecriture des unites d'isolement."""

    def _iso(self, note):
        return extraction.analyser(note, CONFIG)["isolement_mohm"]

    def test_mohm(self):
        self.assertEqual(self._iso("Mesure : 38 MOhm."), 38.0)

    def test_m_omega(self):
        self.assertEqual(self._iso("Mesure : 38 MΩ."), 38.0)

    def test_megohms(self):
        self.assertEqual(self._iso("Isolement 38 mégohms."), 38.0)

    def test_m_ohms(self):
        self.assertEqual(self._iso("Releve 38M ohms sur la boucle."), 38.0)

    def test_isolement_seul(self):
        self.assertEqual(self._iso("Campagne trimestrielle, isolement 38."), 38.0)


class TestDecimales(unittest.TestCase):

    def test_virgule_et_point(self):
        a = extraction.analyser("Courant releve 6,52 A.", CONFIG)
        b = extraction.analyser("Courant releve 6.52 A.", CONFIG)
        self.assertEqual(a["courant_a"], b["courant_a"])
        self.assertEqual(a["courant_a"], 6.52)


class TestFeuxHs(unittest.TestCase):

    def test_lettres_et_chiffres(self):
        a = extraction.analyser("sept feux hors service sur la TDZ.", CONFIG)
        b = extraction.analyser("7 feux HS sur la TDZ.", CONFIG)
        self.assertEqual(a["feux_hs"], 7)
        self.assertEqual(b["feux_hs"], 7)

    def test_hs(self):
        self.assertEqual(
            extraction.analyser("3 HS signales sur l'axe.", CONFIG)["feux_hs"], 3)

    def test_hors_service(self):
        self.assertEqual(
            extraction.analyser("4 feux hors service.", CONFIG)["feux_hs"], 4)

    def test_eteints(self):
        self.assertEqual(
            extraction.analyser("cinq feux éteints sur le bord.", CONFIG)["feux_hs"], 5)

    def test_morts(self):
        self.assertEqual(
            extraction.analyser("2 feux morts remplaces.", CONFIG)["feux_hs"], 2)


class TestDates(unittest.TestCase):

    def test_jj_mm(self):
        d = extraction.analyser("Intervention de nuit du 04/11.", CONFIG)
        self.assertEqual(d["date"], "%d-11-04" % date.today().year)

    def test_jour_mois_lettres(self):
        d = extraction.analyser("Intervention du 4 novembre.", CONFIG)
        self.assertEqual(d["date"], "%d-11-04" % date.today().year)

    def test_date_complete(self):
        d = extraction.analyser("Intervention le 04-11-2026.", CONFIG)
        self.assertEqual(d["date"], "2026-11-04")

    def test_absence_date(self):
        d = extraction.analyser("Visite periodique, rien a signaler.", CONFIG)
        self.assertIsNone(d["date"])


class TestSystemes(unittest.TestCase):

    CAS = [
        ("Controle axe de piste 07R/25L.", "axe de piste"),
        ("Inspection bord de piste.", "bord de piste"),
        ("Feux de seuil piste 25L.", "seuil"),
        ("Remplacement extremite de piste.", "extremite de piste"),
        ("Boucle TDZ mesuree.", "zone de toucher des roues (TDZ)"),
        ("Zone de toucher des roues controlee.", "zone de toucher des roues (TDZ)"),
        ("Rampe d'approche ALS.", "rampe d'approche"),
        ("Alignement PAPI cote sud.", "PAPI"),
        ("Axe de voie de circulation bretelle W.", "axe de voie de circulation"),
        ("Bord de voie de circulation.", "bord de voie de circulation"),
        ("Barres d'arret points d'attente.", "barres d'arret"),
        ("Balisage d'obstacles sur mat.", "balisage d'obstacles"),
    ]

    def test_systemes(self):
        for note, attendu in self.CAS:
            with self.subTest(note=note):
                self.assertEqual(
                    extraction.analyser(note, CONFIG)["systeme"], attendu)


class TestNature(unittest.TestCase):

    def test_preventive_visite(self):
        self.assertEqual(
            extraction.analyser("Visite periodique du balisage.", CONFIG)["nature"],
            "preventive")

    def test_preventive_campagne(self):
        self.assertEqual(
            extraction.analyser("Campagne semestrielle d'isolement.", CONFIG)["nature"],
            "preventive")

    def test_corrective_panne(self):
        self.assertEqual(
            extraction.analyser("Depannage urgent suite a une panne.", CONFIG)["nature"],
            "corrective")

    def test_corrective_urgence(self):
        self.assertEqual(
            extraction.analyser("Intervention d'urgence signalee par la tour.", CONFIG)["nature"],
            "corrective")

    def test_corrective_defaut(self):
        self.assertEqual(
            extraction.analyser("Defaut d'alimentation, reparation effectuee.", CONFIG)["nature"],
            "corrective")


class TestMarqueurs(unittest.TestCase):

    def test_nuit_et_hors_trafic(self):
        d = extraction.analyser("Intervention de nuit, hors trafic.", CONFIG)
        self.assertTrue(d["travail_de_nuit"])

    def test_consignation(self):
        d = extraction.analyser("Circuit consigne avant travaux.", CONFIG)
        self.assertTrue(d["consignation"])

    def test_habilitation_b2v(self):
        self.assertEqual(
            extraction.analyser("Habilitation B2V.", CONFIG)["habilitation"], "B2V")

    def test_habilitation_br(self):
        self.assertEqual(
            extraction.analyser("Habilitation BR requise.", CONFIG)["habilitation"], "BR")

    def test_habilitation_bc(self):
        self.assertEqual(
            extraction.analyser("Presence BC pour consignation.", CONFIG)["habilitation"], "BC")


class TestCasDegrades(unittest.TestCase):

    def test_note_vide(self):
        d = extraction.analyser("", CONFIG)
        self.assertIsNone(d["isolement_mohm"])
        self.assertIsNone(d["courant_a"])
        self.assertIsNone(d["feux_hs"])
        self.assertIsNone(d["systeme"])

    def test_note_none(self):
        d = extraction.analyser(None, CONFIG)
        self.assertEqual(d["moteur"], "regles")
        self.assertIsNone(d["nature"])

    def test_un_seul_mot(self):
        d = extraction.analyser("ok", CONFIG)
        self.assertIsNone(d["isolement_mohm"])
        self.assertFalse(d["travail_de_nuit"])

    def test_sans_valeur_chiffree(self):
        d = extraction.analyser(
            "Passage sur site, rien de particulier a signaler.", CONFIG)
        self.assertIsNone(d["courant_a"])
        self.assertIsNone(d["isolement_mohm"])
        self.assertIsNone(d["feux_hs"])

    def test_isolements_contradictoires_premier_gagne(self):
        d = extraction.analyser(
            "Isolement 38 MOhm releve puis controle : isolement 120 MOhm.", CONFIG)
        self.assertEqual(d["isolement_mohm"], 38.0)

    def test_jamais_d_exception(self):
        for note in ("", "x", None, "###", "isolement abc MOhm", "\x00"):
            with self.subTest(note=repr(note)):
                try:
                    extraction.analyser(note, CONFIG)
                except Exception as exc:  # pragma: no cover
                    self.fail("exception inattendue: %s" % exc)


if __name__ == "__main__":
    unittest.main()
