# -*- coding: utf-8 -*-
"""Tests LLM : autorisation, schema, comparaison sans reseau."""

import unittest

from core import extraction


def _donnees_ok(**kwargs):
    base = {
        "nature": "corrective",
        "systeme": "PAPI",
        "controle": "visuel",
        "courant_a": 6.58,
        "isolement_mohm": None,
        "feux_hs": 1,
        "duree_h": 2.0,
        "travail_de_nuit": True,
        "consignation": True,
        "habilitation": "BR",
        "travaux": "Remplacement",
        "constat": "1 feu HS",
        "suite": "",
    }
    base.update(kwargs)
    return base


class TestAutorisation(unittest.TestCase):

    def test_refuse_sans_autoriser(self):
        cfg = {"llm": {"api_key": "sk-x", "endpoint": "https://x", "model": "m",
                       "autoriser_envoi": False}}
        self.assertFalse(extraction.llm_autorise(cfg))
        data, msg = extraction.extraire_par_llm("note", cfg)
        self.assertIsNone(data)
        self.assertIn("non autorise", msg)

    def test_refuse_sans_cle(self):
        cfg = {"llm": {"api_key": "", "endpoint": "https://x", "model": "m",
                       "autoriser_envoi": True}}
        self.assertFalse(extraction.llm_autorise(cfg))

    def test_accepte_si_complet(self):
        cfg = {"llm": {"api_key": "sk-x", "endpoint": "https://x", "model": "m",
                       "autoriser_envoi": True}}
        self.assertTrue(extraction.llm_autorise(cfg))


class TestSchema(unittest.TestCase):

    def test_schema_valide(self):
        ok, err = extraction.valider_schema_llm(_donnees_ok())
        self.assertTrue(ok)
        self.assertEqual(err, [])

    def test_cle_manquante(self):
        d = _donnees_ok()
        del d["suite"]
        ok, err = extraction.valider_schema_llm(d)
        self.assertFalse(ok)
        self.assertTrue(any("suite" in e for e in err))

    def test_nature_invalide(self):
        ok, err = extraction.valider_schema_llm(_donnees_ok(nature="urgence"))
        self.assertFalse(ok)

    def test_feux_float_entier(self):
        d = _donnees_ok(feux_hs=3.0)
        ok, err = extraction.valider_schema_llm(d)
        self.assertTrue(ok)
        self.assertEqual(d["feux_hs"], 3)


class TestComparer(unittest.TestCase):

    def test_comparer_sans_reseau(self):
        cfg = {"llm": {"autoriser_envoi": False}}
        note = "Depannage PAPI, 1 feu HS, habilitation BR, nuit."
        comp = extraction.comparer_moteurs(note, cfg)
        self.assertEqual(comp["regles"]["moteur"], "regles")
        self.assertIsNone(comp["llm"])
        self.assertTrue(comp["message"])

    def test_ecarts_detectes(self):
        a = _donnees_ok(isolement_mohm=38.0)
        b = _donnees_ok(isolement_mohm=40.0, nature="preventive")
        # Utilise la fonction interne via comparer simule
        ecarts = []
        for cle in extraction.CLES_SCHEMA:
            if extraction._valeurs_differentes(a.get(cle), b.get(cle)):
                ecarts.append(cle)
        self.assertIn("isolement_mohm", ecarts)
        self.assertIn("nature", ecarts)

    def test_analyser_jamais_reseau(self):
        # Meme avec autorisation, analyser() reste sur les regles.
        cfg = {"llm": {"api_key": "sk", "endpoint": "http://127.0.0.1:9",
                       "model": "x", "autoriser_envoi": True, "timeout": 1}}
        d = extraction.analyser("Visite periodique bord de piste, isolement 240.", cfg)
        self.assertEqual(d["moteur"], "regles")
        self.assertEqual(d["isolement_mohm"], 240.0)


if __name__ == "__main__":
    unittest.main()
