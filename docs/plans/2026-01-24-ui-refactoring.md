# Plan de Refactoring UI - Scapin v4

**Créé** : 24 janvier 2026
**Mis à jour** : 27 janvier 2026
**Statut** : En cours

## Objectif

Refactoriser les composants UI volumineux, éliminer les duplications, et créer les composants pour les nouvelles features (Grimaud, Bazin, Chat, OmniFocus).

## Décisions Clés

| Aspect | Choix |
|--------|-------|
| **Stratégie migration** | Directe (pas de période de transition) |
| **Tests** | Unitaires Vitest + E2E existants |
| **Cards** | BaseCard complet + utilitaires |
| **Priorité** | Fondations génériques → Nouvelles features → Refactoring existant |

---

## Vue d'Ensemble des Phases

> **Note** : Ce plan UI dépend de la [Master Roadmap](./2026-01-27-master-roadmap.md). Les phases 3-6 (nouvelles features) ne peuvent être implémentées qu'après leur backend respectif.

| Phase | Contenu | Priorité | Dépendance Backend |
|-------|---------|----------|-------------------|
| 1 | Utilitaires communs | 🔴 Haute | Aucune |
| 2 | Composants génériques (Timeline, Card) | 🔴 Haute | Aucune |
| 3 | **Grimaud** — Dashboard, actions, historique | 🔴 Haute | Master Phase 1 |
| 4 | **Chat** — Panel, messages, mémoire | 🟢 Optionnel | Master Phase 5 |
| 5 | **Bazin** — Briefings, alertes | 🟢 Optionnel | Master Phase 5 |
| 6 | **OmniFocus** — Tâches, météo projets | 🟢 Optionnel | Master Phase 5 |
| 7 | Refactoring QueueItemFocusView | 🟡 Moyenne | Aucune |
| 8 | Refactoring FolderSelector | 🟡 Moyenne | Aucune |
| 9 | Consolidation Timelines & Cards | 🟢 Basse | Aucune |
| 10 | Tests & Documentation | 🔴 Haute | Aucune |

---

## Phase 1 : Utilitaires Communs

**Créer les fichiers utilitaires partagés avant les composants.**

### 1.1 `web/src/lib/utils/iconMappings.ts`

```typescript
// Centralise les mappings d'icônes et couleurs
export const NOTE_TYPE_ICONS: Record<string, string> = {
  personne: '👤',
  organisation: '🏢',
  projet: '📁',
  concept: '💡',
  lieu: '📍',
  evenement: '📅',
  produit: '📦',
  default: '📝'
};

export const MODEL_COLORS: Record<string, { bg: string; text: string }> = {
  haiku: { bg: 'bg-green-500/20', text: 'text-green-500' },
  sonnet: { bg: 'bg-blue-500/20', text: 'text-blue-500' },
  opus: { bg: 'bg-purple-500/20', text: 'text-purple-500' }
};

export const MODEL_LABELS: Record<string, string> = {
  haiku: 'Haiku',
  sonnet: 'Sonnet',
  opus: 'Opus'
};

export const ENTITY_CLASSES: Record<string, string> = {
  person: 'bg-blue-500/10 text-blue-500',
  organization: 'bg-purple-500/10 text-purple-500',
  project: 'bg-green-500/10 text-green-500',
  location: 'bg-orange-500/10 text-orange-500',
  event: 'bg-pink-500/10 text-pink-500',
  default: 'bg-[var(--glass-subtle)] text-[var(--color-text-secondary)]'
};

export const HEALTH_COLORS: Record<string, string> = {
  excellent: 'text-green-500',
  good: 'text-blue-500',
  warning: 'text-yellow-500',
  critical: 'text-red-500'
};

export function getNoteTypeIcon(type: string): string;
export function getModelColor(model: string): { bg: string; text: string };
export function getEntityClass(type: string): string;
export function getQualityColor(score: number | null): 'success' | 'warning' | 'danger' | 'primary';
export function getHealthColor(score: number): string;
```

### 1.2 `web/src/lib/utils/formatters.ts`

```typescript
// Fonctions de formatage réutilisables
export function formatDate(dateStr: string, format?: 'short' | 'time' | 'full'): string;
export function formatDuration(ms: number | null): string;
export function formatDelta(before: number | null, after: number | null): string;
export function formatRelativeTime(date: Date | string): string;
export function formatConfidence(score: number): string; // "96%"
export function formatCognitiveLoad(hours: number): string; // "3h de réunions"
```

### 1.3 Tests unitaires: `web/src/lib/utils/__tests__/`

```
web/src/lib/utils/__tests__/
├── iconMappings.test.ts    (~60 lignes)
└── formatters.test.ts      (~100 lignes)
```

---

## Phase 2 : Composants Génériques

### 2.1 GenericTimeline (`web/src/lib/components/ui/GenericTimeline.svelte`)

**Props:**
```typescript
interface Props<T> {
  items: T[];
  emptyText?: string;
  emptyIcon?: string;
  showConnector?: boolean;
  node: Snippet<[item: T, index: number]>;
  content: Snippet<[item: T, index: number]>;
}
```

**Remplace la structure commune de:**
- `GrimaudTimeline.svelte` (ex-RetoucheTimeline)
- `PassTimeline.svelte`
- `ActivityTimeline.svelte`
- `ChatHistory.svelte` (nouvelle)

### 2.2 TimelineEntry (`web/src/lib/components/ui/TimelineEntry.svelte`)

**Props:**
```typescript
interface Props {
  title?: string;
  timestamp?: string;
  duration?: number;
  badges?: Array<{ label: string; variant?: 'default' | 'success' | 'warning' | 'error'; icon?: string }>;
  expandable?: boolean;
  children: Snippet;
  details?: Snippet;
}
```

### 2.3 BaseCard (`web/src/lib/components/ui/BaseCard.svelte`)

**Props:**
```typescript
interface Props {
  title: string;
  icon?: string;
  subtitle?: string;
  quality?: number | null;
  badges?: Array<{ label: string; variant?: string; icon?: string }>;
  interactive?: boolean;
  selected?: boolean;
  showQuality?: boolean;
  onclick?: () => void;
  children?: Snippet;
  actions?: Snippet;
}
```

### 2.4 SidePanel (`web/src/lib/components/ui/SidePanel.svelte`)

**Nouveau** — Pour le chat et autres panels latéraux.

**Props:**
```typescript
interface Props {
  open: boolean;
  title?: string;
  width?: 'sm' | 'md' | 'lg'; // 320px, 400px, 500px
  position?: 'left' | 'right';
  expandable?: boolean; // Bouton plein écran
  onClose: () => void;
  header?: Snippet;
  children: Snippet;
  footer?: Snippet;
}
```

### 2.5 Tests: `web/src/lib/components/ui/__tests__/`

```
web/src/lib/components/ui/__tests__/
├── GenericTimeline.test.ts   (~60 lignes)
├── TimelineEntry.test.ts     (~40 lignes)
├── BaseCard.test.ts          (~50 lignes)
└── SidePanel.test.ts         (~40 lignes)
```

---

## Phase 3 : Grimaud (Gardien PKM)

> **Anciennement Phase 4** — Réordonné pour aligner avec Master Roadmap Phase 1.

Voir section "Grimaud (Gardien PKM)" ci-dessous.

---

## Phase 4 : Chat (Frontin) — Optionnel

> **Anciennement Phase 3** — Déplacé car dépend de Master Roadmap Phase 5 (nice-to-have).

### Architecture

```
web/src/lib/components/chat/
├── ChatPanel.svelte           (~120 lignes) - Orchestrateur panel/fullscreen
├── ChatHeader.svelte          (~40 lignes)  - Titre, modèle, boutons
├── ChatMessages.svelte        (~80 lignes)  - Liste des messages
├── ChatMessage.svelte         (~60 lignes)  - Message individuel (user/assistant)
├── ChatInput.svelte           (~70 lignes)  - Input + bouton envoi
├── ChatActions.svelte         (~50 lignes)  - Boutons d'action dans les réponses
├── ChatHistory.svelte         (~60 lignes)  - Liste conversations passées
├── ChatMemoryManager.svelte   (~80 lignes)  - Gestion mémoires sélectives
├── ModelSelector.svelte       (~40 lignes)  - Dropdown Haiku/Sonnet/Opus
└── index.ts
```

### Composants détaillés

#### ChatPanel.svelte
```typescript
interface Props {
  open: boolean;
  fullscreen?: boolean;
  onClose: () => void;
}
// État: messages, isLoading, selectedModel, currentConversationId
// Utilise: SidePanel ou mode fullscreen
```

#### ChatMessage.svelte
```typescript
interface Props {
  message: {
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    model?: string;
    actions?: ActionButton[];
  };
  onAction?: (action: ActionButton) => void;
}
// Actions: "Créer tâche OF", "Ajouter à la note", etc.
```

#### ChatActions.svelte
```typescript
interface Props {
  actions: Array<{
    type: 'create_note' | 'create_task' | 'draft_email' | 'modify_note';
    label: string;
    data: Record<string, unknown>;
    requiresConfirmation: boolean;
  }>;
  onExecute: (action) => void;
}
```

#### ChatMemoryManager.svelte
```typescript
interface Props {
  memories: ChatMemory[];
  onDelete: (id: string) => void;
  onEdit: (id: string, content: string) => void;
}
// Affiche: préférences, décisions, faits, instructions
// Filtres par type
```

### Route

- **Panel**: Accessible depuis toutes les pages via `Cmd+K` ou bouton fixe
- **Fullscreen**: `/chat` ou bouton expand dans le panel
- **Historique**: `/chat/history`
- **Mémoires**: `/settings/chat-memory`

---

### Grimaud — Détails (Phase 3)

### Architecture

```
web/src/lib/components/grimaud/
├── GrimaudDashboard.svelte     (~150 lignes) - Vue principale santé PKM
├── GrimaudStats.svelte         (~60 lignes)  - Métriques globales
├── GrimaudActionCard.svelte    (~80 lignes)  - Action proposée/exécutée
├── GrimaudActionList.svelte    (~50 lignes)  - Liste filtrée d'actions
├── GrimaudHistory.svelte       (~70 lignes)  - Historique par note
├── GrimaudHealthBadge.svelte   (~30 lignes)  - Badge santé sur les notes
├── GrimaudDiff.svelte          (~60 lignes)  - Diff avant/après
├── GrimaudTrashbin.svelte      (~50 lignes)  - Corbeille notes fusionnées
├── GrimaudFilters.svelte       (~40 lignes)  - Filtres: type, statut, date
└── index.ts
```

### Composants détaillés

#### GrimaudDashboard.svelte
```typescript
interface Props {
  // Données chargées via API
}
// Sections:
// - Stats globales (notes total, santé %, à valider, fusions/enrichissements ce mois)
// - Filtres
// - Liste d'actions (récentes, à valider)
// - Liens: Corbeille, Historique complet
```

#### GrimaudActionCard.svelte
```typescript
interface Props {
  action: {
    id: string;
    type: 'fusion' | 'liaison' | 'restructuration' | 'enrichissement_texte' | 'enrichissement_web' | 'metadonnees' | 'archivage';
    noteTitle: string;
    noteId: string;
    confidence: number;
    status: 'pending' | 'applied' | 'rejected';
    detail: string;
    timestamp: string;
    canUndo: boolean;
  };
  onApply?: () => void;
  onReject?: () => void;
  onUndo?: () => void;
  onViewDiff?: () => void;
}
// Icônes par type: 🔀 fusion, 🔗 liaison, 📐 restructuration, 📝 enrichissement, 🌐 web, 🏷️ meta, 📦 archivage
```

#### GrimaudHealthBadge.svelte
```typescript
interface Props {
  score: number; // 0-100
  lastScan?: string;
  issues?: number;
  size?: 'sm' | 'md';
}
// Couleurs: vert (>80), bleu (60-80), jaune (40-60), rouge (<40)
// Affichage: score + icône ou juste icône (sm)
```

#### GrimaudHistory.svelte
```typescript
interface Props {
  noteId: string;
  actions: GrimaudAction[];
  onRestore: (snapshotId: string) => void;
}
// Timeline des actions Grimaud sur une note spécifique
// Boutons: Voir avant, Restaurer
```

### Route

- **Dashboard**: `/memoires/grimaud`
- **Corbeille**: `/memoires/grimaud/trash`
- **Badge santé**: Affiché sur chaque note dans `/notes/[id]`

### Migration Retouche → Grimaud

| Ancien | Nouveau |
|--------|---------|
| `RetoucheTimeline.svelte` | `GrimaudHistory.svelte` |
| `PendingActionCard.svelte` | `GrimaudActionCard.svelte` |
| `MergeModal.svelte` | Réutilisé (fusion) |
| `RetoucheDiff.svelte` | `GrimaudDiff.svelte` |
| `/memoires/retouche` | `/memoires/grimaud` |

---

## Phase 5 : Bazin (Proactivité)

### Architecture

```
web/src/lib/components/bazin/
├── MorningBriefing.svelte       (~200 lignes) - Briefing matinal complet
├── ContextualBriefing.svelte    (~180 lignes) - Briefing pré-réunion
├── BriefingSection.svelte       (~50 lignes)  - Section générique du briefing
├── AgendaPreview.svelte         (~60 lignes)  - Aperçu agenda du jour
├── CognitiveLoadMeter.svelte    (~40 lignes)  - Jauge charge cognitive
├── FreeSlots.svelte             (~50 lignes)  - Créneaux libres
├── PriorityEmails.svelte        (~70 lignes)  - Emails prioritaires
├── EngagementsList.svelte       (~60 lignes)  - Engagements J/J+1
├── ProjectWeather.svelte        (~80 lignes)  - Météo projets
├── NoteOfTheDay.svelte          (~40 lignes)  - Note à revoir
├── ParticipantCard.svelte       (~70 lignes)  - Fiche participant réunion
├── PreparationScore.svelte      (~50 lignes)  - Score de préparation
├── AlertsPanel.svelte           (~60 lignes)  - Alertes et notifications
├── SuggestionsPanel.svelte      (~70 lignes)  - Suggestions proactives
└── index.ts
```

### Composants détaillés

#### MorningBriefing.svelte
```typescript
interface Props {
  date?: string; // Par défaut: aujourd'hui
}
// Sections:
// 1. Charge cognitive (heures de réunion)
// 2. Agenda (RDV du jour avec participants)
// 3. Emails prioritaires (haute importance ou personnes clés)
// 4. Engagements (promesses à tenir)
// 5. Créneaux libres
// 6. Note du jour (révision suggérée)
// 7. Météo projets
```

#### ContextualBriefing.svelte
```typescript
interface Props {
  meetingId: string;
  // ou
  meeting: {
    title: string;
    startTime: string;
    participants: Participant[];
    context?: string;
  };
}
// Sections:
// 1. Score de préparation
// 2. Participants (fiches PKM enrichies)
// 3. Historique réunions avec ces personnes
// 4. Points de vigilance
// 5. Questions suggérées
// 6. Actualité fraîche (si pertinent)
// 7. Quick win suggéré
```

#### PreparationScore.svelte
```typescript
interface Props {
  score: number; // 0-100
  factors: Array<{
    name: string;
    status: 'ok' | 'warning' | 'missing';
    detail?: string;
  }>;
}
// Facteurs: participants connus, objectif clair, documents prêts, contexte récent
```

#### ProjectWeather.svelte
```typescript
interface Props {
  projects: Array<{
    id: string;
    name: string;
    health: 'sunny' | 'cloudy' | 'rainy' | 'stormy';
    tasksRemaining?: number;
    nextAction?: string;
    lastActivity?: string;
    context?: string; // Depuis Scapin
  }>;
  showOmniFocus?: boolean;
}
// Icônes météo: ☀️ 🌤️ 🌧️ ⛈️
// Combine données Scapin + OmniFocus si activé
```

#### AlertsPanel.svelte
```typescript
interface Props {
  alerts: Array<{
    type: 'engagement' | 'contact' | 'anniversary' | 'deadline';
    priority: 'high' | 'medium' | 'low';
    title: string;
    detail: string;
    actionUrl?: string;
  }>;
}
// Filtrable, triable par priorité
```

### Routes

- **Briefing matinal**: `/` (page d'accueil) ou `/briefing`
- **Briefing contextuel**: Modal avant réunion ou `/briefing/meeting/[id]`
- **Alertes**: Section dans briefing + `/alerts`

---

## Phase 6 : OmniFocus Integration

### Architecture

```
web/src/lib/components/omnifocus/
├── OmniFocusTasks.svelte        (~100 lignes) - Liste tâches du jour
├── OmniFocusTaskCard.svelte     (~50 lignes)  - Tâche individuelle
├── TaskCreatorModal.svelte      (~120 lignes) - Création tâche OF
├── TaskCreatorForm.svelte       (~80 lignes)  - Formulaire création
├── ProjectMappingList.svelte    (~60 lignes)  - Mapping notes ↔ projets
├── ProjectMappingRow.svelte     (~40 lignes)  - Ligne de mapping
├── OmniFocusStatus.svelte       (~30 lignes)  - Statut sync
└── index.ts
```

### Composants détaillés

#### OmniFocusTasks.svelte
```typescript
interface Props {
  filter?: 'today' | 'flagged' | 'available';
  limit?: number;
  showProject?: boolean;
}
// Affiche les tâches OF avec liens vers Scapin si liées
```

#### TaskCreatorModal.svelte
```typescript
interface Props {
  open: boolean;
  prefill?: {
    title?: string;
    project?: string;
    tags?: string[];
    dueDate?: string;
    note?: string;
    sourceEmailId?: string;
    sourceNoteId?: string;
  };
  onClose: () => void;
  onCreate: (task: NewTask) => void;
}
// Modal avec formulaire pré-rempli depuis email ou note
```

#### TaskCreatorForm.svelte
```typescript
interface Props {
  initialValues?: Partial<TaskFormValues>;
  projects: OFProject[];
  tags: OFTag[];
  onSubmit: (values: TaskFormValues) => void;
}
// Champs: titre, projet (dropdown), tags (multi-select), due date, notes
```

#### ProjectMappingList.svelte
```typescript
interface Props {
  mappings: Array<{
    scapinNoteId: string;
    scapinNoteTitle: string;
    omnifocusProjectId?: string;
    omnifocusProjectName?: string;
    autoMatched: boolean;
  }>;
  onUpdateMapping: (noteId: string, projectId: string) => void;
}
// Table de mapping avec auto-match et override manuel
```

### Routes

- **Tâches du jour**: Section dans briefing Bazin
- **Création tâche**: Modal accessible depuis emails et notes
- **Mapping**: `/settings/omnifocus`

### Boutons d'action

Ajouter `[Créer tâche OF]` sur:
- `EmailDetailView` (emails analysés)
- `NoteDetailView` (notes)
- `ChatActions` (dans les réponses du chat)

---

## Phase 7 : Refactoring QueueItemFocusView

**Fichier actuel:** `web/src/lib/components/peripeties/QueueItemFocusView.svelte` (620 lignes)

### Architecture cible

```
web/src/lib/components/peripeties/queue-item/
├── QueueItemFocusView.svelte       (~100 lignes) - Orchestrateur
├── QueueItemHeader.svelte          (~140 lignes) - Avatar, badges, sparkline, actions
├── ReasoningBox.svelte             (~25 lignes)  - Citation raisonnement IA
├── RetrievedContextSection.svelte  (~90 lignes)  - Contexte récupéré (collapsible)
├── AnalysisDetailsSection.svelte   (~110 lignes) - Entités, transparency, metadata
├── ProposedSideEffects.svelte      (~70 lignes)  - Notes & tâches proposées
├── ActionOptionsSection.svelte     (~50 lignes)  - Boutons décisions
├── EmailContentViewer.svelte       (~70 lignes)  - HTML/Text toggle
├── AttachmentsSection.svelte       (~35 lignes)  - Pièces jointes
└── index.ts
```

### Intégration nouvelles features

- Ajouter bouton `[Créer tâche OF]` dans `ActionOptionsSection`
- Ajouter bouton `[Demander à Scapin]` pour ouvrir le chat avec contexte de l'email

---

## Phase 8 : Refactoring FolderSelector

**Fichier actuel:** `web/src/lib/components/ui/FolderSelector.svelte` (675 lignes)

### Architecture cible

```
web/src/lib/components/ui/folder-selector/
├── FolderSelector.svelte        (~120 lignes) - Orchestrateur
├── SuggestionsSection.svelte    (~70 lignes)  - Suggestions IA avec confiance
├── RecentFoldersSection.svelte  (~35 lignes)  - Chips récents
├── FolderSearchInput.svelte     (~25 lignes)  - Input recherche
├── FolderTree.svelte            (~90 lignes)  - Conteneur arbre filtré
├── FolderNode.svelte            (~55 lignes)  - Nœud récursif
├── CreateFolderForm.svelte      (~70 lignes)  - Formulaire création
└── index.ts
```

---

## Phase 9 : Consolidation Timelines & Cards

### 9.1 Migration Timelines

| Avant | Après |
|-------|-------|
| `RetoucheTimeline.svelte` | → `GrimaudHistory.svelte` (Phase 3) |
| `PassTimeline.svelte` | Utilise `GenericTimeline` |
| `ActivityTimeline.svelte` | Utilise `GenericTimeline` |

### 9.2 Migration Cards

| Avant | Après |
|-------|-------|
| `LectureReviewCard.svelte` | Utilise `BaseCard` |
| `FilageLectureCard.svelte` | Utilise `BaseCard` |
| `PendingActionCard.svelte` | → `GrimaudActionCard.svelte` (Phase 3) |

---

## Phase 10 : Tests & Documentation

### 10.1 Tests Unitaires Vitest

```
web/src/lib/
├── utils/__tests__/
│   ├── iconMappings.test.ts
│   └── formatters.test.ts
├── components/ui/__tests__/
│   ├── GenericTimeline.test.ts
│   ├── TimelineEntry.test.ts
│   ├── BaseCard.test.ts
│   └── SidePanel.test.ts
├── components/chat/__tests__/
│   ├── ChatPanel.test.ts
│   ├── ChatMessage.test.ts
│   └── ChatActions.test.ts
├── components/grimaud/__tests__/
│   ├── GrimaudActionCard.test.ts
│   └── GrimaudHealthBadge.test.ts
└── components/bazin/__tests__/
    ├── PreparationScore.test.ts
    └── CognitiveLoadMeter.test.ts
```

### 10.2 Tests E2E Playwright

```
web/e2e/
├── chat.spec.ts              - Parcours chat complet
├── grimaud.spec.ts           - Dashboard, actions, historique
├── bazin-briefing.spec.ts    - Briefing matinal et contextuel
├── omnifocus.spec.ts         - Création tâche, mapping
├── peripeties.spec.ts        - QueueItemFocusView refactorisé
└── folder-selector.spec.ts   - FolderSelector refactorisé
```

### 10.3 Documentation

- [ ] `web/src/lib/components/ui/README.md` — Composants génériques
- [ ] `web/src/lib/components/chat/README.md` — Composants chat
- [ ] `web/src/lib/components/grimaud/README.md` — Composants Grimaud
- [ ] `web/src/lib/components/bazin/README.md` — Composants Bazin
- [ ] `docs/dev/ui-component-migration.md` — Guide migration
- [ ] `ARCHITECTURE.md` — Section Frontend mise à jour

---

## Ordre d'Implémentation Recommandé

### Sprint 1 : Fondations (Phase 1-2)

| # | Tâche | Fichiers |
|---|-------|----------|
| 1.1 | Créer `iconMappings.ts` | 1 fichier + tests |
| 1.2 | Créer `formatters.ts` | 1 fichier + tests |
| 2.1 | Créer `GenericTimeline` | 1 fichier + tests |
| 2.2 | Créer `TimelineEntry` | 1 fichier + tests |
| 2.3 | Créer `BaseCard` | 1 fichier + tests |
| 2.4 | Créer `SidePanel` | 1 fichier + tests |

### Sprint 2 : Grimaud (Phase 3)

> **Priorité haute** — Aligne avec Master Roadmap Phase 1.

| # | Tâche | Fichiers |
|---|-------|----------|
| 3.1 | Créer structure `grimaud/` | 10 fichiers |
| 3.2 | Implémenter `GrimaudDashboard` | Vue principale |
| 3.3 | Implémenter `GrimaudActionCard` | Actions |
| 3.4 | Implémenter `GrimaudHistory` | Timeline par note |
| 3.5 | Implémenter `GrimaudHealthBadge` | Badge sur notes |
| 3.6 | Route `/memoires/grimaud` | Remplace retouche |
| 3.7 | Tests E2E grimaud | `grimaud.spec.ts` |

### Sprint 3 : Chat (Phase 3) — Optionnel

> **Nice-to-have** — Dépend de Master Roadmap Phase 5.

| # | Tâche | Fichiers |
|---|-------|----------|
| 4.1 | Créer structure `chat/` | 10 fichiers |
| 4.2 | Implémenter `ChatPanel` | Avec SidePanel |
| 4.3 | Implémenter `ChatMessage` + `ChatActions` | Actions exécutables |
| 4.4 | Implémenter `ChatHistory` | Avec GenericTimeline |
| 4.5 | Implémenter `ChatMemoryManager` | Settings |
| 4.6 | Route `/chat` + raccourci `Cmd+K` | Integration |
| 4.7 | Tests E2E chat | `chat.spec.ts` |

### Sprint 4 : Bazin (Phase 5) — Optionnel

> **Nice-to-have** — Dépend de Master Roadmap Phase 5.

| # | Tâche | Fichiers |
|---|-------|----------|
| 5.1 | Créer structure `bazin/` | 14 fichiers |
| 5.2 | Implémenter `MorningBriefing` | Briefing matinal |
| 5.3 | Implémenter `ContextualBriefing` | Pré-réunion |
| 5.4 | Implémenter composants support | Agenda, Load, etc. |
| 5.5 | Route `/briefing` | Page d'accueil |
| 5.6 | Tests E2E briefing | `bazin-briefing.spec.ts` |

### Sprint 5 : OmniFocus (Phase 6) — Optionnel

> **Nice-to-have** — Dépend de Master Roadmap Phase 5.

| # | Tâche | Fichiers |
|---|-------|----------|
| 6.1 | Créer structure `omnifocus/` | 7 fichiers |
| 6.2 | Implémenter `TaskCreatorModal` | Création tâche |
| 6.3 | Implémenter `OmniFocusTasks` | Liste tâches |
| 6.4 | Intégrer dans Bazin | ProjectWeather |
| 6.5 | Route `/settings/omnifocus` | Mapping |
| 6.6 | Tests E2E | `omnifocus.spec.ts` |

### Sprint 6 : Refactoring (Phase 7-9)

| # | Tâche | Fichiers |
|---|-------|----------|
| 7.1 | Refactorer `QueueItemFocusView` | 10 fichiers |
| 8.1 | Refactorer `FolderSelector` | 8 fichiers |
| 9.1 | Migrer Timelines vers `GenericTimeline` | 3 fichiers |
| 9.2 | Migrer Cards vers `BaseCard` | 2 fichiers |

---

## Fichiers Créés/Modifiés (Total)

### Nouveaux fichiers (~80 fichiers)

**Utilitaires (4):**
- `web/src/lib/utils/iconMappings.ts`
- `web/src/lib/utils/formatters.ts`
- `web/src/lib/utils/__tests__/iconMappings.test.ts`
- `web/src/lib/utils/__tests__/formatters.test.ts`

**Composants génériques (8):**
- `web/src/lib/components/ui/GenericTimeline.svelte`
- `web/src/lib/components/ui/TimelineEntry.svelte`
- `web/src/lib/components/ui/BaseCard.svelte`
- `web/src/lib/components/ui/SidePanel.svelte`
- + 4 fichiers tests

**Chat (11):**
- 9 composants + index.ts
- 3 fichiers tests

**Grimaud (11):**
- 9 composants + index.ts
- 2 fichiers tests

**Bazin (15):**
- 14 composants + index.ts

**OmniFocus (8):**
- 7 composants + index.ts

**QueueItem refactorisé (10):**
- 9 composants + index.ts

**FolderSelector refactorisé (8):**
- 7 composants + index.ts

**Tests E2E (5):**
- `chat.spec.ts`
- `grimaud.spec.ts`
- `bazin-briefing.spec.ts`
- `omnifocus.spec.ts`
- `folder-selector.spec.ts`

### Fichiers à supprimer

- `web/src/lib/components/ui/FolderSelector.svelte` (après migration)
- `web/src/lib/components/peripeties/QueueItemFocusView.svelte` (après migration)
- `web/src/lib/components/memory/RetoucheTimeline.svelte` (remplacé par Grimaud)
- `web/src/lib/components/retouche/PendingActionCard.svelte` (remplacé par Grimaud)

### Fichiers à modifier

- `web/src/lib/components/ui/index.ts`
- `web/src/lib/components/peripeties/index.ts`
- `web/src/lib/components/memory/index.ts`
- Routes diverses pour intégrer les nouvelles features

---

## Routes Finales

> **Note** : La homepage (`/`) reste sur le flux actuel jusqu'à l'implémentation de Bazin (Phase 5 Master Roadmap).

| Route | Composant Principal | Description |
|-------|---------------------|-------------|
| `/` | `QueueView` → `MorningBriefing` (après Bazin) | Page d'accueil (flux puis briefing) |
| `/briefing` | `MorningBriefing` | Briefing matinal (quand disponible) |
| `/briefing/meeting/[id]` | `ContextualBriefing` | Briefing pré-réunion |
| `/chat` | `ChatPanel` (fullscreen) | Chat plein écran |
| `/chat/history` | `ChatHistory` | Historique conversations |
| `/flux` | `QueueItemFocusView` | Péripéties |
| `/memoires/grimaud` | `GrimaudDashboard` | Santé PKM |
| `/memoires/grimaud/trash` | `GrimaudTrashbin` | Corbeille |
| `/memoires/review` | `LectureReviewCard` | Révision SM-2 |
| `/memoires/filage` | `FilageLectureCard` | Filage |
| `/notes/[id]` | `NoteDetail` + `GrimaudHealthBadge` | Détail note |
| `/settings/omnifocus` | `ProjectMappingList` | Mapping OF |
| `/settings/chat-memory` | `ChatMemoryManager` | Mémoires chat |
| `/alerts` | `AlertsPanel` | Alertes |

---

## Métriques de Succès

| Métrique | Avant | Après (cible) |
|----------|-------|---------------|
| Lignes QueueItemFocusView | 620 | ~100 |
| Lignes FolderSelector | 675 | ~120 |
| Composants réutilisables | 0 | 4+ |
| Fichiers > 300 lignes | 4 | 0 |
| Nouvelles features UI | 0 | 4 (Chat, Grimaud, Bazin, OF) |
| Tests unitaires | 1 fichier | 15+ fichiers |
| Tests E2E nouvelles features | 0 | 5 fichiers |
| Documentation composants | Partielle | Complète |

---

## Vérification Finale

### Commandes

```bash
# Tests unitaires
cd web && npm run test

# Tests unitaires avec couverture
cd web && npm run test -- --coverage

# Vérification types
cd web && npm run check

# Tests E2E
cd web && npx playwright test

# Lint
cd web && npm run lint
```

### Checklist manuelle

- [ ] Chat: Panel s'ouvre avec Cmd+K
- [ ] Chat: Historique consultable
- [ ] Chat: Actions exécutables
- [ ] Grimaud: Dashboard affiche santé
- [ ] Grimaud: Actions appliquer/rejeter/annuler
- [ ] Grimaud: Badge santé sur notes
- [ ] Bazin: Briefing matinal complet
- [ ] Bazin: Briefing contextuel 2h avant RDV
- [ ] OmniFocus: Création tâche depuis email
- [ ] OmniFocus: Tâches du jour dans briefing
- [ ] Mobile responsive: Tous composants sur 375px

---

*Plan créé le 24 janvier 2026, mis à jour le 27 janvier 2026 (alignement Master Roadmap)*
