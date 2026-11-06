# -*- coding: utf-8 -*-
"""Tests du score de risque (composantes et explication)."""

import json
import os
import unittest
from datetime import date, timedelta

from core import risque

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _config():
    with open(os.path.join(RACINE, "config.json"), encoding="utf-8") as f:
        return json.load(f)


CONFIG = _config()


def _rapport(jours, **kwargs):
    base = {
        "date": (date.today() - timedelta(days=jours)).isoformat(),
        "systeme": "zone de toucher des roues (TDZ)",
        "nature": "preventive",
        "controle": "isolement",
        "isolement_mohm": 150.0,
        "feux_hs": 0,
        "niveau": "info",
        "circuit": "CIR-TEST",
        "site": "Bruxelles",
    }
    base.update(kwargs)
    return base


class TestScoreRisque(unittest.TestCase):

    def test_score_sain_bas(self):
        rapports = [
            _rapport(400, isolement_mohm=200),
            _rapport(200, isolement_mohm=190),
            _rapport(10, isolement_mohm=185),
        ]
        s = risque.scorer_circuit("CIR-TEST", rapports, CONFIG, 0)
        self.assertLess(s["score"], 40)
        self.assertEqual(len(s["detail"]), 5)

    def test_score_critique_eleve(self):
        rapports = [
            _rapport(400, isolement_mohm=140),
            _rapport(200, isolement_mohm=90),
            _rapport(20, isolement_mohm=40, feux_hs=5, nature="corrective",
                     niveau="critique"),
            _rapport(60, nature="corrective", isolement_mohm=55, feux_hs=4),
            _rapport(100, nature="corrective", isolement_mohm=70, feux_hs=3),
        ]
        s = risque.scorer_circuit("CIR-TEST", rapports, CONFIG, 3)
        self.assertGreaterEqual(s["score"], 50)
        self.assertTrue(s["motif_dominant"])
        self.assertTrue(all("texte" in d and "points" in d for d in s["detail"]))

    def test_pente_sans_trois_points(self):
        pts, txt = risque.points_pente(
            [(date.today(), 100.0), (date.today(), 90.0)], 15)
        self.assertEqual(pts, 0.0)
        self.assertIn("Moins de trois", txt)

    def test_regression_lineaire(self):
        # y = -2x + 10
        points = [(0.0, 10.0), (1.0, 8.0), (2.0, 6.0)]
        pente, ordonnee = risque.regression_lineaire(points)
        self.assertAlmostEqual(pente, -2.0, places=5)
        self.assertAlmostEqual(ordonnee, 10.0, places=5)


class TestProjection(unittest.TestCase):

    def test_moins_de_trois_releves(self):
        releves = [
            (date.today() - timedelta(days=200), 120.0),
            (date.today() - timedelta(days=100), 100.0),
        ]
        p = risque.projeter_franchissement(releves, 50, CONFIG)
        self.assertFalse(p["active"])
        self.assertIsNone(p["phrase"])

    def test_pente_positive_pas_de_projection(self):
        releves = [
            (date.today() - timedelta(days=400), 80.0),
            (date.today() - timedelta(days=200), 100.0),
            (date.today() - timedelta(days=20), 130.0),
        ]
        p = risque.projeter_franchissement(releves, 50, CONFIG)
        self.assertFalse(p["active"])

    def test_seuil_deja_franchi(self):
        releves = [
            (date.today() - timedelta(days=400), 120.0),
            (date.today() - timedelta(days=200), 70.0),
            (date.today() - timedelta(days=20), 40.0),
        ]
        p = risque.projeter_franchissement(releves, 50, CONFIG)
        self.assertFalse(p["active"])

    def test_projection_avec_reserve(self):
        # Baisse reguliere qui croise 50 MΩ dans moins de 24 mois.
        releves = [
            (date.today() - timedelta(days=360), 120.0),
            (date.today() - timedelta(days=180), 90.0),
            (date.today() - timedelta(days=10), 70.0),
        ]
        p = risque.projeter_franchissement(releves, 50, CONFIG)
        self.assertTrue(p["active"])
        self.assertIn("seuil de 50 MΩ", p["phrase"])
        self.assertIn("à confirmer par la prochaine campagne", p["phrase"])
        self.assertIn("Estimation à partir de 3 relevés", p["phrase"])

    def test_horizon_24_mois(self):
        # Pente tres faible : franchissement au-dela de 24 mois → silencieux.
        releves = [
            (date.today() - timedelta(days=400), 200.0),
            (date.today() - timedelta(days=200), 199.0),
            (date.today() - timedelta(days=10), 198.0),
        ]
        p = risque.projeter_franchissement(releves, 50, CONFIG)
        self.assertFalse(p["active"])

    def test_score_embarque_projection(self):
        rapports = [
            _rapport(360, isolement_mohm=120),
            _rapport(180, isolement_mohm=90),
            _rapport(10, isolement_mohm=70),
        ]
        s = risque.scorer_circuit("CIR-TEST", rapports, CONFIG, 0)
        self.assertIn("projection", s)
        self.assertTrue(s["projection"]["active"])


if __name__ == "__main__":
    unittest.main()
