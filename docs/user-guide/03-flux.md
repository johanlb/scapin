# 3. Flux

Le **Flux** est le centre de traitement de vos emails et messages. C'est ici que Scapin vous présente les éléments analysés pour validation.

---

## Principe

```
Email arrive → Scapin analyse → Proposition d'action → Vous validez → Exécution
```

Scapin ne fait **jamais** d'action sans votre approbation (sauf si la confiance dépasse 90%).

---

## Interface

### Liste des Items

Chaque item affiche :

- **Expéditeur** : Nom et email
- **Sujet** : Titre de l'email
- **Extrait** : Premiers mots du contenu
- **Action proposée** : Archive, Répondre, Tâche...
- **Confiance** : Score IA (0-100%)
- **Destination** : Dossier cible

### Niveaux d'Affichage

| Mode | Information |
|------|-------------|
| **Compact** | Sujet, expéditeur, action |
| **Normal** | + extrait, confiance, entités |
| **Enrichi** | + raisonnement IA complet |

Basculer avec le bouton "Enrichir" / "Vue simple".

---

## Actions

### Approuver

- **Bouton** : ✓ Approuver (vert)
- **Swipe** : Droite (mobile)
- **Raccourci** : `Enter` (après sélection)

L'email est traité selon l'action proposée.

### Rejeter

- **Bouton** : ✗ Rejeter (rouge)
- **Swipe** : Gauche (mobile)
- **Raccourci** : `Backspace`

L'email reste dans l'inbox, non traité.

### Ré-analyser (Autre)

- **Bouton** : 💡 Autre / Ré-analyser
- Permet de donner une **instruction spécifique** (ex: "Extrais aussi le numéro de facture")
- Déclenche un second passage de l'IA (Passe de Raffinement)
- Utile quand l'analyse automatique a manqué un détail important.

### Modifier

- **Bouton** : ✎ Modifier
- Ajuster l'action ou la destination avant approbation

### Snooze (Reporter)

- **Bouton** : ⏰ Snooze
- Choisir : 1h, 3h, demain, semaine prochaine
- L'item réapparaît à l'heure choisie

### Undo (Annuler)

Après approbation, un toast apparaît :
- Cliquer "Annuler" dans les 10 secondes
- L'action est révoquée

---

## Types d'Actions

| Action | Description |
|--------|-------------|
| **Archive** | Déplacer vers le dossier **Archive** unique. Scapin utilise des métadonnées (catégories) pour le classement au lieu de dossiers imbriqués complexes. |
| **Delete** | Déplacer vers la Corbeille |
| **Reply** | Créer un brouillon de réponse |
| **Task** | Créer une tâche (OmniFocus si configuré) |
| **Flag** | Marquer comme important |
| **Forward** | Transférer à quelqu'un |

---

## Entités Extraites

Scapin identifie automatiquement :

| Type | Description | Badge |
|------|-------------|-------|
| **Personne** | Nom ou email d'un contact | 👤 bleu |
| **Date** | Échéance, rappel ou événement | 📅 orange |
| **Projet** | Nom d'un projet actif ou passé | 📁 violet |
| **Engagement** | Promesse ou action à faire | ✅ bleu |
| **Demande** | Requête formulée par l'expéditeur | 🙋 violet |
| **Décision** | Arbitrage ou choix acté | ⚖️ jaune |
| **Fait** | Information factuelle importante | 📌 gris |
| **Montant** | Prix, facture, devis | 💰 vert |
| **Événement** | Réunion, appel, rendez-vous | 🍕 rouge |
| **Lieu** | Adresse, ville, bureau | 📍 rouge |
| **Organisation** | Entreprise ou institution | 🏢 gris |
| **Logiciel** | Outil technique mentionné | 💻 bleu |
| **Lien** | URL ou ressource externe | 🔗 cyan |
| **Contact** | Coordonnées de contact | 📞 vert |

### Notes Proposées

Si une entité n'existe pas dans votre base :
- Scapin propose de créer une note
- Badge "Auto" si confiance > 90%

#### Badge "Requis"

Certains enrichissements sont marqués **Requis** (badge rouge/orange) :

| Type | Quand "Requis" ? |
|------|-----------------|
| **Deadline** | Toujours requis (information critique) |
| **Engagement** | Si importance haute ou moyenne |
| **Demande** | Si importance haute ou moyenne |
| **Décision** | Si importance haute |
| **Montant** | Si importance haute |
| **Fait** | Si importance haute |
| **Événement** | Si importance haute |

**Pourquoi c'est important ?**

Les enrichissements "Requis" contiennent des informations qui seraient **perdues** si l'email était archivé sans les extraire. Scapin garantit que :

1. Les enrichissements requis sont exécutés **avant** l'archivage
2. Si un enrichissement requis échoue, l'email reste dans le Flux (pas d'archivage)
3. Les enrichissements optionnels sont exécutés en arrière-plan (best-effort)

> **Conseil** : Si vous voyez beaucoup de badges "Requis", prenez le temps de vérifier ces enrichissements avant d'approuver.

### Tâches Proposées

Pour les emails demandant une action :
- Scapin extrait la tâche
- Propose projet et échéance

---

## Mode Focus

Pour traiter les emails en immersion :

1. Cliquer "Mode Focus" ou `/flux/focus`
2. Un email à la fois, plein écran
3. Corps complet visible
4. Actions accessibles au clavier
5. Navigation : ← →

---

## Vue Détail

Cliquer sur un item pour voir :

- Corps complet de l'email (HTML rendu)
- Historique du thread
- Pièces jointes
- Actions disponibles
- Raisonnement IA détaillé
- **Contexte utilisé** (v2.2.2+)

### Transparence du Contexte (v2.2.2)

La vue détail affiche maintenant le contexte qui a influencé l'analyse IA :

#### Influence du Contexte

Section qui explique **comment** le contexte a été utilisé :

| Champ | Description |
|-------|-------------|
| **Notes utilisées** | Liste des notes PKM consultées |
| **Explication** | Résumé de l'influence sur l'analyse |
| **Confirmations** | Informations confirmées par le contexte |
| **Contradictions** | Incohérences détectées |
| **Infos manquantes** | Données recherchées mais non trouvées |

#### Contexte Brut (collapsible)

Pour le debugging technique, une section dépliable affiche les données brutes :

- **Entités recherchées** : Personnes, projets, concepts identifiés
- **Sources consultées** : Notes, Calendrier, OmniFocus, Email
- **Notes trouvées** : Détail de chaque note avec score de pertinence
- **Événements calendrier** : Réunions et rendez-vous liés
- **Tâches OmniFocus** : Actions en cours associées

> **Conseil** : Utilisez cette section pour vérifier que Scapin consulte bien les bonnes notes et comprend correctement le contexte de vos emails

---

## Filtres

### Par Status

- **En attente** : À traiter
- **Approuvés** : Historique des validations
- **Rejetés** : Historique des refus

### Par Source

- Email
- Teams
- Calendrier

### Par Urgence

- Urgent (rouge)
- Normal
- Basse priorité

---

## Traitement en Lot

### Sélection Multiple

1. Cocher les items
2. Actions groupées : Approuver tout, Rejeter tout

### Raccourcis

| Touche | Action |
|--------|--------|
| `a` | Approuver sélectionné |
| `r` | Rejeter sélectionné |
| `s` | Snooze |
| `↑/↓` | Naviguer |
| `Space` | Sélectionner |

---

## Conseils

1. **Traitez régulièrement** — 2-3 fois par jour, 5 min chaque
2. **Faites confiance aux scores élevés** — > 85% est généralement correct
3. **Utilisez les raccourcis** — Plus rapide que la souris
4. **Vérifiez les entités** — Elles enrichissent votre base de notes
