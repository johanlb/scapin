# Guide Utilisateur Scapin

**Version** : 3.1
**Dernière mise à jour** : Janvier 2026

---

## Nouveautés v3.1 — Questions Stratégiques

- **Questions Stratégiques** : Les valets identifient maintenant des questions nécessitant votre réflexion
- **Accumulation multi-valets** : Chaque valet contribue ses observations (Grimaud, Bazin, Planchet, Mousqueton)
- **Intégration PKM** : Les questions sont liées à une note thématique pour un suivi naturel

Voir [3. Péripéties](03-peripeties.md#questions-stratégiques-v31) pour les détails.

---

## Nouveautés v3.0 — Four Valets

- **Architecture Four Valets** : Nouveau pipeline Grimaud → Bazin → Planchet → Mousqueton
- **Grimaud** : Observation silencieuse et extraction brute
- **Bazin** : Enrichissement contextuel avec les mémoires
- **Planchet** : Critique et validation
- **Mousqueton** : Arbitrage final

Voir [6. Architecture](06-architecture.md#architecture-four-valets-v30) pour les détails.

---

## Nouveautés v2.6 — Memory Cycles

- **Filage** : Briefing matinal intelligent avec max 20 Lectures prioritaires
- **Lecture** : Sessions de révision espacée avec questions personnalisées
- **Retouche** : Amélioration automatique IA des notes (Haiku → Sonnet → Opus)
- **Score Qualité** : Évaluation 0-100% de la complétude des notes

Voir [2. Briefing](02-briefing.md#filage-v26) et [4. Notes](04-notes.md#memory-cycles-v26) pour les détails.

---

## Nouveautés v2.5

- **Vue Élément Unique Enrichie** : Timestamps détaillés, avatar expéditeur, badges de complexité et sections contexte visibles par défaut
- **Transparence améliorée** : L'influence du contexte sur l'analyse est maintenant affichée directement
- **Pièces jointes** : Affichage intégré dans la vue élément

Voir [3. Péripéties](03-peripeties.md#vue-élément-unique-enrichie-v25) pour les détails.

---

## Bienvenue

Scapin est votre **gardien cognitif personnel** — un assistant intelligent qui transforme le flux constant d'emails, messages et informations en connaissances organisées et actions pertinentes.

> *"Prendre soin de vous mieux que vous-même."*

Inspiré du valet rusé de Molière, Scapin anticipe vos besoins, organise vos informations et vous libère de la charge mentale des tâches répétitives.

---

## Table des Matières

| Section | Description |
|---------|-------------|
| [1. Démarrage Rapide](01-demarrage.md) | Installation, connexion, premiers pas |
| [2. Briefing](02-briefing.md) | Briefing matinal, pré-réunion |
| [3. Péripéties](03-peripeties.md) | Traitement des emails et messages |
| [4. Notes](04-notes.md) | Base de connaissances, révision espacée |
| [5. Journal](05-journal.md) | Journaling quotidien, boucle de feedback |
| [6. Architecture](06-architecture.md) | Les valets, pipeline cognitif |
| [7. Configuration](07-configuration.md) | Réglages, intégrations |
| [8. Dépannage](08-troubleshooting.md) | Diagnostic erreurs, script `view_errors.py` |
| [9. Canevas](09-canevas.md) | Contexte permanent (Profile, Goals, Projects) |

---

## Concepts Clés

### Information en 3 Niveaux

Scapin présente l'information selon votre besoin immédiat :

| Niveau | Temps | Usage |
|--------|-------|-------|
| **Niveau 1** | 30 secondes | Décision rapide, aperçu |
| **Niveau 2** | 2 minutes | Contexte, options |
| **Niveau 3** | Variable | Détails complets, analyse |

### Les Valets

Scapin utilise une équipe de "valets" spécialisés :

- **Trivelin** — Perception et triage des événements
- **Sancho** — Raisonnement et analyse IA
- **Passepartout** — Base de connaissances
- **Planchet** — Planification des actions
- **Figaro** — Exécution des actions
- **Sganarelle** — Apprentissage continu
- **Frontin** — API REST et interface CLI

### Boucle Cognitive

```
Événement → Analyse IA → Contexte Notes → Action → Feedback → Amélioration
```

Chaque interaction enrichit le système et améliore les futures analyses.

---

## Navigation Rapide

### Raccourcis Clavier

| Raccourci | Action |
|-----------|--------|
| `Cmd+K` / `Ctrl+K` | Recherche globale |
| `?` | Aide raccourcis |
| `Escape` | Fermer modal/panneau |
| `1-6` | Noter révision (page Notes Review) |
| `L` | Terminer Lecture (page Filage) |

### Gestes Mobile

| Geste | Action |
|-------|--------|
| Swipe droite | Approuver |
| Swipe gauche | Rejeter |
| Pull down | Rafraîchir |
| Long press | Actions contextuelles |

---

## Support

- **Documentation technique** : [ARCHITECTURE.md](../../ARCHITECTURE.md)
- **Philosophie** : [DESIGN_PHILOSOPHY.md](../DESIGN_PHILOSOPHY.md)
- **Issues** : [GitHub Issues](https://github.com/johanlb/scapin/issues)
