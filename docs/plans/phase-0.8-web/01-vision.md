# 01 - Vision et Concept

[< Retour à l'index](./00-index.md)

---

## Résumé Exécutif

**Objectif** : Créer une interface web **event-centric** pour Scapin avec SvelteKit + TailwindCSS.

**Vision Centrale** : Scapin est un processeur d'événements. L'interface reflète ce paradigme unifié — un flux unique plutôt que des silos par source.

**Dépendance** : Phase 0.7 (API Jeeves) — ✅ Complétée

---

## Pourquoi Event-Centric ?

### Le problème des silos

Avec une approche classique (page Emails, page Teams, page Calendar), l'utilisateur doit :
- Naviguer entre plusieurs pages pour avoir une vue complète
- Faire du context-switching mental constant
- Risquer d'oublier des éléments dans un silo peu visité

### La solution : flux unifié

Tous les événements arrivent dans **un seul flux chronologique** :

| Avantage | Description |
|----------|-------------|
| **Vue d'ensemble rapide** | En 30 secondes, voir tout ce qui nécessite attention |
| **Priorisation naturelle** | Les événements urgents remontent, peu importe la source |
| **Moins de charge cognitive** | Un seul endroit à surveiller |
| **Patterns visibles** | Voir les corrélations entre sources (email + réunion sur même sujet) |

---

## Les 4 Vues du Flux

| Vue | Contenu | Usage |
|-----|---------|-------|
| **À traiter** | Événements nécessitant action humaine (confiance < seuil) | Travail quotidien |
| **Traités** | Actions exécutées automatiquement par Scapin | Vérification |
| **Historique** | Timeline complète de tous les événements | Recherche |
| **Rejets** | Actions refusées par l'utilisateur | Apprentissage Sganarelle |

---

## Workflows Utilisateur Principaux

### 1. Routine du matin (5 min)
```
1. Ouvrir Scapin → Page Briefing (home)
2. Lire le résumé IA du jour
3. Voir les réunions à venir
4. Traiter les 2-3 événements urgents
5. Commencer sa journée informé
```

### 2. Traitement du flux (10-15 min)
```
1. Aller dans Flux → "À traiter"
2. Pour chaque événement :
   - Voir la proposition de Scapin
   - Approuver / Modifier / Rejeter
3. Les rejets alimentent l'apprentissage
```

### 3. Session Journal (15 min, fin de journée)
```
1. Aller dans Journal
2. Scapin a pré-rempli les événements du jour
3. Répondre aux questions ciblées
4. Corriger les erreurs de catégorisation
5. Les corrections améliorent Scapin
```

### 4. Consultation rapports (5 min, hebdo)
```
1. Aller dans Rapports
2. Consulter le rapport hebdomadaire
3. Voir les tendances et patterns
4. Exporter si besoin (PDF/Markdown)
```

### 5. Discussion libre avec Scapin
```
1. Ouvrir le panel Chat (toujours accessible)
2. Poser une question en langage naturel
3. Scapin répond avec contexte
4. Continuer la conversation ou fermer le panel
```

---

## Architecture de l'Interface

### Layout Principal

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Header : Logo + Status Scapin + Recherche (Cmd+K) + User              │
├────────────┬────────────────────────────────────┬───────────────────────┤
│            │                                    │                       │
│  SIDEBAR   │       CONTENU PRINCIPAL            │    CHAT SCAPIN        │
│            │                                    │    (réductible)       │
│  Briefing  │   Varie selon la page :            │                       │
│  Flux      │   - Briefing du jour               │   ┌───────────────┐   │
│  Notes     │   - Liste événements               │   │ Conversation  │   │
│  Discuss.  │   - Éditeur de note                │   │ avec Scapin   │   │
│  Journal   │   - Chat complet                   │   │               │   │
│  Rapports  │   - Dashboard stats                │   │               │   │
│  Stats     │   - Paramètres                     │   └───────────────┘   │
│  Settings  │                                    │   [Écrire un msg...]  │
│            │                                    │                       │
└────────────┴────────────────────────────────────┴───────────────────────┘
```

### Panel Chat (style Claude Desktop)

Le chat avec Scapin est un **panel latéral permanent** qui peut être :
- **Ouvert** : Visible à droite, permet de discuter tout en consultant le contenu
- **Réduit** : Icône flottante en bas à droite, un clic l'ouvre
- **Plein écran** : Via la page `/discussions` pour les longues conversations

**Avantages** :
- Poser une question sur l'événement qu'on regarde
- Garder le contexte de la conversation entre pages
- Accès rapide sans quitter sa tâche

---

## Principes UX

### 1. Information en 3 Niveaux (Progressive Disclosure)

| Niveau | Temps | Ce qu'on voit | Exemple (événement email) |
|--------|-------|---------------|---------------------------|
| **1** | 30s | Résumé actionnable | "Email de Marie — Budget Q2 — Archiver ✓" |
| **2** | 2min | Contexte et options | Sujet complet, extrait, raison de la proposition, alternatives |
| **3** | Variable | Détails complets | Email complet, historique avec Marie, fichiers liés |

**Implémentation** :
- Niveau 1 = Card dans la liste
- Niveau 2 = Panneau latéral au clic
- Niveau 3 = Page dédiée ou modal

### 2. Hiérarchie de l'Information

- **Urgent en haut** : Événements critiques visibles immédiatement
- **Badges colorés** : Rouge (urgent), Orange (important), Gris (normal)
- **Compteurs** : Nombre d'éléments à traiter visible dans la sidebar

### 3. Keyboard First

| Raccourci | Action |
|-----------|--------|
| `Cmd+K` | Recherche globale |
| `j/k` | Naviguer dans la liste |
| `a` | Approuver |
| `r` | Rejeter |
| `m` | Modifier |
| `u` | Annuler (undo) |
| `?` | Afficher aide raccourcis |

### 4. Feedback Immédiat

- **Toast notifications** : Confirmation des actions
- **Loading states** : Skeleton pendant le chargement
- **Optimistic updates** : UI mise à jour avant confirmation serveur

### 5. Prévention des Erreurs

- **Confirmations** : Pour actions destructrices (supprimer note, rejeter définitivement)
- **Undo** : Possibilité d'annuler les 5 dernières actions
- **Soft delete** : Les éléments vont dans une corbeille avant suppression définitive

---

## Journal vs Rapports

### Journal (interactif)

**But** : Améliorer Scapin via feedback quotidien

```
Session interactive (~15 min) :
1. Scapin pré-remplit avec les événements du jour
2. Questions ciblées : "Qui est Jean Martin ?", "Action correcte ?"
3. Johan répond et corrige
4. Corrections → Sganarelle apprend
```

**Page** : `/journal`

### Rapports (consultation)

**But** : Synthèses générées pour consultation

```
Rapports automatiques :
- Journalier : "12 emails traités, 3 réunions, 2 tâches créées"
- Hebdomadaire : "Tendances, temps par projet, taux d'approbation"
- Mensuel : "Évolution confiance, patterns détectés"
```

**Page** : `/rapports`

---

## Accessibilité

| Critère | Implémentation |
|---------|----------------|
| Contraste | WCAG AA minimum (4.5:1 texte, 3:1 UI) |
| Focus | Outline visible sur tous les éléments interactifs |
| Labels | Tous les inputs ont un label associé |
| ARIA | Attributs sur composants dynamiques |
| Clavier | Navigation complète sans souris |

---

## Performance

| Optimisation | Technique |
|--------------|-----------|
| Code splitting | Chargement par route (SvelteKit natif) |
| Lazy loading | Images et composants lourds |
| Preload | Données critiques (briefing) au login |
| Cache | Réponses API avec SWR pattern |
| Debounce | Recherche (300ms) pour éviter requêtes excessives |

---

## Responsive (Nice-to-have)

L'interface est conçue desktop-first mais reste utilisable sur tablette :

| Breakpoint | Adaptation |
|------------|------------|
| Desktop (>1200px) | Layout complet 3 colonnes |
| Tablette (768-1200px) | Chat en overlay, sidebar collapsible |
| Mobile (<768px) | Navigation bottom, contenu plein écran |

---

## Phase Ultérieure (0.9)

### Prédictions Scapin
- Anticipation intelligente : "Demain, ~8 emails à traiter"
- Suggestions proactives basées sur les patterns
- Alertes préventives

### Résumé Audio
- TTS pour écouter le briefing
- Utile pendant le café ou en mobilité
- Intégration future PWA mobile

---

[Suivant : Architecture >](./02-architecture.md)
