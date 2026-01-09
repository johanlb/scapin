# 5. Journal

Le **Journal** est votre espace de réflexion quotidienne. C'est aussi le cœur de la boucle d'apprentissage de Scapin.

---

## Principe

```
Journée vécue → Scapin pré-remplit → Vous complétez → Scapin apprend
```

Le journaling quotidien (~15 minutes) permet à Scapin de :
- Apprendre vos préférences
- Calibrer ses analyses
- Améliorer ses suggestions

---

## Accès

- **Web** : `/journal`
- **CLI** : `scapin journal --interactive`

---

## Structure

### Résumé du Jour

Scapin génère automatiquement :
- Emails traités (approuvés/rejetés)
- Messages Teams importants
- Réunions effectuées
- Tâches complétées

### Questions

Scapin pose des questions sur :

#### Décisions

*"Vous avez approuvé l'email de Jean concernant le Projet Alpha. Était-ce la bonne décision ?"*

- Confirmer : Scapin renforce ce pattern
- Corriger : Scapin ajuste son modèle

#### Préférences

*"Comment préférez-vous traiter les newsletters ?"*

- Archive automatique
- Revue hebdomadaire
- Suppression

#### Patterns

*"J'ai remarqué que vous archivez toujours les emails de facturation dans Finance/Factures. Dois-je le faire automatiquement ?"*

---

## Multi-Sources

### Tabs

| Tab | Contenu |
|-----|---------|
| **Email** | Résumé emails, corrections |
| **Teams** | Messages, discussions |
| **Calendrier** | Réunions, notes |
| **OmniFocus** | Tâches, projets |

### Corrections

Pour chaque source, vous pouvez :
- Corriger une décision passée
- Ajuster une catégorisation
- Modifier une priorité

---

## Types de Questions

### Pattern

Questions sur les comportements détectés :
- "Toujours archiver les emails de X ?"
- "Priorité haute pour les messages de Y ?"

### Préférence

Questions sur vos goûts :
- "Format de briefing préféré ?"
- "Fréquence de notifications ?"

### Calibration

Questions pour affiner la confiance :
- "Cette analyse était-elle correcte ?"
- "Ce score de confiance vous semble-t-il juste ?"

---

## Revues Périodiques

### Revue Hebdomadaire

Chaque dimanche (ou jour configuré) :
- Résumé de la semaine
- Patterns détectés
- Score de productivité
- Suggestions d'amélioration

### Revue Mensuelle

Fin de mois :
- Tendances sur 30 jours
- Progression des objectifs
- Évolution des sources
- Recommandations

---

## Calibration Sganarelle

Le module d'apprentissage utilise vos feedbacks pour :

### Ajuster les Seuils

- Email urgent : Qu'est-ce qui est vraiment urgent ?
- Confiance : Quand Scapin peut-il agir seul ?

### Améliorer les Analyses

- Catégorisation des expéditeurs
- Détection des sujets importants
- Priorisation des sources

### Métriques

| Métrique | Description |
|----------|-------------|
| **Précision** | % de décisions correctes |
| **Rappel** | % d'items importants détectés |
| **Calibration** | Corrélation confiance/exactitude |

---

## Export

### Formats

- **Markdown** : Journal complet en .md
- **JSON** : Données structurées

### Usage

```bash
scapin journal --date 2026-01-09 --format markdown --output journal.md
```

---

## Conseils

1. **15 minutes chaque soir** — Routine idéale
2. **Soyez honnête** — Corrigez vraiment les erreurs
3. **Expliquez vos choix** — "Rejeté car spam" aide Scapin
4. **Consultez les revues** — Insights sur vos habitudes
5. **Patience** — L'apprentissage prend 2-4 semaines
