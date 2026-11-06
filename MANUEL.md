# Mode d'emploi

À l'attention des techniciens et des responsables de maintenance.

---

## En deux phrases

Vous écrivez votre note d'intervention comme vous le faites déjà, en langage
normal. L'application la range dans les bonnes cases, vérifie les valeurs, et
prévient tout de suite si quelque chose sort des clous.

---

## 1. Ouvrir l'application

Dans le navigateur : **http://localhost:8000**

Cinq onglets en haut :

| Onglet | À quoi il sert |
|---|---|
| **Tableau de bord** | les chiffres du moment et les derniers rapports |
| **Nouveau rapport** | c'est ici que tout commence |
| **Rapports** | l'historique complet |
| **Alertes** | tout ce qui a été envoyé, et à qui |
| **Seuils** | les valeurs d'alerte en vigueur |

---

## 2. Saisir une intervention

Onglet **Nouveau rapport**.

1. Renseignez le **site**, le **circuit**, votre **nom** et la **date**.
2. Dans la grande zone, écrivez votre note **normalement**. Pas de format
   imposé, pas de formulaire à remplir case par case.
3. Cliquez sur **Analyser la note**.

### Écrivez comme vous parlez

Un exemple de note qui fonctionne très bien :

> Intervention de nuit du 04/11, créneau 22h à 02h, hors trafic.
> Circuit consigné avant travaux, habilitation B2V.
> Mesure d'isolement sur la boucle TDZ : 38 MOhm. Courant relevé 6,52 A.
> Sept feux hors service sur la zone de toucher des roues.
> Baisse d'isolement constatée depuis deux campagnes.
> Optiques à commander avant la prochaine visite.

### Ce que l'application sait reconnaître toute seule

- **Les valeurs** : « 38 MOhm », « isolement de 38 », « 6,52 A », « sept feux
  hors service », « 3 HS », « de 22h à 02h », « 4 heures ».
- **Le système** : axe de piste, bord de piste, seuil, extrémité, TDZ, rampe
  d'approche, PAPI, axe ou bord de voie de circulation, barres d'arrêt,
  balisage d'obstacles.
- **Le type de contrôle** : inspection visuelle, mesure d'isolement, contrôle
  électrique, photométrie.
- **Le contexte** : travail de nuit, consignation, habilitation B2V ou BR.
- **La nature** : visite périodique ou dépannage.

### Les trois rubriques du rapport

Vos phrases sont réparties automatiquement :

- **Travaux réalisés** : ce que vous avez fait.
- **Constat et anomalies** : les phrases qui contiennent un constat, un défaut,
  une baisse, une dégradation.
- **Suite à donner** : les phrases qui parlent de quelque chose à commander, à
  prévoir, à planifier, à surveiller.

> **Astuce.** Pour qu'une consigne atterrisse dans « suite à donner », employez
> une tournure claire : « à commander », « à prévoir », « à replanifier ».

---

## 3. Vérifier et corriger

L'écran d'analyse montre d'abord un **bandeau de couleur** :

| Couleur | Signification |
|---|---|
| **Vert** | aucun écart par rapport aux seuils |
| **Orange** | point de vigilance, à surveiller |
| **Rouge** | écart critique, une alerte part à la validation |

En dessous, **pourquoi ce niveau** : chaque motif est écrit en clair, avec la
valeur relevée et le seuil appliqué. Vous n'avez jamais à deviner.

Puis tous les champs extraits, **modifiables**. L'application se trompe parfois,
surtout sur une note très abrégée. **Relisez toujours avant de valider.**

> **Rien n'est enregistré tant que vous n'avez pas cliqué sur « Valider ».**
> Vous pouvez revenir en arrière sans conséquence.

---

## 4. Valider

Cliquez sur **Valider et enregistrer**. Trois choses se produisent :

1. Le rapport reçoit une référence définitive, RAP-0001, RAP-0002, et ainsi de
   suite.
2. Si le niveau le justifie, une **alerte part immédiatement** : notification
   sur les téléphones abonnés, courriel aux destinataires configurés, et
   inscription au journal.
3. Vous arrivez sur le rapport complet, prêt à imprimer.

---

## 5. Imprimer le rapport

Sur la page du rapport, bouton **Imprimer**. La mise en page retire les menus et
les blocs techniques : il ne reste que le rapport.

---

## 6. Consulter les alertes

Onglet **Alertes**. Chaque entrée indique l'heure, le niveau, le message exact
envoyé, et l'état de chaque canal.

> **Le journal est tenu même quand aucun canal n'est configuré.** Il reste donc
> toujours une trace, y compris hors ligne.

---

## Questions fréquentes

**L'application s'est trompée sur une valeur.**
Corrigez-la à l'écran d'analyse avant de valider. C'est prévu pour.

**Je n'ai pas reçu la notification sur mon téléphone.**
Vérifiez que vous êtes abonné au bon sujet dans l'application ntfy, et que le
canal push est actif dans les réglages. L'onglet Alertes indique « envoyé » ou
le détail de l'échec.

**Pourquoi noter une valeur quand tout va bien ?**
Parce qu'une mesure isolée ne dit rien et que trois mesures dessinent une
tendance. Un isolement qui passe de 142 à 89 puis à 38 MΩ n'est pas une panne :
c'est une dérive qu'on voit venir. Elle n'apparaît que si les bonnes campagnes
ont été saisies.

**Qui décide des seuils ?**
Pas l'application. Ils sont définis dans la configuration, par système de
balisage, et se fixent avec l'exploitant. L'onglet **Seuils** affiche à tout
moment les valeurs en vigueur.

**Puis-je l'utiliser sans connexion internet ?**
Oui, entièrement. Seuls les envois de notifications ont besoin du réseau, et
leur échec n'empêche ni l'analyse ni l'enregistrement.

---

## Les bons réflexes

- Écrivez vos **valeurs chiffrées** avec leur unité : 38 MOhm, 6,52 A.
- Précisez toujours si le circuit a été **consigné** : l'application le relève,
  et son absence déclenche un point de vigilance sur un dépannage.
- Employez « à commander », « à prévoir », « à planifier » pour ce qui doit
  revenir plus tard.
- **Relisez l'écran d'analyse.** Trente secondes de vérification valent mieux
  qu'un rapport faux dans l'historique.

## Repartir d'une base propre

Si vous souhaitez vider l'historique et recommencer :

```bash
python3 historique.py --vider
python3 historique.py
```

La première commande efface tous les rapports enregistrés, la seconde
recharge le jeu de démonstration.
