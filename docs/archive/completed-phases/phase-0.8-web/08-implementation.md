# 08 - Ordre d'Implémentation

[< Retour à l'index](./00-index.md) | [< API Endpoints](./07-api-endpoints.md)

---

## Vue d'Ensemble

**21 étapes** organisées en 5 phases :

| Phase | Étapes | Focus | Priorité |
|-------|--------|-------|----------|
| **Setup** | 1-4 | Infrastructure technique | MVP |
| **Core UI** | 5-10 | Fonctionnalités principales | MVP |
| **Mobile** | 11 | Adaptation mobile-first | **MVP** |
| **Analytics** | 12-15 | Stats, Journal, Rapports | Nice-to-have |
| **Backend** | 16-20 | Extensions API | MVP/Parallèle |
| **Polish** | 21 | Tests et finitions | MVP |

---

## Graphe de Dépendances

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                      PHASE SETUP                          │
                    └──────────────────────────────────────────────────────────┘
                                              │
            ┌─────────────────────────────────┴─────────────────────────────────┐
            │                                                                   │
     ┌──────▼──────┐                                                    ┌───────▼───────┐
     │  1. Setup   │                                                    │ 16-20. Backend│
     │   SvelteKit │                                                    │  (parallèle)  │
     └──────┬──────┘                                                    └───────────────┘
            │
     ┌──────▼──────┐
     │ 2. Design   │
     │   System    │
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ 3. Layout   │◄─── Chat Panel (latéral, style Claude)
     └──────┬──────┘
            │
     ┌──────▼──────┐
     │ 4. API +    │
     │   Auth      │
     └──────┬──────┘
            │
            └─────────────────────────────────────────────────────────────────────┐
                    │                      PHASE CORE UI                          │
                    └─────────────────────────────────────────────────────────────┘
                                              │
     ┌────────────────┬───────────────┬───────┴───────┬───────────────┬───────────┐
     │                │               │               │               │           │
┌────▼────┐    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐    │
│ 5.Login │    │ 6.Briefing  │ │ 7-8.Flux    │ │ 9.Notes     │ │10.Discuss.  │    │
└────┬────┘    │   (Home)    │ │  (4 tabs)   │ │   PKM       │ │   Chat      │    │
     │         └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │
     │                                                                            │
     └──────────────────────────────────────┬─────────────────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────────────────┐
                    │                      PHASE MOBILE (MVP)                    │
                    └───────────────────────────────────────────────────────────┘
                                            │
                                     ┌──────▼──────┐
                                     │ 11.Mobile   │
                                     │ BottomNav   │
                                     │ Swipe/Touch │
                                     │ PWA         │
                                     └──────┬──────┘
                                            │
                    ┌───────────────────────┴───────────────────────────────────┐
                    │                    PHASE ANALYTICS (Nice-to-have)          │
                    └───────────────────────────────────────────────────────────┘
                                            │
          ┌─────────────────┬───────────────┼───────────────┬───────────────────┐
          │                 │               │               │                   │
   ┌──────▼──────┐   ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐           │
   │ 12.Stats    │   │ 13.Pipeline │ │ 14.Journal  │ │ 15.Rapports │           │
   │  Dashboard  │   │   Valets    │ │ Interactif  │ │             │           │
   └─────────────┘   └─────────────┘ └─────────────┘ └─────────────┘           │
                                                                                │
                    ┌───────────────────────┴───────────────────────────────────┐
                    │                      PHASE POLISH (MVP)                    │
                    └───────────────────────────────────────────────────────────┘
                                            │
                                     ┌──────▼──────┐
                                     │ 21. Tests & │
                                     │   Polish    │
                                     └─────────────┘
```

---

## Étape 1 : Setup Projet SvelteKit — MVP

**Complexité** : S | **Dépendances** : Aucune

```bash
npm create svelte@latest web    # TypeScript, skeleton
cd web
npm install
```

1. Configurer TypeScript strict mode
2. Installer TailwindCSS + plugins (forms, typography)
3. Configurer thème dark/light auto (`prefers-color-scheme`)
4. Setup Prettier + ESLint + svelte-check
5. Structure dossiers :
   ```
   src/
   ├── lib/
   │   ├── components/    # Composants réutilisables
   │   ├── stores/        # Svelte stores
   │   ├── api/           # Client API
   │   └── utils/         # Utilitaires
   ├── routes/            # Pages SvelteKit
   └── app.css            # Styles globaux
   ```

---

## Étape 2 : Design System — MVP

**Complexité** : M | **Dépendances** : Étape 1

Créer les composants UI de base :

| Composant | Description |
|-----------|-------------|
| `Button.svelte` | Variantes : primary, secondary, ghost, danger |
| `Card.svelte` | Container avec ombre et bordure |
| `Badge.svelte` | Labels colorés (urgence, source) |
| `Input.svelte` | Champs texte avec validation |
| `Modal.svelte` | Dialogs modaux |
| `Tabs.svelte` | Navigation par onglets |
| `Toast.svelte` | Notifications temporaires |
| `ConfidenceBar.svelte` | Barre confiance 0-100% avec couleur |
| `SourceBadge.svelte` | Badges Email/Teams/Calendar/OmniFocus |
| `Skeleton.svelte` | Placeholder chargement |

Configurer :
- Palette couleurs (voir 03-design-system.md)
- Typographie (Inter + JetBrains Mono)
- Tester responsive

---

## Étape 3 : Layout Principal — MVP

**Complexité** : M | **Dépendances** : Étape 2

Architecture 3 colonnes avec chat latéral (style Claude Desktop) :

| Composant | Description |
|-----------|-------------|
| `Layout.svelte` | Container principal 3 colonnes |
| `Sidebar.svelte` | Navigation + compteurs badges |
| `ChatPanel.svelte` | **Panel latéral droit** (pas input en bas!) |
| `Header.svelte` | Status Scapin + Recherche (Cmd+K) + User |

**Important** : Le ChatPanel est un **panel latéral collapsible**, pas un input fixe en bas. Il peut être :
- Ouvert (visible à droite)
- Réduit (icône flottante)
- Plein écran (via /discussions)

---

## Étape 4 : Client API + Auth — MVP

**Complexité** : M | **Dépendances** : Étape 3

| Fichier | Description |
|---------|-------------|
| `api/client.ts` | Fetch wrapper + JWT interceptor + retry |
| `api/types.ts` | Types générés depuis OpenAPI backend |
| `stores/auth.ts` | Store auth (login, logout, refresh, user) |
| `api/websocket.ts` | Client WebSocket pour temps réel |

```typescript
// Exemple client.ts
export async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const token = get(authStore).token;
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options?.headers
    }
  });
  if (!res.ok) throw new ApiError(res);
  return res.json();
}
```

---

## Étape 5 : Page Login — MVP

**Complexité** : S | **Dépendances** : Étape 4

1. Formulaire login avec validation (email + password)
2. Gestion erreurs (credentials invalides, serveur down)
3. Redirect vers `/` (Briefing) après login réussi
4. "Remember me" (localStorage pour token)
5. Page `/auth/login` protégée si déjà connecté

---

## Étape 6 : Page Briefing (Home) — MVP

**Complexité** : L | **Dépendances** : Étape 4-5

La page d'accueil, visible au login.

| Composant | Description |
|-----------|-------------|
| `BriefingLayout.svelte` | Layout 2 colonnes (principal + sidebar) |
| `ScapinSummary.svelte` | Résumé IA du jour (généré par Sancho) |
| `UrgentList.svelte` | Top 3-5 événements urgents |
| `MeetingsToday.svelte` | Réunions avec liens briefing pré-réunion |
| `StatsQuick.svelte` | Compteurs rapides (emails, teams, etc.) |
| `ProgressBar.svelte` | "12 traités / 15 à traiter" |

---

## Étape 7 : Flux d'Événements — Composants — MVP

**Complexité** : L | **Dépendances** : Étape 4

Composants réutilisables pour le flux :

| Composant | Description |
|-----------|-------------|
| `EventCard.svelte` | Card générique (source, résumé, confiance, action proposée) |
| `EventList.svelte` | Liste avec infinite scroll + virtualisation |
| `EventDetail.svelte` | Panneau latéral détails (niveau 2) |
| `EventActions.svelte` | Boutons Approuver/Modifier/Rejeter/Snooze |
| `EventFilters.svelte` | Filtres source, urgence, date |

---

## Étape 8 : Flux d'Événements — Page — MVP

**Complexité** : M | **Dépendances** : Étape 7

**Une seule page `/flux` avec 4 onglets** (pas de routes séparées !) :

| Onglet | Contenu | Badge |
|--------|---------|-------|
| **À traiter** | Événements pending | Compteur rouge |
| **Traités** | Actions exécutées par Scapin | — |
| **Historique** | Timeline complète | — |
| **Rejets** | Actions refusées (apprentissage) | — |

Fonctionnalités :
- Navigation clavier : `j`/`k` (haut/bas), `a` (approuver), `r` (rejeter), `m` (modifier), `u` (undo)
- Détail événement : panneau latéral au clic (pas nouvelle page)
- Route `/flux/[id]` pour lien direct vers un événement spécifique

---

## Étape 9 : Notes PKM — CRUD Complet — MVP

**Complexité** : L | **Dépendances** : Étape 4

| Composant | Description |
|-----------|-------------|
| `NotesList.svelte` | Arborescence dossiers + recherche |
| `NoteEditor.svelte` | Éditeur Markdown (CodeMirror ou Monaco) |
| `NotePreview.svelte` | Rendu Markdown temps réel |
| `NoteLinks.svelte` | Backlinks (liens bidirectionnels) |
| `NotePinned.svelte` | Notes épinglées en haut |

Routes :
- `/notes` — Liste et arborescence
- `/notes/[...path]` — Édition d'une note

---

## Étape 10 : Discussions Multi-Sessions — MVP

**Complexité** : L | **Dépendances** : Étape 4

| Composant | Description |
|-----------|-------------|
| `DiscussionsList.svelte` | Liste sessions (épinglées en haut) |
| `DiscussionView.svelte` | Vue conversation complète |
| `ChatInput.svelte` | Input avec suggestions auto |
| `ChatMessage.svelte` | Bulles user/Scapin avec markdown |

Fonctionnalités :
- Intégration WebSocket temps réel
- Démarrage depuis contexte (event, note, rapport)
- `/discussions` — Page plein écran
- `/discussions/[id]` — Discussion spécifique

---

## Étape 11 : Adaptation Mobile — MVP

**Complexité** : L | **Dépendances** : Étapes 1-10

L'usage mobile est **régulier**, donc prioritaire.

| Composant | Description |
|-----------|-------------|
| `BottomNav.svelte` | Navigation bottom bar (5 items) |
| `SwipeableCard.svelte` | Cards avec gestes swipe |
| `MobileLayout.svelte` | Layout adapté mobile |
| `TouchActions.svelte` | Actions optimisées touch (44px min) |

Fonctionnalités :
- Bottom navigation : Accueil, Flux, Notes, Chat, Plus
- Swipe gauche/droite sur EventCard pour actions rapides
- Pull-to-refresh sur les listes
- Long press pour menu contextuel
- PWA manifest + service worker basique

```css
/* Mobile-first breakpoints */
/* Base: Mobile (< 640px) */
@media (min-width: 640px) { /* Tablet */ }
@media (min-width: 1024px) { /* Desktop */ }
```

Routes :
- Mêmes routes, layout adapté automatiquement
- Chat en page dédiée `/chat` sur mobile (pas panel)

---

## Étape 12 : Page Statistiques — Nice-to-have

**Complexité** : M | **Dépendances** : Étape 4

| Composant | Description |
|-----------|-------------|
| `StatsOverview.svelte` | Dashboard principal avec KPIs |
| `StatsChart.svelte` | Wrapper Chart.js réutilisable |
| `StatsBySource.svelte` | Donut chart répartition par source |
| `ConfidenceChart.svelte` | Évolution confiance dans le temps |
| `ApprovalChart.svelte` | Taux approbation/rejet/modification |
| `LearningPatterns.svelte` | Patterns Sganarelle |

Export CSV/JSON des données.

---

## Étape 13 : Pipeline Valets — Nice-to-have

**Complexité** : M | **Dépendances** : Étape 4

Visualisation temps réel de la brigade (conçue dans 05-mockups-analytics.md).

| Composant | Description |
|-----------|-------------|
| `PipelineView.svelte` | Vue complète avec Johan, Scapin, Valets |
| `ValetCard.svelte` | Card individuelle (état, sujet, métriques) |
| `ValetStats.svelte` | Statistiques par valet |

WebSocket pour mise à jour temps réel des états.

---

## Étape 14 : Page Journal — Nice-to-have

**Complexité** : M | **Dépendances** : Étape 4

| Composant | Description |
|-----------|-------------|
| `JournalList.svelte` | Liste des journaux par date |
| `JournalEditor.svelte` | Édition journal du jour |
| `JournalQuestion.svelte` | Questions interactives Sganarelle |
| `JournalCorrection.svelte` | Interface correction avec feedback |

Route `/journal` et `/journal/[date]`.

---

## Étape 15 : Page Rapports — Nice-to-have

**Complexité** : M | **Dépendances** : Étape 12

| Composant | Description |
|-----------|-------------|
| `ReportList.svelte` | Liste avec filtres (type, date) |
| `ReportCard.svelte` | Affichage rapport formaté |
| `ReportExport.svelte` | Boutons export PDF/Markdown |

Onglets : Journalier / Hebdomadaire / Mensuel.

---

## Étape 16 : Backend — Events Router — MVP (Parallèle)

**Complexité** : L | **Dépendances** : Phase 0.7 existante

```
src/jeeves/api/routers/events.py
```

1. EventService avec agrégation multi-sources (email, teams, calendar)
2. Endpoints : GET pending/processed/rejected/snoozed
3. Actions : POST approve/reject/modify/undo/snooze
4. Pagination et filtrage
5. Tests unitaires

---

## Étape 17 : Backend — Notes Router — MVP (Parallèle)

**Complexité** : M | **Dépendances** : Passepartout existant

```
src/jeeves/api/routers/notes.py
```

1. Intégration Passepartout pour CRUD
2. Recherche full-text
3. Liens bidirectionnels (backlinks)
4. Gestion versions
5. Tests unitaires

---

## Étape 18 : Backend — Discussions & Stats — MVP (Parallèle)

**Complexité** : L | **Dépendances** : Sancho existant

```
src/jeeves/api/routers/discussions.py
src/jeeves/api/routers/stats.py
```

1. Discussions multi-sessions avec historique
2. Intégration Sancho pour réponses IA
3. WebSocket handler temps réel
4. Service agrégation statistiques
5. Tests unitaires

---

## Étape 19 : Backend — Reports & Valets — Nice-to-have (Parallèle)

**Complexité** : M | **Dépendances** : Étape 18

```
src/jeeves/api/routers/reports.py
src/jeeves/api/routers/valets.py
```

1. ReportGenerator service
2. Export PDF/Markdown
3. Endpoint status valets temps réel
4. Tests unitaires

---

## Étape 20 : Backend — Auth + Settings — MVP (Parallèle)

**Complexité** : M | **Dépendances** : Phase 0.7 existante

```
src/jeeves/api/routers/auth.py
src/jeeves/api/routers/settings.py
```

1. JWT complet (login, refresh, logout)
2. Middleware d'authentification
3. CRUD settings et comptes
4. Tests unitaires

---

## Étape 21 : Tests & Polish — MVP

**Complexité** : L | **Dépendances** : Toutes

| Type | Outil | Focus |
|------|-------|-------|
| **Unit** | Vitest | Composants Svelte isolés |
| **E2E** | Playwright | Parcours critiques (login → briefing → flux → action) |
| **Accessibilité** | axe-core | WCAG AA compliance |
| **Performance** | Lighthouse | Score > 90 |

Finitions :
- Responsive final (tablette, mobile)
- Lazy loading images et composants lourds
- Code splitting par route
- Documentation utilisateur

---

## Résumé MVP vs Nice-to-have

| Étape | Nom | MVP | Nice-to-have |
|-------|-----|-----|--------------|
| 1-5 | Setup → Login | X | |
| 6-10 | Briefing → Discussions | X | |
| **11** | **Adaptation Mobile** | **X** | |
| 12-13 | Stats, Pipeline | | X |
| 14-15 | Journal, Rapports | | X |
| 16-18, 20 | Backend core | X | |
| 19 | Backend reports/valets | | X |
| 21 | Tests & Polish | X | |

**MVP** = Étapes 1-11, 16-18, 20-21 (17 étapes)
**Complet** = Toutes les 21 étapes

### Récapitulatif Phases

| Phase | Étapes | Priorité |
|-------|--------|----------|
| Setup | 1-4 | MVP |
| Core UI | 5-10 | MVP |
| Mobile | 11 | **MVP** |
| Analytics | 12-15 | Nice-to-have |
| Backend | 16-20 | MVP (parallèle) |
| Polish | 21 | MVP |

---

[< API Endpoints](./07-api-endpoints.md) | [Suivant : Critères de Succès >](./09-criteres-succes.md)
