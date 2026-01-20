# 4. Notes

Les **Notes** sont le cœur de votre base de connaissances. Scapin utilise vos notes pour enrichir l'analyse des emails et vous aide à les maintenir à jour.

---

## Philosophie PKM

Scapin implémente une approche **PKM (Personal Knowledge Management)** inspirée de Zettelkasten, adaptée au contexte professionnel.

### Principes Fondamentaux

| Principe | Description |
|----------|-------------|
| **Centralisation** | Une note par entité (personne, projet) plutôt que des fragments épars |
| **Liens bidirectionnels** | Les wikilinks créent un réseau navigable |
| **Enrichissement continu** | Chaque email traité peut enrichir vos notes |
| **Révision active** | L'algorithme SM-2 maintient vos connaissances fraîches |

### Boucle Vertueuse Notes ↔ Emails

```
┌─────────────────────────────────────────────────────────────────┐
│                    BOUCLE D'ENRICHISSEMENT                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   📧 Email arrive                                                │
│        │                                                         │
│        ▼                                                         │
│   🔍 Scapin détecte "Marie Dupont"                              │
│        │                                                         │
│        ▼                                                         │
│   📚 Passepartout cherche [[Marie Dupont]]                      │
│        │                                                         │
│        ├──► Note trouvée → Contexte injecté dans l'analyse      │
│        │         │                                               │
│        │         ▼                                               │
│        │    🧠 Sancho analyse AVEC le contexte                  │
│        │         │                                               │
│        │         ▼                                               │
│        │    📝 Nouvel enrichissement proposé                    │
│        │         │                                               │
│        │         ▼                                               │
│        │    ✅ Vous validez → Note mise à jour                  │
│        │                                                         │
│        └──► Note absente → Scapin propose de la créer           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Exemple concret** :
1. Email de Marie Dupont concernant le Projet Alpha
2. Scapin trouve votre note `[[Marie Dupont]]` : *"Directrice technique chez Acme Corp"*
3. L'analyse utilise ce contexte : *"Email de la directrice technique, probablement important"*
4. Scapin extrait : *"Marie confirme le budget de 50k€"*
5. Enrichissement proposé pour `[[Projet Alpha]]` : *"Budget confirmé : 50 000€"*

---

## Structure

### Organisation : Stratégie "Project-First"

Scapin privilégie une organisation **centralisée** pour éviter la fragmentation. Au lieu de dizaines de petites notes atomiques, l'information est regroupée dans des notes "piliers" :

```
notes/
├── projets/           # Notes centrales pour chaque projet actif
│   ├── Projet_Alpha.md
│   └── Projet_Beta.md
├── domaines/          # Actifs, finances, santé, administration
│   ├── Maison.md      # Tout ce qui concerne le domicile
│   └── Fiscalité.md
├── relations/         # Fiches détaillées des contacts clés
│   ├── Jean_Dupont.md
│   └── Marie_Martin.md
└── journal/           # Entrées quotidiennes fusionnées
    └── 2026-01.md     # Journal mensuel
```

### Types de Notes

| Type | Usage | Icône |
|------|-------|-------|
| **Projet** | Initiatives, dossiers, chantiers | 📁 |
| **Personne** | Contacts clés, partenaires | 👤 |
| **Actif** | Biens, investissements, lieux | 🏠 |
| **Domaine** | Sujets transverses (Santé, Finance) | 🛡️ |
| **Réunion** | Comptes-rendus (souvent liés à un Projet) | 📅 |

---

## Interface

L'interface Notes est organisée en **3 colonnes** style Apple Notes :

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  🔍 Recherche globale (Cmd+K)                                         [×]   │
├───────────────┬─────────────────────┬────────────────────────────────────────┤
│ DOSSIERS      │ NOTES               │ CONTENU                                │
│ (224px)       │ (288px)             │ (flexible)                             │
├───────────────┼─────────────────────┼────────────────────────────────────────┤
│               │ 🔍 Rechercher...    │                                        │
│ 📁 Toutes     │                     │  # Marie Dupont                    ✏️  │
│               │ ┌─────────────────┐ │                                        │
│ 📌 Épinglées  │ │ 📌 Projet Alpha │ │  **Rôle** : Directrice technique       │
│   └ (3)       │ │    Modifié: 2h  │ │  **Entreprise** : [[Acme Corp]]        │
│               │ ├─────────────────┤ │                                        │
│ 📁 projets/   │ │ 👤 Marie Dupont │ │  ## Historique                         │
│   └ (12)      │ │    Modifié: 1j  │◄│                                        │
│               │ ├─────────────────┤ │  - 2026-01: Réunion kick-off           │
│ 📁 relations/ │ │ 👤 Jean Martin  │ │  - 2025-12: Premier contact            │
│   └ (45)      │ │    Modifié: 3j  │ │                                        │
│               │ ├─────────────────┤ │  ## Notes                              │
│ 📁 domaines/  │ │ 📁 Fiscalité    │ │                                        │
│   └ (8)       │ │    Modifié: 1s  │ │  Préfère les appels aux emails.        │
│               │ └─────────────────┘ │  Disponible le mardi après-midi.       │
│ 🗑️ Corbeille  │                     │                                        │
│   └ (2)       │                     │  [[Projet Alpha]] [[Acme Corp]]        │
├───────────────┴─────────────────────┼────────────────────────────────────────┤
│                                     │ [Écrire] [Aperçu] [Split]    🕐 🧹 💾  │
└─────────────────────────────────────┴────────────────────────────────────────┘
```

| Colonne | Contenu | Largeur |
|---------|---------|---------|
| **1** | Arbre de dossiers | 224px |
| **2** | Liste des notes + Recherche | 288px |
| **3** | Contenu de la note | Flexible |

### Arbre de Dossiers (Colonne 1)

- Navigation hiérarchique avec expansion/collapse
- Dossiers virtuels : "Toutes les notes" et "Supprimées récemment"
- Compteur de notes par dossier
- Créer dossiers avec clic droit
- Glisser-déposer pour organiser

### Notes Épinglées

Vos notes favorites en accès rapide.

### Recherche API (Colonne 2)

La barre de recherche en haut de la colonne 2 permet une recherche puissante dans toutes vos notes.

**Raccourci clavier** : `Cmd+K` (ou `Ctrl+K`)

**Fonctionnalités** :
- Recherche hybride : full-text + sémantique
- Debounce automatique (300ms)
- Score de pertinence affiché (badge coloré)
- Extraits avec highlights des termes trouvés
- Chemin du dossier affiché pour chaque résultat

**Actions** :
- `Escape` ou clic sur ✕ : Effacer la recherche
- Clic sur un résultat : Ouvre la note

### Édition du Titre (Colonne 3)

**Double-clic** sur le titre d'une note pour l'éditer directement.

| Action | Résultat |
|--------|----------|
| Double-clic sur titre | Passe en mode édition |
| `Enter` | Sauvegarde le titre |
| `Escape` | Annule les modifications |
| Clic ailleurs | Sauvegarde le titre |
| ✓ | Sauvegarde |
| ✕ | Annule |

---

## Éditeur Markdown

### Modes

| Mode | Description |
|------|-------------|
| **Écrire** | Édition pure Markdown |
| **Aperçu** | Rendu HTML |
| **Split** | Édition + aperçu côte à côte |

### Barre d'Outils

| Bouton | Raccourci | Action |
|--------|-----------|--------|
| **B** | `Cmd+B` | Gras |
| *I* | `Cmd+I` | Italique |
| `</>` | `Cmd+E` | Code |
| 🔗 | `Cmd+K` | Lien |
| [[]] | `Cmd+W` | Wikilink |

### Wikilinks

Créez des liens entre notes :

```markdown
Voir [[Jean Dupont]] pour le contexte du [[Projet Alpha]].
```

Les wikilinks sont cliquables dans l'aperçu.

### Auto-Save

- Sauvegarde automatique après 1 seconde d'inactivité
- Indicateur "Enregistré" / "Enregistrement..."

---

## Memory Cycles (v2.6)

Scapin utilise un système de **double cycle mémoire** basé sur l'algorithme SM-2 :

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEMORY CYCLES                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐         ┌──────────────────┐                         │
│   │    RETOUCHE      │         │     LECTURE      │                         │
│   │    (IA auto)     │         │    (Humain)      │                         │
│   └────────┬─────────┘         └────────┬─────────┘                         │
│            │                            │                                    │
│            ▼                            ▼                                    │
│   ┌──────────────────┐         ┌──────────────────┐                         │
│   │ • Enrichit       │         │ • Révise         │                         │
│   │ • Structure      │         │ • Répond aux Q   │                         │
│   │ • Résume         │         │ • Note qualité   │                         │
│   │ • Injecte Q      │         │ • Mémorise       │                         │
│   │ • Score qualité  │         │                  │                         │
│   └────────┬─────────┘         └────────┬─────────┘                         │
│            │                            │                                    │
│            └────────────┬───────────────┘                                    │
│                         ▼                                                    │
│                   ┌───────────┐                                              │
│                   │  FILAGE   │                                              │
│                   │ (Matin)   │                                              │
│                   └───────────┘                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cycle Retouche (IA)

La **Retouche** est le cycle d'amélioration automatique par l'IA. Elle tourne en arrière-plan (hors heures calmes 23h-7h) et améliore vos notes progressivement.

#### Actions Retouche

| Action | Description |
|--------|-------------|
| **Enrichir** | Ajoute des informations contextuelles |
| **Structurer** | Réorganise les sections pour plus de clarté |
| **Résumer** | Génère un résumé en tête de note |
| **Questions** | Injecte des questions pour vous |
| **Score** | Calcule un score de qualité (0-100%) |

#### Escalade de Modèles

L'IA utilise une escalade progressive selon la complexité :

| Modèle | Usage | Confiance |
|--------|-------|-----------|
| **Haiku** | Par défaut | ≥ 70% |
| **Sonnet** | Cas complexes | ≥ 50% |
| **Opus** | Cas critiques | < 50% |

#### Délai Initial

Les nouvelles notes ne sont pas retouchées immédiatement. Un délai de **1 heure** permet de terminer la création avant l'analyse IA.

### Cycle Lecture (Humain)

La **Lecture** est votre cycle de révision personnelle. Voir [Filage](02-briefing.md#filage-v26) pour le briefing matinal.

#### Démarrer une Lecture

1. Via le Filage matinal (`/briefing/filage`)
2. Via l'API : `POST /api/briefing/lecture/{note_id}/start`

#### Compléter une Lecture

1. Lisez la note attentivement
2. Répondez aux questions (si présentes)
3. Notez votre rappel (0-5)

| Note | Signification | Effet |
|------|---------------|-------|
| **5** | Parfait | Intervalle × 2.5 |
| **4** | Bon | Intervalle × 2.0 |
| **3** | Correct | Intervalle × 1.5 |
| **2** | Difficile | Reset 24h |
| **1** | Très difficile | Reset 24h |
| **0** | Oubli total | Reset 24h |

### Score de Qualité

Chaque note possède un **score de qualité** (0-100%) calculé automatiquement :

```
┌─────────────────────────────────────────────────────────────────┐
│  SCORE QUALITÉ                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Base                                 50 points                  │
│  + Nombre de mots (100-500)          +10 points                  │
│  + Résumé présent                    +15 points                  │
│  + Sections (×3 pts, max 15)         +15 points max              │
│  + Liens (×2 pts, max 10)            +10 points max              │
│  - Actions suggérées                 -5 pts chacune              │
│                                                                  │
│  TOTAL MAX                           100 points                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Badges de Qualité

| Score | Badge | Signification |
|-------|-------|---------------|
| 90-100% | 🌟 | Excellente |
| 70-89% | ✅ | Bonne |
| 50-69% | 🔶 | À améliorer |
| 0-49% | 🔴 | Lacunaire |

### Questions pour Johan

L'IA peut injecter des **questions personnalisées** pour combler les lacunes :

```markdown
## Questions pour Johan
- Quel est le budget exact du projet ?
- Quelle est la relation avec [[Marie Dupont]] ?
```

Ces questions :
- Apparaissent pendant les sessions de Lecture
- Peuvent être répondues directement dans l'interface
- Sont intégrées à la note une fois répondues
- Déclenchent une priorité haute dans le Filage

---

## Révision Espacée (SM-2) — Legacy

> **Note** : Cette section décrit l'ancien système de révision. Le nouveau système [Memory Cycles](#memory-cycles-v26) le remplace avec deux cycles distincts.

Scapin utilise l'algorithme **SuperMemo 2** pour vous aider à maintenir vos notes à jour.

### Principe

1. Nouvelle note → Révision dans 2h (Retouche) ou 24h (Lecture)
2. Bonne révision → Intervalle augmente
3. Mauvaise révision → Retour au début

### Page Révision (Legacy)

Accès : `/notes/review` ou widget Dashboard

1. Note affichée
2. Réfléchir (sans voir le contenu)
3. Révéler le contenu
4. Noter la qualité (1-6)
5. Note suivante

### Raccourcis Révision

| Touche | Action |
|--------|--------|
| `1-6` | Noter la qualité |
| `←/→` | Naviguer |
| `s` | Reporter (snooze) |
| `Escape` | Quitter |

---

## Historique (Git)

Chaque note est versionnée avec Git.

### Voir l'Historique

1. Ouvrir une note
2. Cliquer 🕐 (Historique)
3. Liste des versions

### Comparer

1. Sélectionner deux versions
2. Voir le diff (ajouts/suppressions)

### Restaurer

1. Sélectionner une version
2. Cliquer "Restaurer"
3. Confirmer

---

## Synchronisation Apple Notes

### Import

1. Aller dans Notes
2. Cliquer "Sync Apple Notes"
3. Attendre la synchronisation

### Mapping

- Dossier Apple Notes → Dossier Scapin
- Contenu HTML → Markdown

### Bidirectionnel

- Modifications dans Scapin → Apple Notes
- Modifications dans Apple Notes → Scapin
- Conflits résolus par date de modification

---

## Revue Hygiène

Le bouton **🧹 Revue Hygiène** analyse la qualité de la note sélectionnée et suggère des améliorations.

### Lancer une Revue

1. Sélectionner une note
2. Cliquer sur le bouton 🧹 dans la barre d'outils

### États du Bouton

| État | Apparence | Signification |
|------|-----------|---------------|
| **Idle** | 🧹 | Prêt pour la revue |
| **Loading** | ⏳ | Analyse en cours |
| **Issues** | 🧹 + Badge rouge | Problèmes détectés |
| **Clean** | ✨ | Note impeccable |

### Types de Problèmes Détectés

| Type | Description |
|------|-------------|
| **Lien cassé** | Wikilink vers note inexistante |
| **Orpheline** | Note sans liens entrants |
| **Obsolète** | Contenu potentiellement périmé |
| **Incomplet** | Section manquante ou vide |
| **Doublon** | Information dupliquée ailleurs |
| **Format** | Problème de formatage Markdown |

### Panneau de Résultats

Le panneau affiche chaque problème avec :
- **Icône de sévérité** : 🔴 Erreur, 🟡 Avertissement, ℹ️ Info
- **Description** du problème
- **Suggestion** de correction (optionnel)
- **Confiance** de la détection (0-100%)

### Actions

- Cliquer sur un problème pour voir les détails
- Bouton "Corriger" pour appliquer une suggestion automatique
- Bouton "Ignorer" pour masquer un problème

---

## Média (Images, Audio, Vidéo, PDF)

Les notes synchronisées depuis Apple Notes peuvent contenir des médias embarqués.

### Types Supportés

| Type | Extensions | Affichage |
|------|------------|-----------|
| **Images** | jpg, png, gif, webp, heic | Inline avec lazy loading |
| **Audio** | m4a, mp3, wav | Lecteur audio natif |
| **Vidéo** | mp4, mov | Lecteur vidéo natif |
| **PDF** | pdf | Iframe intégrée |

### Syntaxe Apple Media

Les médias Apple Notes utilisent le protocole `apple-media://` :

```markdown
![Description](apple-media://attachment-uuid)
```

Scapin convertit automatiquement ces URLs vers `/api/media/{uuid}` pour l'affichage.

### Cache et Performance

- **Lazy loading** : Les images ne sont chargées que lorsqu'elles sont visibles
- **Cache 24h** : Les médias sont mis en cache côté navigateur
- **Optimisation** : Les grandes images sont servies avec des headers de cache appropriés

---

## Enrichissement Automatique

### Sources

Scapin enrichit vos notes depuis :
- Emails traités
- Messages Teams
- Événements calendrier
- Web (recherche)

### Processus

1. Scapin détecte une entité (ex: personne)
2. Cherche la note existante
3. Propose un enrichissement
4. Vous validez ou modifiez
5. Note mise à jour

### Auto-Apply

Si confiance > 90% :
- Enrichissement appliqué automatiquement
- Badge "Auto" dans l'historique
- Révisable à tout moment

---

## Conseils

1. **Utilisez les wikilinks** — Créez un réseau de connaissances
2. **Faites votre Filage** — 10 min de Lectures chaque matin
3. **Répondez aux questions** — Enrichissez vos notes progressivement
4. **Laissez l'IA travailler** — Les Retouches améliorent vos notes automatiquement
5. **Visez 80% de qualité** — Le score vous guide vers des notes complètes
6. **Épinglez l'essentiel** — Accès rapide aux notes clés
