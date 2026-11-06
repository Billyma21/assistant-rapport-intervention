# Assistant de rapport d'intervention

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)
[![Hors ligne](https://img.shields.io/badge/mode-hors%20ligne%20par%20d%C3%A9faut-0E7C86)](#)
[![Sans dépendance](https://img.shields.io/badge/dépendances-bibliothèque%20standard-important)](#)

Application web locale qui transforme une **note de terrain libre** en
**rapport d'intervention structuré**, applique des **seuils paramétrables** et
déclenche des **alertes motivées** — conçue pour la maintenance du balisage
lumineux aéronautique (AGL).

> **Auteur :** MAAYOUD.B ([@Billyma21](https://github.com/Billyma21))  
> **Copyright © 2026 MAAYOUD.B.** Tous droits réservés quant à l'attribution.  
> Publié sous licence [MIT](LICENSE).

---

## Le problème

Un technicien intervient sur une piste à deux heures du matin, dans un créneau
court, avec des gants. Il note ce qu'il a fait sur un carnet ou dans un message.
Le lendemain, quelqu'un ressaisit tout au bureau, range l'information dans les
bonnes cases, et remarque, parfois, qu'une valeur était anormale.

**L'écart entre le relevé et sa prise en compte se compte en jours.** C'est cet
écart que cet outil supprime.

## Fonctionnalités

| Domaine | Capacités |
|---|---|
| **Extraction** | Moteur de règles déterministe ; complément d'extraction distant optionnel |
| **Criticité** | Seuils par système, récurrence 12 mois, motifs stables et opposables |
| **Pilotage** | Tableau de bord, fiches circuit / site, score de risque 0–100 expliqué |
| **Tendance** | Projection d'isolement (régression linéaire, garde-fous métier) |
| **Sorties** | Export CSV / JSON, charge ERP (`/odoo.json`), impression signée, résumé hebdo |
| **Alertes** | Journal interne permanent ; push ntfy et courriel SMTP optionnels |

## Décisions d'architecture

1. **Aucune dépendance externe** — bibliothèque standard Python uniquement.
   Démarre sur n'importe quel poste, y compris hors réseau.
2. **Hors ligne par défaut** — aucune fonctionnalité essentielle ne dépend d'Internet.
3. **Déterminisme** — pour une même note et une même config, le moteur de règles
   rend exactement le même résultat.
4. **Aucun seuil réglementaire en dur** — tout est dans `config.json`.
5. **Extraction distante optionnelle** — le verdict reste celui des règles ;
   aucune donnée n'est envoyée sans `autoriser_envoi: true`.

## Prérequis

- Python **3.9** ou supérieur  
- Aucun `pip install`

## Démarrage rapide

```bash
git clone https://github.com/Billyma21/assistant-rapport-intervention.git
cd assistant-rapport-intervention

# Copier la configuration d'exemple
cp config.example.json config.json   # Windows : copy config.example.json config.json

# Charger un parc de démonstration (déterministe)
python historique.py --vider
python historique.py --resume

# Lancer le serveur
python app.py
```

Ouvrir **http://localhost:8000**

Sous Windows : double-cliquer sur `demarrer.bat`.  
Sous macOS / Linux : `./demarrer.sh`.  
Changer de port : `PORT=9000 python app.py`.

### Tests

```bash
python -m unittest discover tests -v
```

## Structure du projet

```
assistant-rapport-intervention/
├── app.py                 Serveur HTTP et routage
├── historique.py          Parc de démonstration déterministe
├── resume.py              Résumé hebdomadaire
├── config.example.json    Seuils, notifications, extraction distante, risque
├── demarrer.bat / .sh
├── core/
│   ├── extraction.py      Moteur de règles (+ complément distant optionnel)
│   ├── seuils.py          Verdict et motifs
│   ├── risque.py          Score 0–100 + projection
│   ├── export.py          CSV, JSON, charge Odoo
│   ├── notify.py          Push, courriel, journal
│   └── storage.py         SQLite
├── web/views.py           Interface HTML
├── tests/                 Suite unittest
├── exemples/              5 notes de terrain
├── MANUEL.md              Mode d'emploi utilisateurs
├── LICENSE
└── README.md
```

## Configuration

Copier `config.example.json` en `config.json` (fichier ignoré par Git).

### Seuils

```json
"seuils": {
  "defaut": {
    "isolement_mohm": 50,
    "courant_nominal_a": 6.6,
    "courant_tolerance_a": 0.15,
    "feux_hs_alerte": 5,
    "recurrence_12m": 3
  },
  "par_systeme": {
    "toucher des roues": { "feux_hs_alerte": 3 },
    "PAPI": { "feux_hs_alerte": 1 }
  }
}
```

Les valeurs livrées sont des **exemples** à confirmer avec l'exploitant.

### Notifications

- **Push** (ntfy) et **courriel** (SMTP) : désactivés par défaut.
- Le **journal interne** enregistre toujours les alertes, même hors ligne.

### Complément d'extraction distant (optionnel)

```json
"llm": {
  "api_key": "...",
  "endpoint": "https://api.anthropic.com/v1/messages",
  "model": "claude-sonnet-4-5",
  "timeout": 20,
  "autoriser_envoi": true
}
```

Sans clé **ou** sans `autoriser_envoi: true`, aucune note n'est envoyée.
Sur la page d'analyse : bouton « Comparer avec l'extraction distante ».

## Principales routes

| Route | Description |
|---|---|
| `/` | Tableau de bord |
| `/nouveau` | Saisie d'une note |
| `/rapports`, `/rapport/<id>` | Liste et fiche (impression) |
| `/circuit/<ref>`, `/sites`, `/site/<nom>` | Pilotage parc |
| `/alertes`, `/config`, `/sante` | Alertes, config, healthcheck |
| `/export.csv`, `/export.json` | Exports filtrables |
| `/rapport/<id>/odoo.json` | Charge utile ERP |

### Export

```
/export.csv?site=Liège&circuit=CIR-0009&debut=2025-01-01&fin=2026-12-31
```

CSV UTF-8 avec BOM, séparateur point-virgule (Excel).

### Passerelle ERP

`GET /rapport/<id>/odoo.json` produit une charge JSON prête pour un connecteur
Odoo (XML-RPC / JSON-RPC) : site, circuit, date, type de contrôle, mesures,
conformité, observations, référence externe.

### Résumé hebdomadaire

```bash
python resume.py
```

## Données de démonstration

`historique.py` construit un parc plausible (6 plateformes, ~20 circuits,
soixante-dix rapports sur 18 mois). **Ce ne sont pas des données d'exploitation.**
Aucune donnée personnelle, aucun nom d'entreprise.

## Documentation utilisateur

Voir [MANUEL.md](MANUEL.md) pour le mode d'emploi terrain / bureau.

## Feuille de route (hors prototype)

- Authentification et comptes
- Saisie mobile hors ligne avec synchronisation
- Dictée vocale
- Connecteur Odoo actif (poussée XML-RPC)
- Pièces jointes photo
- Exposition HTTPS via reverse proxy

## Auteur & copyright

| | |
|---|---|
| **Auteur** | **MAAYOUD.B** ([@Billyma21](https://github.com/Billyma21)) |
| **Copyright** | © 2026 MAAYOUD.B. Tous droits réservés quant à l'attribution. |
| **Licence** | [MIT](LICENSE) — libre d'usage, de modification et de redistribution, sous réserve du maintien de l'avis de copyright. |

```
Copyright (c) 2026 MAAYOUD.B
```

Contributions et retours : ouvrir une *issue* ou une *pull request* sur ce dépôt.
