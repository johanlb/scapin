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
| **Archive** | Déplacer vers Archive/[Année]/[Catégorie] |
| **Delete** | Déplacer vers Corbeille |
| **Reply** | Créer un brouillon de réponse |
| **Task** | Créer une tâche (OmniFocus si configuré) |
| **Flag** | Marquer comme important |
| **Forward** | Transférer à quelqu'un |

---

## Entités Extraites

Scapin identifie automatiquement :

| Type | Exemple | Badge |
|------|---------|-------|
| **Personne** | Jean Dupont | 👤 bleu |
| **Date** | 15 janvier 2026 | 📅 orange |
| **Projet** | Projet Alpha | 📁 violet |
| **Montant** | 1 500 € | 💰 vert |
| **Organisation** | Acme Inc. | 🏢 gris |
| **URL** | https://... | 🔗 cyan |

### Notes Proposées

Si une entité n'existe pas dans votre base :
- Scapin propose de créer une note
- Badge "Auto" si confiance > 90%

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
