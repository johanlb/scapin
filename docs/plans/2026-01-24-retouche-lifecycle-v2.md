# Plan : Retouche v2 — Cycle de Vie des Notes

**Branche** : `retouche-lifecycle-v2`
**Date** : Janvier 2026
**Objectif** : Compléter le système Retouche avec gestion du cycle de vie et amélioration du quality_score

---

## Résumé des Fonctionnalités

| Action | Description | Comportement |
|--------|-------------|--------------|
| `flag_obsolete` | Marquer note obsolète | **Toujours Filage** (validation humaine) |
| `merge_into` | Fusionner dans une autre note | Auto si ≥ 0.85, sinon Filage |
| `move_to_folder` | Classer dans le bon dossier | Auto si ≥ 0.85 |
| `quality_score` | Score de qualité revu | Nouvelle formule + priorisation |

---

## Phase 1 : Nouvelles Actions Retouche (2 commits)

### 1.1 Ajouter les actions à l'Enum

**Fichier** : `src/passepartout/retouche_reviewer.py`

```python
class RetoucheAction(str, Enum):
    # ... existant ...
    FLAG_OBSOLETE = "flag_obsolete"      # Marquer obsolète → Filage
    MERGE_INTO = "merge_into"            # Fusionner → Auto/Filage
    MOVE_TO_FOLDER = "move_to_folder"    # Classer → Auto
```

### 1.2 Implémenter les handlers

**FLAG_OBSOLETE** (jamais auto, toujours Filage) :
```python
# Dans _parse_ai_response() : forcer applied=False
if action_type == RetoucheAction.FLAG_OBSOLETE:
    should_apply = False  # Toujours validation humaine
    requires_confirmation = True
```

**MERGE_INTO** (auto si ≥ 0.85, sinon Filage) :
```python
if action_type == RetoucheAction.MERGE_INTO:
    should_apply = confidence >= 0.85
    requires_confirmation = confidence < 0.85
```

**MOVE_TO_FOLDER** (auto si ≥ 0.85) :
```python
if action_type == RetoucheAction.MOVE_TO_FOLDER:
    should_apply = confidence >= 0.85
    # Utilise NoteManager.move_note() existant
```

### 1.3 Métadonnées pour actions en attente

**Fichier** : `src/passepartout/note_metadata.py`

```python
# Nouveaux champs
pending_actions: list[dict] = field(default_factory=list)  # Actions en attente de confirmation
obsolete_flag: bool = False
obsolete_reason: str = ""
merge_target_id: Optional[str] = None
```

---

## Phase 2 : Intégration Filage (2 commits)

### 2.1 Étendre MorningBriefing

**Fichier** : `src/frontin/briefing/models.py`

```python
@dataclass
class PendingRetoucheAction:
    action_id: str
    note_id: str
    note_title: str
    action_type: str  # "flag_obsolete", "merge_into"
    message: str
    confidence: float
    created_at: str
    # Pour merge_into
    target_note_id: Optional[str] = None
    target_note_title: Optional[str] = None

@dataclass
class MorningBriefing:
    # ... existant ...
    pending_retouche_actions: list[PendingRetoucheAction] = field(default_factory=list)
```

### 2.2 Pydantic Models API

**Fichier** : `src/frontin/api/models/retouche.py`

```python
from pydantic import BaseModel

class ApproveActionRequest(BaseModel):
    """Request pour approuver une action retouche."""
    merged_content: str | None = None  # Pour MERGE_INTO avec édition

class ActionResultResponse(BaseModel):
    """Response après approve/reject."""
    success: bool
    action_id: str
    action_type: str
    error: str | None = None
    message: str | None = None
```

### 2.3 Service Layer (logique métier séparée)

**Fichier** : `src/frontin/api/services/retouche_action_service.py`

```python
class RetoucheActionService:
    """Service pour gérer les actions retouche en attente."""

    async def approve_action(self, action_id: str,
                            merged_content: str | None = None) -> ActionResultResponse:
        """Approuve et exécute l'action."""
        action = await self._get_action(action_id)
        if not action:
            return ActionResultResponse(success=False, error="action_not_found")

        if action.action_type == "merge_into":
            return await self._execute_merge(action, merged_content)
        elif action.action_type == "flag_obsolete":
            return await self._execute_delete(action)

    async def reject_action(self, action_id: str) -> ActionResultResponse:
        """Rejette l'action, la supprime de pending."""
        ...
```

### 2.4 Endpoints de confirmation

**Fichier** : `src/frontin/api/routers/briefing.py`

```python
@router.post("/retouche-actions/{action_id}/approve",
             response_model=APIResponse[ActionResultResponse])
async def approve_retouche_action(
    action_id: str,
    request: ApproveActionRequest,
    service: RetoucheActionService = Depends(get_retouche_action_service),
) -> APIResponse[ActionResultResponse]:
    """Approuve et exécute l'action retouche."""
    result = await service.approve_action(action_id, request.merged_content)
    return APIResponse(success=result.success, data=result)

@router.post("/retouche-actions/{action_id}/reject",
             response_model=APIResponse[ActionResultResponse])
async def reject_retouche_action(
    action_id: str,
    service: RetoucheActionService = Depends(get_retouche_action_service),
) -> APIResponse[ActionResultResponse]:
    """Rejette l'action, la supprime de pending."""
    result = await service.reject_action(action_id)
    return APIResponse(success=result.success, data=result)
```

### 2.5 Types TypeScript Client

**Fichier** : `web/src/lib/api/types/retouche.ts`

```typescript
export interface PendingRetoucheAction {
    action_id: string;
    note_id: string;
    note_title: string;
    action_type: 'flag_obsolete' | 'merge_into';
    message: string;
    confidence: number;
    created_at: string;
    target_note_id?: string;
    target_note_title?: string;
}

export interface ApproveActionRequest {
    merged_content?: string;
}

export interface ActionResultResponse {
    success: boolean;
    action_id: string;
    action_type: string;
    error?: string;
    message?: string;
}
```

**Fichier** : `web/src/lib/api/retouche.ts`

```typescript
import { apiClient, type APIResponse } from './client';
import type { ActionResultResponse, ApproveActionRequest } from './types/retouche';

export async function approveAction(
    actionId: string,
    request?: ApproveActionRequest
): Promise<ActionResultResponse> {
    const response = await apiClient.post<APIResponse<ActionResultResponse>>(
        `/api/retouche-actions/${actionId}/approve`,
        request ?? {}
    );
    if (!response.success) throw new APIError(response.error ?? 'Échec');
    return response.data!;
}

export async function rejectAction(actionId: string): Promise<ActionResultResponse> {
    const response = await apiClient.post<APIResponse<ActionResultResponse>>(
        `/api/retouche-actions/${actionId}/reject`
    );
    if (!response.success) throw new APIError(response.error ?? 'Échec');
    return response.data!;
}
```

**Edge cases gérés dans le service :**
- `target_not_found` : Note cible supprimée entre-temps
- `source_modified` : Note modifiée depuis la suggestion → message "Veuillez relancer la retouche"
- `action_not_found` : Action déjà traitée ou expirée

### 2.6 UI Filage

**Fichier** : `web/src/routes/memoires/filage/+page.svelte`

Ajouter section "Actions à confirmer" avec :
- Carte par action pending
- Boutons Approuver / Rejeter
- Affichage du contexte (note cible pour merge)

---

## Phase 3 : Quality Score v2 (2 commits)

### 3.1 Nouvelle formule de calcul

**Fichier** : `src/passepartout/retouche_reviewer.py`

**Ancienne formule** (problématique) :
```python
score = 50  # Base trop généreuse
score += min(20, word_count // 50)  # Mots
score -= actions_needed * 5  # Pénalité inversée !
```

**Nouvelle formule** :
```python
def _calculate_quality_score(context, analysis) -> int:
    score = 0  # Base neutre

    # Contenu (max 30 pts)
    if word_count >= 50:
        score += 10
    if word_count >= 200:
        score += 10
    if word_count >= 500:
        score += 10

    # Structure (max 25 pts)
    if has_summary:
        score += 15
    score += min(10, section_count * 3)

    # Liens (max 15 pts)
    score += min(15, len(outgoing_links) * 3)

    # Complétude IA (max 30 pts) — NOUVEAU
    # Moins d'actions proposées = note déjà bien formée
    actions_count = len([a for a in analysis.actions if a.applied])
    if actions_count == 0:
        score += 30  # Aucune amélioration nécessaire
    elif actions_count <= 2:
        score += 20
    elif actions_count <= 4:
        score += 10
    # > 4 actions = 0 bonus

    return max(0, min(100, score))
```

### 3.2 Priorisation backend

**Fichier** : `src/passepartout/note_metadata.py`

Modifier `get_due_for_retouche()` et `get_due_for_lecture()` :
```sql
ORDER BY
    importance_order ASC,
    COALESCE(quality_score, 0) ASC,  -- Notes faibles en premier
    retouche_next ASC
```

### 3.3 Filtre UI

**Fichier** : `web/src/routes/memoires/+page.svelte`

Ajouter bouton filtre "À améliorer" (quality_score < 50)

**Fichier** : `src/frontin/api/routers/notes.py`

```python
@router.get("/low-quality")
async def get_low_quality_notes(threshold: int = 50, limit: int = 20):
    """Retourne les notes avec quality_score < threshold"""
```

---

## Phase 4 : Action MOVE_TO_FOLDER (1 commit)

### 4.1 Logique de classement

**Fichier** : `src/passepartout/retouche_reviewer.py`

Dans le prompt IA, ajouter :
```
- move_to_folder : Si la note est mal classée, suggérer le bon dossier.
  Dossiers possibles : Personnes, Projets, Entités, Réunions, Processus, Événements, Souvenirs
  Fournir le dossier cible dans "content". Confiance 0.85 requise.
```

Handler :
```python
if action.action_type == RetoucheAction.MOVE_TO_FOLDER:
    target_folder = action.content
    if target_folder:
        # Utilise l'infrastructure existante
        self.notes.move_note(note_id, f"Personal Knowledge Management/{target_folder}")
```

---

## Phase 5 : Interface Utilisateur Complète (2 commits)

### 5.1 Modal de Fusion (MERGE_INTO)

**Fichier** : `web/src/lib/components/notes/MergeModal.svelte`

```svelte
<!-- Modal côte à côte avec Liquid Glass et accessibilité -->
<script lang="ts">
  import { onMount } from 'svelte';
  import type { Note } from '$lib/api/types/notes';

  interface Props {
    sourceNote: Note;
    targetNote: Note;
    onMerge: (mergedContent: string) => void;
    onCancel: () => void;
  }

  let { sourceNote, targetNote, onMerge, onCancel }: Props = $props();

  // États
  let mergedContent = $state(targetNote.content);
  let loading = $state(false);
  let error = $state<string | null>(null);

  // Refs pour focus trap
  let dialogRef: HTMLElement;
  let firstFocusable: HTMLElement;
  let lastFocusable: HTMLElement;

  // Keyboard handling (Tab trap + Escape)
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      onCancel();
    } else if (event.key === 'Tab') {
      // Focus trap dans le modal
      if (event.shiftKey && document.activeElement === firstFocusable) {
        event.preventDefault();
        lastFocusable.focus();
      } else if (!event.shiftKey && document.activeElement === lastFocusable) {
        event.preventDefault();
        firstFocusable.focus();
      }
    }
  }

  onMount(() => {
    // Focus initial sur le textarea
    firstFocusable?.focus();
  });

  async function handleMerge() {
    loading = true;
    error = null;
    try {
      await onMerge(mergedContent);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur lors de la fusion';
    } finally {
      loading = false;
    }
  }
</script>

<!-- Modal avec ARIA et Liquid Glass -->
<div
  bind:this={dialogRef}
  role="dialog"
  aria-modal="true"
  aria-labelledby="merge-title"
  class="fixed inset-0 z-50 flex items-center justify-center"
  onkeydown={handleKeydown}
>
  <!-- Backdrop -->
  <div class="absolute inset-0 bg-black/50" onclick={onCancel} aria-hidden="true"></div>

  <!-- Content avec glass-solid -->
  <div class="relative glass-solid rounded-2xl p-6 max-w-5xl w-full mx-4 max-h-[90vh] overflow-auto">
    <h2 id="merge-title" class="text-xl font-semibold mb-4">Fusionner les notes</h2>

    {#if error}
      <div role="alert" class="bg-red-100 text-red-800 p-3 rounded mb-4">
        {error}
      </div>
    {/if}

    <div class="grid grid-cols-2 gap-4">
      <!-- Note source (lecture seule) -->
      <div class="glass-subtle rounded-xl p-4">
        <h3 class="font-medium mb-2">Source : {sourceNote.title}</h3>
        <pre class="text-sm whitespace-pre-wrap">{sourceNote.content}</pre>
      </div>

      <!-- Note cible (éditable) -->
      <div class="glass-subtle rounded-xl p-4">
        <label for="merged-content" class="font-medium mb-2 block">
          Cible : {targetNote.title}
        </label>
        <textarea
          id="merged-content"
          bind:this={firstFocusable}
          bind:value={mergedContent}
          class="w-full h-96 p-2 rounded border bg-white/80 focus:ring-2 focus:ring-blue-500 focus:outline-none"
          aria-describedby="merge-hint"
        ></textarea>
        <p id="merge-hint" class="text-sm text-muted mt-1">
          Modifiez le contenu fusionné selon vos besoins
        </p>
      </div>
    </div>

    <div class="flex gap-2 mt-6 justify-end">
      <button
        type="button"
        onclick={onCancel}
        class="glass-interactive px-4 py-2 rounded-lg"
        disabled={loading}
      >
        Annuler
      </button>
      <button
        bind:this={lastFocusable}
        type="button"
        onclick={handleMerge}
        disabled={loading}
        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
      >
        {#if loading}
          <span class="spinner" aria-hidden="true"></span>
        {/if}
        Fusionner et archiver source
      </button>
    </div>
  </div>
</div>
```

**Accessibilité :**
- `role="dialog"` + `aria-modal="true"`
- `aria-labelledby` pour le titre
- Focus trap (Tab/Shift+Tab cyclent dans le modal)
- Escape ferme le modal
- Focus initial sur le textarea
- Labels sur tous les inputs

**États UI :**
- `loading`: Spinner + boutons désactivés
- `error`: Alert role avec message
- Liquid Glass : `glass-solid` pour modal, `glass-subtle` pour sections

### 5.2 Notifications pour actions auto avec Undo

**Fichier** : `src/frontin/api/services/retouche_notification_service.py`

Ajouter méthodes :
```python
async def notify_auto_move(self, note_id: str, note_title: str,
                           old_folder: str, new_folder: str) -> bool:
    """Toast + panel : Note déplacée automatiquement"""

async def notify_auto_merge(self, source_title: str, target_title: str,
                            undo_token: str) -> bool:
    """Toast + panel : Fusion automatique effectuée"""

async def undo_auto_action(self, undo_token: str) -> bool:
    """Annule une action auto (move ou merge) dans les 30s"""
```

**Fichier** : `web/src/lib/components/ui/Toast.svelte`

Toast avec bouton Undo (timeout 30s) :
```svelte
<Toast type="info" duration={30000}>
  <span>📂 [[Note]] déplacée vers Personnes</span>
  <Button size="xs" variant="ghost" onclick={undo}>Annuler</Button>
</Toast>
```

**Mécanisme Undo :**
- Backend génère un `undo_token` (UUID) stocké en mémoire (TTLCache 60s)
- Token contient : action_type, note_id, previous_state (folder ou content)
- Endpoint `POST /api/retouche/undo/{token}` restaure l'état précédent
- Après 30s, le toast disparaît et l'undo n'est plus proposé

### 5.3 Filtres dans /memoires

**Fichier** : `web/src/routes/memoires/+page.svelte`

Ajouter 3 nouveaux filtres :

```svelte
<FilterBar>
  <!-- Filtres existants -->
  <FilterChip active={filter === 'all'}>Toutes</FilterChip>
  <FilterChip active={filter === 'recent'}>Récentes</FilterChip>

  <!-- Nouveaux filtres -->
  <FilterChip active={filter === 'low-quality'} icon="⚠️">
    À améliorer ({lowQualityCount})
  </FilterChip>
  <FilterChip active={filter === 'obsolete'} icon="🗑️">
    Obsolètes ({obsoleteCount})
  </FilterChip>
  <FilterChip active={filter === 'merge-pending'} icon="🔀">
    À fusionner ({mergePendingCount})
  </FilterChip>
</FilterBar>
```

**Endpoints API requis** :
```python
@router.get("/notes/obsolete")      # Notes avec obsolete_flag=True
@router.get("/notes/merge-pending") # Notes avec merge_target_id != null
@router.get("/notes/low-quality")   # Notes avec quality_score < 50
```

**Empty states :**
```svelte
{#if filter === 'low-quality' && notes.length === 0}
  <EmptyState icon="✨" message="Toutes vos notes sont de bonne qualité !" />
{:else if filter === 'obsolete' && notes.length === 0}
  <EmptyState icon="📚" message="Aucune note obsolète" />
{:else if filter === 'merge-pending' && notes.length === 0}
  <EmptyState icon="🔀" message="Aucune fusion en attente" />
{/if}
```

### 5.4 Carte d'action dans le Filage

**Fichier** : `web/src/lib/components/memory/PendingActionCard.svelte`

```svelte
<script lang="ts">
  import type { PendingRetoucheAction } from '$lib/api/types/retouche';

  interface Props {
    action: PendingRetoucheAction;
    onApprove: () => Promise<void>;
    onReject: () => Promise<void>;
    onOpenMergeModal?: () => void;
  }

  let { action, onApprove, onReject, onOpenMergeModal }: Props = $props();

  let loading = $state(false);

  // Labels accessibles
  const actionLabel = $derived(
    action.action_type === 'flag_obsolete' ? 'Supprimer' : 'Fusionner'
  );
  const iconLabel = $derived(
    action.action_type === 'flag_obsolete' ? 'Note obsolète' : 'Fusion suggérée'
  );

  async function handleApprove() {
    loading = true;
    try {
      await onApprove();
    } finally {
      loading = false;
    }
  }

  async function handleReject() {
    loading = true;
    try {
      await onReject();
    } finally {
      loading = false;
    }
  }
</script>

<!-- Card avec Liquid Glass et accessibilité -->
<article
  class="glass-subtle rounded-xl p-4 border-l-4 border-amber-500"
  aria-label="Action en attente : {action.note_title}"
>
  <div class="flex items-center gap-3">
    <!-- Icon avec aria-label -->
    <span class="text-2xl" role="img" aria-label={iconLabel}>
      {action.action_type === 'flag_obsolete' ? '🗑️' : '🔀'}
    </span>

    <div class="flex-1 min-w-0">
      <h4 class="font-medium truncate">[[{action.note_title}]]</h4>
      <p class="text-sm text-muted-foreground">{action.message}</p>
      {#if action.target_note_title}
        <p class="text-sm text-blue-600">
          → Fusionner avec [[{action.target_note_title}]]
        </p>
      {/if}
      <p class="text-xs text-muted-foreground mt-1">
        Confiance : {Math.round(action.confidence * 100)}%
      </p>
    </div>

    <div class="flex gap-2 flex-shrink-0">
      <button
        type="button"
        onclick={handleReject}
        disabled={loading}
        class="glass-interactive px-3 py-1.5 text-sm rounded-lg"
        aria-label="Ignorer l'action pour {action.note_title}"
      >
        Ignorer
      </button>

      {#if action.action_type === 'merge_into' && onOpenMergeModal}
        <button
          type="button"
          onclick={onOpenMergeModal}
          disabled={loading}
          class="bg-blue-600 text-white px-3 py-1.5 text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
          aria-label="Voir et fusionner {action.note_title} avec {action.target_note_title}"
        >
          Voir et fusionner
        </button>
      {:else}
        <button
          type="button"
          onclick={handleApprove}
          disabled={loading}
          class="bg-red-600 text-white px-3 py-1.5 text-sm rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-1"
          aria-label="Supprimer {action.note_title}"
        >
          {#if loading}
            <span class="spinner w-3 h-3" aria-hidden="true"></span>
          {/if}
          Supprimer
        </button>
      {/if}
    </div>
  </div>
</article>
```

**Accessibilité :**
- `<article>` sémantique avec `aria-label`
- `role="img"` + `aria-label` sur les icônes emoji
- `aria-label` explicites sur tous les boutons
- Loading states avec spinners masqués pour screen readers

---

## Phase 6 : Tests (1 commit)

### Tests unitaires Backend

**Fichier** : `tests/unit/test_retouche_reviewer.py`

```python
class TestFlagObsolete:
    def test_never_auto_applies(self):
        """FLAG_OBSOLETE should always require confirmation"""

    def test_creates_pending_action(self):
        """FLAG_OBSOLETE creates entry in pending_actions"""

class TestMergeInto:
    def test_auto_applies_above_085(self):
        """MERGE_INTO auto-applies at 85%+ confidence"""

    def test_requires_confirmation_below_085(self):
        """MERGE_INTO goes to Filage below 85%"""

    def test_stores_target_note_id(self):
        """MERGE_INTO stores target note reference"""

class TestMoveToFolder:
    def test_moves_to_correct_folder(self):
        """Note is moved to correct folder based on type"""

    def test_no_op_if_already_in_folder(self):
        """MOVE_TO_FOLDER skips if already in target folder"""

class TestQualityScoreV2:
    def test_empty_note_scores_zero(self):
        """Empty note should score 0, not 50"""

    def test_no_actions_gives_bonus(self):
        """Note needing no improvements gets 30pt bonus"""

    def test_many_actions_no_bonus(self):
        """Note with 5+ actions gets 0 bonus"""
```

**Fichier** : `tests/unit/test_retouche_action_service.py`

```python
class TestApproveAction:
    async def test_approve_flag_obsolete_deletes_note(self):
        """Approving FLAG_OBSOLETE soft-deletes the note"""

    async def test_approve_merge_appends_content(self):
        """Approving MERGE_INTO appends source to target"""

    async def test_approve_merge_archives_source(self):
        """After merge, source note is soft-deleted"""

    # CAS D'ERREUR (obligatoire selon /workflow)
    async def test_approve_fails_if_target_deleted(self):
        """Returns error if merge target was deleted"""

    async def test_approve_fails_if_source_modified(self):
        """Returns error if source was modified since suggestion"""

    async def test_approve_fails_if_action_not_found(self):
        """Returns error if action already processed"""

class TestRejectAction:
    async def test_reject_removes_from_pending(self):
        """Rejecting action removes it from pending_actions"""

class TestUndoAction:
    async def test_undo_move_restores_folder(self):
        """Undo MOVE_TO_FOLDER restores original folder"""

    async def test_undo_merge_restores_source(self):
        """Undo MERGE_INTO restores source note"""

    async def test_undo_fails_after_timeout(self):
        """Undo returns error after 60s TTL expired"""
```

### Tests E2E Frontend

**Fichier** : `web/e2e/pages/filage.spec.ts`

```typescript
test.describe('Filage - Actions Retouche', () => {
  test('displays pending retouche actions', async ({ page }) => {
    // Mock pending actions
    await page.route('**/api/briefing/daily', (route) =>
      route.fulfill({
        body: JSON.stringify({
          pending_retouche_actions: [
            { action_id: '1', note_title: 'Test', action_type: 'flag_obsolete', confidence: 0.9 }
          ]
        })
      })
    );
    await page.goto('/memoires/filage');
    await expect(page.locator('text=Test')).toBeVisible();
  });

  test('approve button triggers deletion', async ({ page }) => {
    // Test approve flow
  });

  test('reject button removes action', async ({ page }) => {
    // Test reject flow
  });

  test('keyboard navigation works', async ({ page }) => {
    // Tab between buttons, Enter to activate
  });
});
```

**Fichier** : `web/e2e/pages/merge-modal.spec.ts`

```typescript
test.describe('MergeModal', () => {
  test('displays both notes side by side', async ({ page }) => {
    // Test modal content
  });

  test('escape closes modal', async ({ page }) => {
    // Keyboard a11y test
  });

  test('focus trap works correctly', async ({ page }) => {
    // Tab cycles within modal
  });

  test('shows error if target note deleted', async ({ page }) => {
    // Mock API error, verify error message
  });
});
```

---

## Phase 7 : Migration (1 commit)

### 7.1 Recalcul quality_score pour notes existantes

**Script** : `scripts/migrate_quality_scores.py`

```python
"""
Migration : Recalcul quality_score avec nouvelle formule.
À exécuter une fois après déploiement.
"""
async def migrate():
    notes = note_manager.list_all_notes()
    updated = 0

    for note in notes:
        old_score = note.quality_score
        new_score = calculate_quality_score_v2(note)

        if old_score != new_score:
            note_metadata.update(note.note_id, quality_score=new_score)
            updated += 1

    print(f"Migration terminée : {updated}/{len(notes)} notes mises à jour")
```

**Exécution :**
```bash
python scripts/migrate_quality_scores.py --dry-run  # Prévisualisation
python scripts/migrate_quality_scores.py            # Exécution
```

### 7.2 Initialisation champs metadata

Les nouveaux champs ont des valeurs par défaut :
- `pending_actions`: `[]`
- `obsolete_flag`: `False`
- `merge_target_id`: `None`

Pas de migration nécessaire — SQLite gère les valeurs par défaut.

---

## Fichiers Critiques

### Backend

| Fichier | Modifications |
|---------|---------------|
| `src/passepartout/retouche_reviewer.py` | 3 nouvelles actions, nouvelle formule quality_score |
| `src/passepartout/note_metadata.py` | Champs pending_actions, priorisation par quality |
| `src/frontin/briefing/models.py` | PendingRetoucheAction model |
| `src/frontin/briefing/generator.py` | Charger pending_actions |
| `src/frontin/api/models/retouche.py` | **Nouveau** — Pydantic models request/response |
| `src/frontin/api/services/retouche_action_service.py` | **Nouveau** — Service layer approve/reject |
| `src/frontin/api/routers/briefing.py` | Endpoints approve/reject |
| `src/frontin/api/routers/notes.py` | Endpoints low-quality, obsolete, merge-pending |
| `src/frontin/api/services/retouche_notification_service.py` | notify_auto_move, notify_auto_merge, undo |
| `scripts/migrate_quality_scores.py` | **Nouveau** — Script migration |

### Frontend

| Fichier | Modifications |
|---------|---------------|
| `web/src/lib/api/types/retouche.ts` | **Nouveau** — Types TypeScript |
| `web/src/lib/api/retouche.ts` | **Nouveau** — Client API |
| `web/src/lib/components/notes/MergeModal.svelte` | **Nouveau** — Modal fusion (a11y + Liquid Glass) |
| `web/src/lib/components/memory/PendingActionCard.svelte` | **Nouveau** — Carte action Filage |
| `web/src/routes/memoires/filage/+page.svelte` | Section actions pending |
| `web/src/routes/memoires/+page.svelte` | 3 nouveaux filtres + empty states |
| `web/src/lib/components/ui/Toast.svelte` | Bouton Undo avec timeout |

### Documentation

| Fichier | Modifications |
|---------|---------------|
| `ARCHITECTURE.md` | Section Retouche Lifecycle |
| `docs/user-guide/retouche.md` | **Nouveau** — Guide utilisateur |

---

## Vérification

### Tests Automatisés

```bash
# Backend
.venv/bin/pytest tests/unit/test_retouche_reviewer.py -v
.venv/bin/pytest tests/unit/test_retouche_action_service.py -v

# Frontend E2E
cd web && npx playwright test filage.spec.ts merge-modal.spec.ts

# Qualité code
.venv/bin/ruff check src/ --fix
cd web && npm run check
```

### Tests Manuels

1. **Test Filage** :
   - [ ] Actions pending apparaissent dans `/memoires/filage`
   - [ ] Bouton "Voir et fusionner" ouvre le modal
   - [ ] Bouton "Supprimer" pour FLAG_OBSOLETE

2. **Test Modal Merge** :
   - [ ] Affiche les 2 notes côte à côte
   - [ ] Permet d'éditer le résultat
   - [ ] "Fusionner" → archive la source
   - [ ] **Keyboard** : Escape ferme, Tab cycle dans modal
   - [ ] **Error state** : Supprimer note cible → "Note cible introuvable"

3. **Test Filtres /memoires** :
   - [ ] Filtre "À améliorer" montre notes < 50
   - [ ] Filtre "Obsolètes" montre notes flaggées
   - [ ] Filtre "À fusionner" montre merge pending
   - [ ] **Empty states** : Chaque filtre affiche message approprié si 0 notes

4. **Test Notifications avec Undo** :
   - [ ] Toast apparaît après action auto (move, merge)
   - [ ] Bouton "Annuler" visible pendant 30s
   - [ ] Clic sur Annuler → action inversée + toast confirmation
   - [ ] Après 30s → bouton disparaît, undo impossible

5. **Test quality_score** :
   - [ ] Note vide = 0 (pas 50)
   - [ ] Note sans actions proposées = bonus 30pts

6. **Test Edge Cases** :
   - [ ] Approve merge avec note cible supprimée → erreur explicite
   - [ ] Approve merge avec note source modifiée → erreur "relancer retouche"

7. **Test Migration** :
   - [ ] `--dry-run` n'applique pas les changements
   - [ ] Exécution réelle met à jour les scores

### Checklist Avant Merge (workflow)

```
□ Documentation mise à jour (ARCHITECTURE.md, docs/user-guide/retouche.md)
□ Tests E2E écrits et passants
□ Tests unitaires écrits et passants (y compris cas d'erreur)
□ Logs vérifiés — aucun ERROR/WARNING nouveau
□ Ruff : 0 warning
□ TypeScript : npm run check passe
□ Pas de TODO, code commenté, ou console.log
```

---

## Commits Prévus

1. `feat(retouche): ajouter actions FLAG_OBSOLETE, MERGE_INTO, MOVE_TO_FOLDER`
2. `feat(metadata): ajouter champs pending_actions et obsolete_flag`
3. `feat(briefing): intégrer actions retouche en attente dans Filage`
4. `feat(api): ajouter endpoints approve/reject avec service layer`
5. `fix(quality): réécrire formule quality_score (base 0, bonus complétude)`
6. `feat(notes): ajouter priorisation par qualité et endpoints filtres`
7. `feat(ui): ajouter MergeModal avec a11y et Liquid Glass`
8. `feat(ui): ajouter PendingActionCard et section Filage`
9. `feat(ui): ajouter filtres avec empty states dans /memoires`
10. `feat(notifications): ajouter toast avec mécanisme undo (30s)`
11. `test(retouche): ajouter tests lifecycle actions et UI`
12. `chore(migration): ajouter script recalcul quality_score`
13. `docs: mettre à jour ARCHITECTURE.md et user-guide`

**Total : 13 commits atomiques**

---

## Documentation à Mettre à Jour

### ARCHITECTURE.md

Ajouter section "Retouche Lifecycle" :
- Nouvelles actions (flag_obsolete, merge_into, move_to_folder)
- Flux de validation Filage
- Mécanisme Undo

### docs/user-guide/

Créer ou modifier `docs/user-guide/retouche.md` :
- Explication des nouvelles actions
- Comment approuver/rejeter dans Filage
- Filtres disponibles dans /memoires
- Notifications et Undo
