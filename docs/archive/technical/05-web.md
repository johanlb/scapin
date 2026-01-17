# Frontend SvelteKit

**Version** : 0.8.0
**Dernière mise à jour** : 11 janvier 2026
**Répertoire** : `web/`

---

## Table des Matières

1. [Configuration & Tooling](#1-configuration--tooling)
2. [Layout & Routing](#2-layout--routing)
3. [Stores Svelte 5](#3-stores-svelte-5)
4. [Composants](#4-composants)
5. [Client API TypeScript](#5-client-api-typescript)
6. [Utilitaires](#6-utilitaires)
7. [PWA & Service Worker](#7-pwa--service-worker)
8. [Tests Playwright](#8-tests-playwright)

---

## 1. Configuration & Tooling

### 1.1 SvelteKit (`svelte.config.js`)

```javascript
import adapter from '@sveltejs/adapter-auto';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  kit: { adapter: adapter() }
};
```

- **Adapter** : `adapter-auto` (détection automatique)
- **Preprocessor** : Vite Svelte plugin
- **SPA Mode** : SSR désactivé

### 1.2 Vite (`vite.config.ts`)

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true }
    }
  }
});
```

### 1.3 Scripts NPM

```json
{
  "dev": "vite dev",                     // Dev server (HMR)
  "dev:full": "cd .. && ./scripts/dev.sh", // Dev avec backend
  "build": "vite build",                 // Build production
  "preview": "vite preview",             // Preview production
  "check": "svelte-kit sync && svelte-check", // Type-check
  "test": "vitest",                      // Unit tests
  "test:e2e": "playwright test"          // E2E tests
}
```

### 1.4 Dépendances Clés

| Package | Version | Usage |
|---------|---------|-------|
| `svelte` | 5.45.6 | Framework UI (runes) |
| `@sveltejs/kit` | 2.49.1 | Méta-framework |
| `tailwindcss` | 4.1.18 | Styling |
| `@tanstack/svelte-virtual` | 3.13.16 | Virtual scrolling |
| `marked` | 17.0.1 | Markdown parsing |
| `@playwright/test` | 1.57.0 | E2E testing |

### 1.5 CSS Variables (`app.css`)

**Thème système** :
```css
/* Colors */
--color-primary: #007aff;
--color-accent: #007aff;
--color-text-primary: #000 / #fff;
--color-bg-primary: #fff / #000;
--color-error: #ff3b30;

/* Glass Design */
--glass-prominent: rgba(255,255,255,0.7);
--glass-subtle: rgba(255,255,255,0.5);

/* Transitions */
--transition-fast: 150ms;
--transition-normal: 300ms;
--spring-responsive: cubic-bezier(0.4, 0, 0.2, 1);
```

---

## 2. Layout & Routing

### 2.1 Root Layout (`src/routes/+layout.svelte`)

**Responsabilités** :

1. **Initialization** (onMount)
   - Auth : `authStore.initialize()`
   - Service Worker : Enregistrement PWA
   - Notifications : `notificationStore.initialize()`
   - Keyboard : Raccourcis globaux (Cmd+K)

2. **Auth Guard** ($effect)
   - Vérifie `authStore.state` à chaque changement
   - Redirige vers `/login` si non authentifié

3. **WebSocket** ($effect)
   - Connexion quand authentifié
   - Écoute événements temps-réel

4. **Layout Responsive**
   - Desktop : Sidebar (w-16/w-56) + ChatPanel (w-72)
   - Mobile : BottomNav + Overlay

### 2.2 SPA Mode (`+layout.ts`)

```typescript
export const ssr = false;       // SPA mode
export const prerender = false; // Pas de prérendering
```

### 2.3 Structure des Pages

```
src/routes/
├── +layout.svelte          # Root (auth, sidebar, chat)
├── +layout.ts              # SSR=false
├── +page.svelte            # Home (Briefing)
├── login/+page.svelte      # Login PIN
├── flux/
│   ├── +page.svelte        # Queue emails
│   ├── [id]/+page.svelte   # Détail email
│   └── focus/+page.svelte  # Focus mode
├── notes/
│   ├── +page.svelte        # 3-colonnes
│   ├── [...path]/+page.svelte # Note détail
│   └── review/+page.svelte # SM-2 révision
├── discussions/+page.svelte # Chat
├── journal/+page.svelte    # Journaling
├── drafts/
│   ├── +page.svelte        # Liste brouillons
│   └── [id]/+page.svelte   # Édition
├── help/+page.svelte       # Guide
├── settings/+page.svelte   # Configuration
├── stats/+page.svelte      # Statistiques
└── valets/+page.svelte     # État valets
```

---

## 3. Stores Svelte 5

### 3.1 Auth Store (`auth.svelte.ts`)

**État** :
```typescript
interface AuthState {
  isAuthenticated: boolean;
  user: string | null;
  authRequired: boolean;
  loading: boolean;
  error: string | null;
  initialized: boolean;
  backendAvailable: boolean;
  retryCount: number;
}
```

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `initialize()` | Charge état depuis token |
| `login(pin)` | Login avec PIN 4-6 chiffres |
| `logout()` | Déconnexion + clear localStorage |
| `retryConnection()` | Réessaye connexion backend |

**Retry Logic** : Exponential backoff (1s → 2s → 4s, max 3 tentatives)

### 3.2 WebSocket Store (`websocket.svelte.ts`)

**État** :
```typescript
interface WebSocketState {
  status: 'disconnected' | 'connecting' | 'connected' | 'error';
  lastEvent: ProcessingEventData | null;
  recentEvents: ProcessingEventData[]; // Last 50
  error: string | null;
}
```

**Types d'événements** :
- `processing_started`, `processing_completed`
- `email_started`, `email_analyzing`, `email_completed`
- `email_queued`, `email_executed`, `email_error`
- `batch_started`, `batch_completed`, `batch_progress`
- `system_ready`, `system_error`

**Protocole** :
1. Connexion `ws://localhost:8000/ws/live`
2. Envoi `{type: 'auth', token}`
3. Attente `{type: 'authenticated'}`
4. Ping/pong toutes les 30 secondes
5. Auto-reconnect après 3 secondes

### 3.3 Toast Store (`toast.svelte.ts`)

**Types** :
```typescript
type ToastType = 'success' | 'error' | 'warning' | 'info' | 'undo';

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  title?: string;
  duration?: number;
  onUndo?: () => Promise<void>;
  countdownSeconds?: number;
}
```

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `add(type, message, options)` | Ajouter toast |
| `undo(message, onUndo, options)` | Toast avec countdown 15s |
| `executeUndo(id)` | Appeler action undo |
| `dismiss(id)` | Fermer un toast |
| `clear()` | Effacer tous |

### 3.4 Queue Store (`queue.svelte.ts`)

**État** :
```typescript
interface QueueState {
  items: QueueItem[];
  stats: QueueStats | null;
  loading: boolean;
  error: string | null;
  currentPage: number;
  hasMore: boolean;
  total: number;
  statusFilter: string;
}
```

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `fetchQueue(status, page)` | Charge items paginés |
| `loadMore()` | Append next page |
| `approve(itemId, ...)` | Approuver + refresh |
| `reject(itemId, reason?)` | Rejeter + refresh |
| `removeFromList(itemId)` | Optimistic update |
| `restoreItem(item)` | Restore après undo |

### 3.5 Briefing Store (`briefing.svelte.ts`)

**État** :
```typescript
interface BriefingState {
  briefing: MorningBriefing | null;
  stats: Stats | null;
  loading: boolean;
  error: string | null;
  lastFetch: Date | null;
}
```

**Computed** :
```typescript
const urgentItems = $derived(briefing?.urgent_items ?? []);
const calendarToday = $derived(briefing?.calendar_today ?? []);
```

### 3.6 Note Chat Store (`note-chat.svelte.ts`)

**État** :
```typescript
interface NoteChatState {
  noteContext: NoteContext | null;
  isOpen: boolean;
  messages: ChatMessage[];
  suggestions: DiscussionSuggestion[];
  sending: boolean;
  discussionId: string | null;
}
```

**Suggestions contextuelles par type** :
- `personne`: "Prépare interaction", "Résume échanges"
- `projet`: "État avancement", "Prochains jalons"
- `concept`: "Explique simplement", "Exemples"

### 3.7 Notes Review Store (`notes-review.svelte.ts`)

**État** :
```typescript
interface NotesReviewState {
  dueNotes: NoteReviewMetadata[];
  stats: ReviewStatsResponse | null;
  currentIndex: number;
  reviewedThisSession: number;
}
```

**Méthodes** :

| Méthode | Description |
|---------|-------------|
| `fetchDueNotes(limit?, type?)` | Notes à réviser |
| `submitReview(quality: 0-5)` | Enregistre révision SM-2 |
| `postponeCurrentNote(hours)` | Décale révision |
| `nextNote()`, `previousNote()` | Navigation |

---

## 4. Composants

### 4.1 UI Composants (`lib/components/ui/`)

#### Button.svelte

```typescript
interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'glass';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  hapticStyle?: 'light' | 'medium' | 'heavy';
  onclick?: (e: MouseEvent) => void;
}
```

- Liquid glass styling
- Haptic feedback mobile
- Loading spinner intégré
- Touch target 44px min

#### Modal.svelte

```typescript
interface Props {
  open: boolean;              // $bindable
  title?: string;
  size?: 'sm' | 'md' | 'lg' | 'full';
  closable?: boolean;
  closeOnBackdrop?: boolean;
  closeOnEscape?: boolean;
}
```

- Focus trap
- Scroll lock
- Spring animation
- ESC key close

#### CommandPalette.svelte

- Recherche globale (Cmd+K)
- Debounced search (300ms)
- Résultats : notes, emails, events
- Navigation clavier

#### Card.svelte

```typescript
interface Props {
  variant?: 'default' | 'elevated' | 'elevated-glass';
  padding?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}
```

#### VirtualList.svelte

```typescript
interface Props {
  items: T[];
  height: number;
  itemHeight: number;
}
```

- `@tanstack/svelte-virtual`
- Scrolle 10,000+ items
- Lazy rendering

#### SwipeableCard.svelte

- Détection swipe touch (20px min)
- Feedback visuel
- Desktop : souris glisse

#### PullToRefresh.svelte

- Mobile pull-to-refresh (80px)
- Spinner animé
- Cooldown 1 seconde

### 4.2 Layout Composants (`lib/components/layout/`)

#### Sidebar.svelte

Navigation items :
```
☀️  Rapport (/)
📜 Courrier (/flux)
✏️  Brouillons (/drafts)
📝 Carnets (/notes)
💬 Conversations (/discussions)
📖 Journal (/journal)
🎭 Valets (/valets)
📊 Registres (/stats)
⚙️  Réglages (/settings)
```

#### ChatPanel.svelte

- Desktop : fixed right (w-72)
- Mobile : modal overlay
- Modes : Général, Note, Focus

#### NotificationsPanel.svelte

- Badge unread count
- Slide-in panel / modal
- Mark read, delete

#### MobileNav.svelte

- Bottom nav (mobile)
- 5-6 items clés
- Tap feedback

### 4.3 Notes Composants (`lib/components/notes/`)

#### MarkdownEditor.svelte

- Toolbar d'édition
- Syntax highlighting
- Auto-save 2s inactivité

#### MarkdownPreview.svelte

- Parse markdown → HTML
- Sanitized (DOMPurify)
- Wikilinks `[[Note]]` → liens

#### NoteHistory.svelte

- Timeline modifications
- Restore version
- Diff view

#### ReviewCard.svelte

- SM-2 metadata
- Quality buttons (0-5)
- Next review date

---

## 5. Client API TypeScript

### 5.1 Client API (`lib/api/client.ts`)

```typescript
const API_BASE = '/api';

// Token management
setAuthToken(token)
getAuthToken()
clearAuthToken()

// Error handling
class ApiError extends Error {
  constructor(public status: number, public message: string)
}
```

### 5.2 Endpoints Principaux

#### Auth
```typescript
login(pin: string): Promise<TokenResponse>
checkAuth(): Promise<AuthCheckResponse>
logout(): Promise<void>
```

#### Queue
```typescript
listQueueItems(page, limit, status?): Promise<{data, page, has_more, total}>
getQueueStats(): Promise<QueueStats>
approveQueueItem(id, modifiedAction?, modifiedCategory?): Promise<QueueItem>
rejectQueueItem(id, reason?): Promise<QueueItem>
undoQueueItem(id): Promise<QueueItem>
reanalyzeQueueItem(id): Promise<QueueItem>
```

#### Notes
```typescript
getNotesTree(maxDepth?): Promise<NotesTree>
listNotes(page, limit, folderPath?): Promise<{data, page, has_more, total}>
getNote(noteId): Promise<Note>
updateNote(noteId, content, tags?): Promise<Note>
syncAppleNotes(): Promise<NoteSyncStatus>
```

#### Review (SM-2)
```typescript
getNotesDue(limit?, noteType?): Promise<{notes, total}>
getReviewStats(): Promise<ReviewStatsResponse>
recordReview(noteId, quality): Promise<RecordReviewResponse>
postponeReview(noteId, hours): Promise<void>
```

#### Briefing
```typescript
getMorningBriefing(): Promise<MorningBriefing>
getPreMeetingBriefing(eventId): Promise<MeetingBriefing>
```

#### Search
```typescript
globalSearch(query, options?): Promise<GlobalSearchResponse>
```

---

## 6. Utilitaires

### 6.1 Formatters (`lib/utils/formatters.ts`)

```typescript
// Dates
formatRelativeTime(isoString)    // "Il y a 5 minutes"
formatDate(date)                 // "14 jan. 2026"
formatTime(date)                 // "14:30"
formatDatetime(date)             // "14 jan. 2026 14:30"

// Texte
truncate(text, maxLength)        // "Très long texte..."
highlightMatches(text, query)    // Search highlighting
parseWikilinks(text)             // Extract [[Note]]
```

### 6.2 Keyboard Shortcuts (`lib/utils/keyboard-shortcuts.ts`)

```typescript
interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  meta?: boolean;
  handler: () => void;
  global?: boolean;
}
```

**Global** :
```
Cmd+K / Ctrl+K    → Command palette
?                  → Aide clavier
Esc                → Fermer modals
```

**Context (Flux)** :
```
j                  → Item suivant
k                  → Item précédent
a                  → Approuver
r                  → Rejeter
s                  → Snooze
Enter              → Détail
```

### 6.3 Haptics (`lib/utils/haptics.ts`)

```typescript
type HapticStyle = 'light' | 'medium' | 'heavy';

function haptic(style: HapticStyle): void
```

---

## 7. PWA & Service Worker

### 7.1 Manifest (`static/manifest.json`)

```json
{
  "name": "Scapin",
  "short_name": "Scapin",
  "description": "Votre valet de l'esprit",
  "start_url": "/",
  "display": "standalone",
  "theme_color": "#007aff",
  "background_color": "#000000"
}
```

**Features** :
- **Standalone** : Affiche comme app native
- **Offline** : Service Worker cache
- **Install** : Ajouter à l'écran d'accueil
- **Shortcuts** : Raccourcis depuis launcher
- **Share Target** : Reçoit shares
- **Protocol Handler** : `web+scapin://`

### 7.2 Service Worker (`static/sw.js`)

**Version** : 0.9.0

**Stratégies de Cache** :

| Route | Stratégie | Cache |
|-------|-----------|-------|
| `/` | Cache-first | STATIC |
| `/api/*` | Network-first | API_CACHE (5 min TTL) |
| `.js, .css, .png` | Cache-first | CACHE |
| `/ws` | Skip | — |

**Notifications Push** :
```javascript
self.addEventListener('push', (event) => {
  const data = event.data?.json();
  self.registration.showNotification(data.title, data);
});
```

---

## 8. Tests Playwright

### 8.1 Configuration (`playwright.config.ts`)

```typescript
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'Mobile Chrome', use: { ...devices['Pixel 5'] } },
    { name: 'Mobile Safari', use: { ...devices['iPhone 12'] } }
  ]
});
```

### 8.2 Structure des Tests

| Fichier | Tests | Scope |
|---------|-------|-------|
| `flux.spec.ts` | 14 | Approve, reject, snooze |
| `notes.spec.ts` | 18 | Tree, editor, preview |
| `discussions.spec.ts` | 13 | Chat panel, messages |
| `journal.spec.ts` | 13 | Multi-source tabs |
| `stats.spec.ts` | 13 | Metrics, charts |
| `settings.spec.ts` | 14 | Tabs, integrations |
| `search.spec.ts` | 15 | Command palette |
| `notifications.spec.ts` | 12 | Badge, panel |

**Total** : 132 tests × 5 browsers = **660 tests**

### 8.3 Exemple

```typescript
test.describe('Flux', () => {
  test('should approve email', async ({ page }) => {
    await page.goto('/');
    const item = await page.locator('[data-testid="flux-item"]').first();
    await item.locator('[data-testid="approve-button"]').click();
    await expect(page.locator('[data-testid="undo-toast"]')).toContainText('approuvé');
  });
});
```

### 8.4 Test Selectors

```typescript
export const SELECTORS = {
  pinInput: '[data-testid="pin-input"]',
  loginSubmit: '[data-testid="login-submit"]',
  fluxList: '[data-testid="flux-list"]',
  fluxItem: (id) => `[data-testid="flux-item-${id}"]`,
  approveButton: '[data-testid="approve-button"]',
  commandPalette: '[data-testid="command-palette"]',
  searchInput: '[data-testid="search-input"]'
};
```

---

## Résumé Architecture

### Svelte 5 Runes

```svelte
<script>
  // State
  let count = $state(0);

  // Computed
  const doubled = $derived(count * 2);

  // Effects
  $effect(() => {
    console.log('Count changed:', count);
  });
</script>
```

### Store Factory Pattern

```typescript
function createCustomStore() {
  let state = $state({...});

  function action() { /* modify state */ }

  return {
    get state() { return state; },
    action
  };
}
```

### Responsive Layout

```
Mobile (< 640px):
├─ Bottom nav (5 items)
├─ Full-width content
└─ ChatPanel as modal

Desktop (> 1024px):
├─ Sidebar expanded (w-56)
├─ Main content lg:mr-72
└─ ChatPanel visible (w-72)
```
