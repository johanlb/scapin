# 02 - Architecture Technique

[< Retour à l'index](./00-index.md) | [< Vision](./01-vision.md)

---

## Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SCAPIN WEB INTERFACE                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         FRONTEND (SvelteKit)                             ││
│  │  Port: 5173 (dev) / 3000 (prod)                                         ││
│  │                                                                          ││
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           ││
│  │  │Briefing │ │  Flux   │ │  Notes  │ │ Journal │ │  Stats  │           ││
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           ││
│  │       │           │           │           │           │                  ││
│  │       └───────────┴───────────┴───────────┴───────────┘                  ││
│  │                              ↓                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                      STORES (État Global)                           │││
│  │  │  auth │ events │ chat │ notes │ theme │ notifications              │││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  │                              ↓                                           ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐││
│  │  │                    API CLIENT (TypeScript)                          │││
│  │  │  - Fetch wrapper avec intercepteur JWT                              │││
│  │  │  - WebSocket manager pour temps réel                                │││
│  │  │  - Types générés depuis OpenAPI                                     │││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                    ↓ HTTP / WebSocket                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         BACKEND (FastAPI)                                ││
│  │  Port: 8000                                                              ││
│  │  REST: /api/*  │  Auth: /api/auth/*  │  WebSocket: /ws/*                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture des Couches

### 1. Routes (Pages)

Les routes SvelteKit définissent les pages de l'application. Chaque route :
- Charge ses données via `+page.server.ts` (SSR) ou `+page.ts` (client)
- Utilise les stores pour l'état partagé
- Compose des composants réutilisables

### 2. Stores (État Global)

Les stores Svelte gèrent l'état partagé entre composants. Pattern utilisé : **stores dérivés** pour les données calculées.

### 3. API Client

Couche d'abstraction pour communiquer avec le backend :
- Gestion automatique des tokens JWT (refresh transparent)
- Gestion des erreurs centralisée
- Cache avec invalidation

### 4. Composants

Composants réutilisables organisés par domaine :
- `ui/` — Composants génériques (Button, Card, Modal...)
- `events/` — Composants spécifiques au flux d'événements
- `notes/` — Composants pour les notes PKM
- etc.

---

## Gestion de l'État (Stores)

### Schéma d'Interaction

```
┌─────────────────────────────────────────────────────────────────────┐
│                           STORES                                     │
│                                                                      │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                  │
│  │   auth   │─────→│  events  │      │   chat   │                  │
│  │          │      │          │      │          │                  │
│  │ • user   │      │ • pending│      │ • messages│                 │
│  │ • token  │      │ • processed     │ • sessions│                 │
│  │ • isAuth │      │ • filters│      │ • current │                 │
│  └──────────┘      └──────────┘      └──────────┘                  │
│       │                 │                  │                        │
│       │                 ↓                  │                        │
│       │           ┌──────────┐             │                        │
│       │           │ derived: │             │                        │
│       │           │pendingCount           │                        │
│       │           │urgentEvents│           │                        │
│       │           └──────────┘             │                        │
│       │                                    │                        │
│       ↓                                    ↓                        │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐                  │
│  │  theme   │      │  notes   │      │notifications               │
│  │          │      │          │      │          │                  │
│  │ • mode   │      │ • list   │      │ • toasts │                  │
│  │ • auto   │      │ • current│      │ • unread │                  │
│  └──────────┘      └──────────┘      └──────────┘                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Définition des Stores

```typescript
// stores/auth.ts
interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login(credentials: Credentials): Promise<void>;
  logout(): void;
  refresh(): Promise<void>;
}

// stores/events.ts
interface EventsStore {
  pending: Event[];           // À traiter
  processed: Event[];         // Traités par Scapin
  rejected: Event[];          // Rejets
  filters: EventFilters;      // Filtres actifs
  loading: boolean;

  // Actions
  fetch(view: 'pending' | 'processed' | 'rejected'): Promise<void>;
  approve(id: string): Promise<void>;
  reject(id: string, reason?: string): Promise<void>;
  modify(id: string, changes: Partial<Event>): Promise<void>;
  undo(id: string): Promise<void>;
}

// stores/chat.ts
interface ChatStore {
  sessions: ChatSession[];    // Liste des discussions
  current: ChatSession | null;// Discussion active
  messages: Message[];        // Messages de la session courante
  isConnected: boolean;       // WebSocket connecté

  // Actions
  send(content: string): Promise<void>;
  switchSession(id: string): void;
  createSession(context?: EventContext): Promise<void>;
}

// stores/notifications.ts
interface NotificationsStore {
  toasts: Toast[];            // Notifications temporaires
  unread: Notification[];     // Notifications persistantes non lues

  // Actions
  show(message: string, type: 'success' | 'error' | 'info'): void;
  dismiss(id: string): void;
  markRead(id: string): void;
}
```

### Stores Dérivés

```typescript
// Stores dérivés (calculés automatiquement)
import { derived } from 'svelte/store';

// Nombre d'événements en attente (pour badge sidebar)
export const pendingCount = derived(events, $events => $events.pending.length);

// Événements urgents uniquement
export const urgentEvents = derived(events, $events =>
  $events.pending.filter(e => e.urgency === 'high')
);

// Thème effectif (auto = suit le système)
export const effectiveTheme = derived(theme, $theme =>
  $theme.mode === 'auto'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : $theme.mode
);
```

---

## Communication Temps Réel (WebSocket)

### Connexions WebSocket

```typescript
// lib/api/websocket.ts

class WebSocketManager {
  private connections: Map<string, WebSocket> = new Map();

  // Connexion principale pour notifications et status
  connectMain(): void {
    this.connect('main', '/ws/main');
  }

  // Connexion pour une discussion spécifique
  connectChat(sessionId: string): void {
    this.connect(`chat-${sessionId}`, `/ws/chat/${sessionId}`);
  }

  private connect(key: string, path: string): void {
    const ws = new WebSocket(`${WS_BASE_URL}${path}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(key, data);
    };

    ws.onclose = () => {
      // Reconnexion automatique avec backoff
      setTimeout(() => this.connect(key, path), 1000);
    };

    this.connections.set(key, ws);
  }

  private handleMessage(key: string, data: WSMessage): void {
    switch (data.type) {
      case 'new_event':
        events.addPending(data.event);
        notifications.show('Nouvel événement', 'info');
        break;
      case 'chat_message':
        chat.addMessage(data.message);
        break;
      case 'status_update':
        scapinStatus.set(data.status);
        break;
    }
  }
}
```

### Types de Messages WebSocket

| Type | Direction | Description |
|------|-----------|-------------|
| `new_event` | Server → Client | Nouvel événement à traiter |
| `event_processed` | Server → Client | Événement traité par Scapin |
| `chat_message` | Bidirectionnel | Message dans une discussion |
| `status_update` | Server → Client | Changement status Scapin |
| `typing` | Client → Server | Indicateur de frappe |

---

## Génération des Types (OpenAPI → TypeScript)

### Workflow

```
Backend (FastAPI)          →    OpenAPI Schema    →    TypeScript Types

src/jeeves/api/            →    /api/openapi.json →    web/src/lib/api/types.ts
  models/responses.py
  routers/*.py
```

### Script de Génération

```bash
# web/scripts/generate-types.sh

#!/bin/bash
# Génère les types TypeScript depuis l'API FastAPI

API_URL="${API_URL:-http://localhost:8000}"

# Récupérer le schéma OpenAPI
curl -s "$API_URL/openapi.json" -o openapi.json

# Générer les types TypeScript
npx openapi-typescript openapi.json -o src/lib/api/types.ts

# Nettoyer
rm openapi.json

echo "✅ Types générés dans src/lib/api/types.ts"
```

### Package.json Script

```json
{
  "scripts": {
    "generate:types": "./scripts/generate-types.sh",
    "dev": "npm run generate:types && vite dev",
    "build": "npm run generate:types && vite build"
  }
}
```

---

## Configuration Environnement

### Variables d'Environnement

```bash
# web/.env.example

# API Backend
PUBLIC_API_URL=http://localhost:8000
PUBLIC_WS_URL=ws://localhost:8000

# Feature flags
PUBLIC_ENABLE_CHAT=true
PUBLIC_ENABLE_KEYBOARD_SHORTCUTS=true

# Development
PUBLIC_DEV_MODE=true
```

### Configuration SvelteKit

```typescript
// web/src/lib/config.ts

export const config = {
  apiUrl: import.meta.env.PUBLIC_API_URL || 'http://localhost:8000',
  wsUrl: import.meta.env.PUBLIC_WS_URL || 'ws://localhost:8000',

  features: {
    chat: import.meta.env.PUBLIC_ENABLE_CHAT === 'true',
    keyboardShortcuts: import.meta.env.PUBLIC_ENABLE_KEYBOARD_SHORTCUTS === 'true',
  },

  isDev: import.meta.env.PUBLIC_DEV_MODE === 'true',
};
```

---

## Structure des Fichiers Frontend

```
web/
├── package.json
├── svelte.config.js
├── tailwind.config.js
├── vite.config.ts
├── tsconfig.json
├── .env.example
│
├── scripts/
│   └── generate-types.sh      # Génération types depuis OpenAPI
│
├── src/
│   ├── app.html               # Template HTML de base
│   ├── app.css                # Styles globaux + Tailwind
│   │
│   ├── lib/
│   │   ├── config.ts          # Configuration environnement
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts      # Client HTTP avec auth JWT
│   │   │   ├── websocket.ts   # Manager WebSocket
│   │   │   ├── types.ts       # Types générés depuis OpenAPI
│   │   │   ├── events.ts      # API flux d'événements
│   │   │   ├── briefing.ts    # API briefing
│   │   │   ├── notes.ts       # API notes PKM (CRUD)
│   │   │   ├── chat.ts        # API discussions
│   │   │   ├── journal.ts     # API journal
│   │   │   ├── reports.ts     # API rapports
│   │   │   ├── stats.ts       # API statistiques
│   │   │   └── auth.ts        # API authentification
│   │   │
│   │   ├── stores/
│   │   │   ├── auth.ts        # Store auth (JWT, user)
│   │   │   ├── theme.ts       # Store thème (dark/light/auto)
│   │   │   ├── events.ts      # Store flux d'événements
│   │   │   ├── chat.ts        # Store conversations Scapin
│   │   │   ├── notes.ts       # Store notes PKM
│   │   │   ├── notifications.ts # Store notifications/toasts
│   │   │   └── scapinStatus.ts  # Store status Scapin (actif/focus/erreur)
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.svelte          # Layout principal 3 colonnes
│   │   │   │   ├── Sidebar.svelte         # Navigation gauche
│   │   │   │   ├── Header.svelte          # Header avec status + recherche
│   │   │   │   ├── ChatPanel.svelte       # Panel chat latéral (droite, réductible)
│   │   │   │   ├── CommandPalette.svelte  # Recherche globale Cmd+K
│   │   │   │   ├── NotificationCenter.svelte
│   │   │   │   └── KeyboardShortcuts.svelte # Modal aide raccourcis (?)
│   │   │   │
│   │   │   ├── ui/
│   │   │   │   ├── Button.svelte
│   │   │   │   ├── Card.svelte
│   │   │   │   ├── Badge.svelte
│   │   │   │   ├── Input.svelte
│   │   │   │   ├── Select.svelte
│   │   │   │   ├── Checkbox.svelte
│   │   │   │   ├── Avatar.svelte
│   │   │   │   ├── Modal.svelte
│   │   │   │   ├── Tabs.svelte
│   │   │   │   ├── Toast.svelte
│   │   │   │   ├── Skeleton.svelte        # Loading placeholder
│   │   │   │   ├── ConfidenceBar.svelte   # Barre de confiance 0-100%
│   │   │   │   ├── SourceBadge.svelte     # Badge source (Email/Teams/etc)
│   │   │   │   ├── UrgencyBadge.svelte    # Badge urgence (high/medium/low)
│   │   │   │   ├── StatusIndicator.svelte # Status Scapin temps réel
│   │   │   │   └── HoverPreview.svelte    # Preview liens [[...]] au survol
│   │   │   │
│   │   │   ├── events/
│   │   │   │   ├── EventCard.svelte       # Card événement générique
│   │   │   │   ├── EventList.svelte       # Liste avec infinite scroll
│   │   │   │   ├── EventDetail.svelte     # Panneau détail (niveau 2)
│   │   │   │   ├── EventActions.svelte    # Boutons Approve/Modify/Reject/Undo
│   │   │   │   ├── EventFilters.svelte    # Filtres source/urgence/date
│   │   │   │   ├── EventBulkActions.svelte # Actions en masse
│   │   │   │   ├── SavedFilters.svelte    # Filtres sauvegardés
│   │   │   │   └── QuickActions.svelte    # Actions rapides (briefing)
│   │   │   │
│   │   │   ├── briefing/
│   │   │   │   ├── BriefingCard.svelte    # Résumé IA du jour
│   │   │   │   ├── UrgentList.svelte      # Événements urgents
│   │   │   │   ├── MeetingsToday.svelte   # Réunions du jour
│   │   │   │   └── ScapinSummary.svelte   # Message personnalisé Scapin
│   │   │   │
│   │   │   ├── notes/
│   │   │   │   ├── NotesList.svelte       # Arborescence + recherche
│   │   │   │   ├── NoteEditor.svelte      # Éditeur Markdown
│   │   │   │   ├── NotePreview.svelte     # Rendu Markdown
│   │   │   │   ├── NoteLinks.svelte       # Liens bidirectionnels
│   │   │   │   ├── NoteTemplates.svelte   # Sélecteur de templates
│   │   │   │   └── NoteLinkPreview.svelte # Preview hover [[liens]]
│   │   │   │
│   │   │   ├── chat/
│   │   │   │   ├── ChatInput.svelte       # Input avec suggestions
│   │   │   │   ├── ChatMessage.svelte     # Bulle message (user/scapin)
│   │   │   │   ├── ChatHistory.svelte     # Liste messages scrollable
│   │   │   │   └── ChatSuggestions.svelte # Suggestions contextuelles
│   │   │   │
│   │   │   ├── journal/
│   │   │   │   ├── JournalEditor.svelte   # Éditeur session journal
│   │   │   │   ├── JournalQuestion.svelte # Question interactive
│   │   │   │   └── JournalProgress.svelte # Barre de progression
│   │   │   │
│   │   │   ├── reports/
│   │   │   │   ├── ReportCard.svelte      # Aperçu rapport
│   │   │   │   ├── ReportDetail.svelte    # Contenu complet
│   │   │   │   └── ReportExport.svelte    # Options export PDF/MD
│   │   │   │
│   │   │   └── stats/
│   │   │       ├── StatsOverview.svelte   # KPIs principaux
│   │   │       ├── StatsChart.svelte      # Graphique réutilisable
│   │   │       ├── TokenUsage.svelte      # Consommation tokens
│   │   │       └── ConfidenceChart.svelte # Évolution confiance
│   │   │
│   │   └── utils/
│   │       ├── format.ts          # Formatage dates, nombres
│   │       ├── colors.ts          # Couleurs par confiance/urgence/source
│   │       ├── markdown.ts        # Rendu Markdown
│   │       └── keyboard.ts        # Gestion raccourcis clavier
│   │
│   └── routes/
│       ├── +layout.svelte         # Layout global (sidebar + chat panel)
│       ├── +layout.server.ts      # Auth check SSR
│       ├── +page.svelte           # Home = Briefing du jour
│       │
│       ├── login/
│       │   └── +page.svelte       # Page login
│       │
│       ├── flux/
│       │   ├── +page.svelte       # Flux unifié (défaut: À traiter)
│       │   ├── +layout.svelte     # Layout avec onglets
│       │   ├── traites/
│       │   │   └── +page.svelte   # Onglet "Traités"
│       │   ├── historique/
│       │   │   └── +page.svelte   # Onglet "Historique"
│       │   ├── rejets/
│       │   │   └── +page.svelte   # Onglet "Rejets"
│       │   └── [id]/
│       │       └── +page.svelte   # Détail événement (niveau 3)
│       │
│       ├── notes/
│       │   ├── +page.svelte       # Liste/arborescence notes
│       │   ├── new/
│       │   │   └── +page.svelte   # Nouvelle note (avec template)
│       │   └── [...path]/
│       │       └── +page.svelte   # Vue/édition note (path dynamique)
│       │
│       ├── discussions/
│       │   ├── +page.svelte       # Liste discussions (multi-sessions)
│       │   └── [id]/
│       │       └── +page.svelte   # Discussion plein écran
│       │
│       ├── journal/
│       │   ├── +page.svelte       # Liste journaux passés
│       │   └── [date]/
│       │       └── +page.svelte   # Session journal du jour
│       │
│       ├── rapports/
│       │   ├── +page.svelte       # Liste rapports (défaut: journaliers)
│       │   ├── +layout.svelte     # Layout avec onglets type
│       │   ├── hebdo/
│       │   │   └── +page.svelte   # Rapports hebdomadaires
│       │   ├── mensuel/
│       │   │   └── +page.svelte   # Rapports mensuels
│       │   └── [id]/
│       │       └── +page.svelte   # Détail rapport + export
│       │
│       ├── stats/
│       │   └── +page.svelte       # Dashboard statistiques
│       │
│       └── settings/
│           └── +page.svelte       # Configuration complète
│
├── static/
│   ├── favicon.ico
│   └── logo.svg
│
└── tests/
    ├── unit/
    │   └── *.test.ts              # Tests Vitest
    └── e2e/
        └── *.spec.ts              # Tests Playwright
```

---

## Dépendances Frontend

```json
{
  "name": "scapin-web",
  "version": "0.8.0",
  "type": "module",
  "scripts": {
    "dev": "npm run generate:types && vite dev",
    "build": "npm run generate:types && vite build",
    "preview": "vite preview",
    "generate:types": "./scripts/generate-types.sh",
    "test": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint . && prettier --check .",
    "format": "prettier --write ."
  },
  "dependencies": {
    "@sveltejs/kit": "^2.0.0",
    "svelte": "^5.0.0"
  },
  "devDependencies": {
    "@sveltejs/adapter-node": "^2.0.0",
    "@tailwindcss/forms": "^0.5.0",
    "@tailwindcss/typography": "^0.5.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "@types/node": "^20.0.0",
    "openapi-typescript": "^6.0.0",
    "vitest": "^1.0.0",
    "@playwright/test": "^1.40.0",
    "prettier": "^3.0.0",
    "prettier-plugin-svelte": "^3.0.0",
    "eslint": "^8.0.0",
    "eslint-plugin-svelte": "^2.0.0"
  }
}
```

---

## Résumé des Routes

| Route | Page | Description |
|-------|------|-------------|
| `/` | Briefing | Page d'accueil, résumé du jour |
| `/login` | Login | Authentification |
| `/flux` | Flux | Événements à traiter (défaut) |
| `/flux/traites` | Flux | Événements traités |
| `/flux/historique` | Flux | Timeline complète |
| `/flux/rejets` | Flux | Rejets (apprentissage) |
| `/flux/[id]` | Détail | Événement complet |
| `/notes` | Notes | Arborescence PKM |
| `/notes/new` | Notes | Nouvelle note |
| `/notes/[...path]` | Notes | Vue/édition note |
| `/discussions` | Discussions | Liste sessions chat |
| `/discussions/[id]` | Discussions | Chat plein écran |
| `/journal` | Journal | Liste sessions passées |
| `/journal/[date]` | Journal | Session interactive |
| `/rapports` | Rapports | Journaliers (défaut) |
| `/rapports/hebdo` | Rapports | Hebdomadaires |
| `/rapports/mensuel` | Rapports | Mensuels |
| `/rapports/[id]` | Rapports | Détail + export |
| `/stats` | Statistiques | Dashboard KPIs |
| `/settings` | Paramètres | Configuration |

---

[< Vision](./01-vision.md) | [Suivant : Design System >](./03-design-system.md)
