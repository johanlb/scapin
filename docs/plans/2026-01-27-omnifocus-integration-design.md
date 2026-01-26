# Intégration OmniFocus

**Date** : 27 janvier 2026
**Statut** : Design validé
**Auteur** : Johan + Claude

---

## Résumé exécutif

Scapin s'intègre avec OmniFocus pour combiner le meilleur des deux mondes :
- **OmniFocus** = Actions (quoi faire, deadlines, séquences, revue GTD)
- **Scapin** = Contexte (qui, pourquoi, historique, relations)

**Fonctionnalités clés** :
- Création automatique de tâches OF depuis les emails analysés
- Affichage des tâches du jour dans le briefing Bazin
- Météo projets enrichie avec données OF
- Synchronisation bidirectionnelle des engagements

---

## Contexte

### Usage OmniFocus de Johan

Johan utilise OmniFocus en mode **GTD complet** :
- Inbox pour la capture
- Projets organisés par domaines (Personnel, Work, AWCS, etc.)
- Tags incluant des personnes (prénom, rangés par type)
- Revue hebdomadaire
- Horizons GTD (Areas of Focus, Goals, Projects)

### Principe de séparation

| Système | Responsabilité |
|---------|----------------|
| **OmniFocus** | Quoi faire — Actions, deadlines, séquences, revue |
| **Scapin** | Contexte — Qui, pourquoi, historique, relations |

Pas de duplication. Chaque système fait ce qu'il fait le mieux.

---

## Architecture technique

### Accès à OmniFocus

| Méthode | Choix |
|---------|-------|
| **API** | OmniFocus Automation API (JavaScript) |
| **Prérequis** | OmniFocus Pro |
| **Accès** | Bidirectionnel (lecture + écriture) |

### Module Scapin

```
src/trivelin/omnifocus/           # Sous-module de Trivelin (perception)
├── __init__.py
├── client.py                     # Client Automation API
├── sync.py                       # Synchronisation périodique
├── task_creator.py               # Création de tâches
├── project_mapper.py             # Mapping notes ↔ projets OF
└── models.py                     # Modèles de données OF
```

### Synchronisation

| Mode | Fréquence | Usage |
|------|-----------|-------|
| **Périodique** | Toutes les 15-30 min | Arrière-plan, données fraîches |
| **À la demande** | Manuel | Refresh avant briefing, sur action |

---

## Flux Scapin → OmniFocus

### Création automatique de tâches

Quand Scapin détecte un engagement/action dans un email :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLUX : Email → Tâche OmniFocus                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Email reçu de Marc : "Peux-tu m'envoyer le budget Q2 ?"                 │
│                                                                             │
│  2. Scapin analyse → Détecte action : "Envoyer budget Q2"                   │
│     → Personne : Marc Dupont                                                │
│     → Deadline : non spécifiée                                              │
│     → Projet probable : TechCorp ou Projet Alpha                            │
│                                                                             │
│  3. Création tâche OmniFocus :                                              │
│     ┌─────────────────────────────────────────────────────────────────┐     │
│     │ Titre : Envoyer budget Q2 à Marc                                │     │
│     │ Projet : Projet Alpha (auto-détecté) ou Inbox                   │     │
│     │ Tags : scapin, Marc D.                                          │     │
│     │ Note : Source: [lien email Scapin]                              │     │
│     │        Contexte: Budget Q2 pour TechCorp                        │     │
│     │ Due : (si mentionnée)                                           │     │
│     └─────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│  4. Lien créé : Engagement Scapin ↔ Tâche OF                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Format de la tâche créée

| Champ OF | Contenu |
|----------|---------|
| **Titre** | Action reformulée clairement |
| **Projet** | Auto-assigné si match trouvé, sinon Inbox |
| **Tags** | `scapin` + tag personne si applicable |
| **Note** | Lien vers email Scapin + contexte extrait |
| **Due date** | Si mentionnée dans l'email |
| **Flag** | Si urgent détecté |

### Création manuelle

Bouton "Créer tâche OF" disponible sur :
- Les emails (même sans action détectée)
- Les notes (pour créer une tâche liée)

---

## Flux OmniFocus → Scapin

### Tâches du jour dans Bazin

Le briefing matinal affiche les tâches OF du jour :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ✅ TÂCHES DU JOUR (OmniFocus)                                              │
│  ───────────────────────────────────────────────────────────────────────    │
│  🔴 Envoyer budget Q2 à Marc (due aujourd'hui)           [Voir dans OF]     │
│  🟡 Relire contrat Gii                                   [Voir dans OF]     │
│  ⚪ Appeler garage pour révision                         [Voir dans OF]     │
│                                                                             │
│  → 3 tâches flaggées, 12 disponibles                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Météo projets enrichie

Combinaison Scapin (contexte) + OF (état tâches) :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📊 MÉTÉO PROJETS                                                           │
│  ───────────────────────────────────────────────────────────────────────    │
│  🟢 Projet Alpha — 3 tâches restantes, prochaine action définie             │
│      Contexte Scapin : RDV avec Marc demain                                 │
│  🟡 Vente Nautil — 5 tâches, bloqué (en attente)                            │
│      Contexte Scapin : Attente réponse acheteur depuis 5j                   │
│  🔴 Migration serveur — 12 tâches, aucune action depuis 2 sem               │
│      Contexte Scapin : Deadline J-3                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Indicateurs de santé projet (depuis OF)

| Indicateur | Source OF |
|------------|-----------|
| Nombre de tâches restantes | Count tasks remaining |
| Prochaine action définie | Has next action |
| Bloqué | Tasks with "waiting" tag or on hold |
| Activité récente | Last completed task date |

---

## Mapping Notes Scapin ↔ OmniFocus

### Projets

**Méthode : Auto par nom + override frontmatter**

1. Scapin cherche un projet OF avec nom similaire
2. Si trouvé → association automatique
3. Si ambiguïté ou besoin de personnaliser → frontmatter

```yaml
---
title: Vente Nautil 6
type: projet
omnifocus_project: Vente de Nautil 6
---
```

### Personnes (Tags)

**Structure OF existante :**
```
Tags/
├── Collègues/
│   ├── Marc
│   └── Sophie
├── Amis/
│   └── Damien
├── Famille/
│   └── Maman
└── ...
```

**Mapping dans le frontmatter de la fiche Personne :**

```yaml
---
title: Marc Dupont
type: personne
omnifocus_tag: Marc D.
---
```

**Gestion des homonymes :**
- Suffixe si conflit : "Marc D." ou "Marc (TechCorp)"
- Stocké dans le frontmatter pour éviter l'ambiguïté

---

## Synchronisation des engagements

### Création

```
Email → Scapin détecte engagement → Crée tâche OF → Lie les deux
```

L'engagement Scapin stocke l'ID de la tâche OF :

```yaml
engagement:
  id: eng_123
  content: "Envoyer budget Q2 à Marc"
  source: email_456
  omnifocus_task_id: "task_abc123"
  status: pending
```

### Complétion

```
Tâche complétée dans OF → Sync → Scapin met à jour l'engagement
```

```yaml
engagement:
  id: eng_123
  content: "Envoyer budget Q2 à Marc"
  omnifocus_task_id: "task_abc123"
  status: completed
  completed_at: 2026-01-27T14:30:00Z
```

### Suppression

Si la tâche est supprimée dans OF :
- L'engagement Scapin reste (historique)
- Marqué comme "annulé" ou "supprimé dans OF"

---

## Interface utilisateur

### Briefing Bazin

Section "Tâches du jour" ajoutée au briefing matinal.

### Bouton création

Sur emails et notes :
```
[Créer tâche OF]
```

Ouvre un formulaire pré-rempli :
- Titre suggéré
- Projet suggéré
- Tags suggérés
- Possibilité de modifier avant création

### Lien vers OF

Bouton `[Voir dans OF]` ouvre OmniFocus directement sur la tâche/projet.

URL scheme : `omnifocus:///task/task_id`

---

## Configuration

### Paramètres utilisateur

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| `omnifocus_enabled` | true | Activer l'intégration |
| `sync_interval_minutes` | 15 | Fréquence sync périodique |
| `auto_create_tasks` | true | Créer tâches auto depuis emails |
| `default_project` | "Inbox" | Projet si pas de match |
| `scapin_tag` | "scapin" | Tag pour tâches créées par Scapin |

### Mapping personnalisé

Table de mapping accessible dans les paramètres :

| Note Scapin | Projet OmniFocus |
|-------------|------------------|
| AWCS | AWCS |
| Projet Alpha | Work > Projet Alpha |
| ... | ... |

---

## Coûts et performance

### Impact performance

| Opération | Fréquence | Impact |
|-----------|-----------|--------|
| Sync périodique | 15 min | Faible (lecture OF locale) |
| Création tâche | Par email avec action | Faible (écriture locale) |
| Refresh à la demande | Manuel | Instantané |

### Pas de coût API

OmniFocus Automation API est locale (pas de cloud), donc :
- Pas de coût supplémentaire
- Pas de latence réseau
- Fonctionne offline

---

## Questions ouvertes

1. **Projets archivés** — Scapin doit-il voir les projets OF archivés ?
2. **Perspectives** — Utiliser les perspectives OF pour filtrer ?
3. **Recurring tasks** — Comment gérer les tâches récurrentes ?
4. **Conflits** — Que faire si mapping ambigu (plusieurs projets similaires) ?

---

## Prochaines étapes

1. Créer le module `src/trivelin/omnifocus/`
2. Implémenter le client Automation API (JavaScript bridge)
3. Implémenter la sync périodique
4. Ajouter création auto de tâches dans le pipeline d'analyse
5. Intégrer dans Bazin (briefing matinal)
6. Ajouter météo projets enrichie
7. UI : bouton création manuelle
8. Tests avec données réelles

---

## Relation avec les autres modules

| Module | Interaction |
|--------|-------------|
| **Trivelin** | Héberge le sous-module omnifocus (perception externe) |
| **Sancho** | Détecte les actions dans les emails → déclenche création OF |
| **Bazin** | Affiche tâches du jour et météo projets enrichie |
| **Passepartout** | Stocke le mapping notes ↔ OF, met à jour engagements |

---

*Document créé le 27 janvier 2026*
